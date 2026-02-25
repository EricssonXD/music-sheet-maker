<script lang="ts">
	/**
	 * AudioPlayer — plays back transcribed MIDI via Tone.js with a sampled piano.
	 */
	import { onDestroy } from 'svelte';

	interface Props {
		midiB64: string;
	}

	let { midiB64 }: Props = $props();

	let isPlaying = $state(false);
	let isLoaded = $state(false);
	let currentTime = $state(0);
	let totalDuration = $state(0);
	let error = $state('');

	let synth: any = null;
	let toneTransport: any = null;
	let tonePart: any = null;
	let animFrame: number | null = null;

	async function loadMidi() {
		if (!midiB64 || isLoaded) return;

		try {
			const { Midi } = await import('@tonejs/midi');
			const Tone = await import('tone');

			// Decode base64 to ArrayBuffer
			const binaryStr = atob(midiB64);
			const bytes = new Uint8Array(binaryStr.length);
			for (let i = 0; i < binaryStr.length; i++) {
				bytes[i] = binaryStr.charCodeAt(i);
			}
			const midi = new Midi(bytes.buffer);

			// Create a simple synth (PolySynth for chords/polyphony)
			synth = new Tone.PolySynth(Tone.Synth, {
				oscillator: { type: 'triangle' },
				envelope: {
					attack: 0.02,
					decay: 0.3,
					sustain: 0.4,
					release: 0.8,
				},
			}).toDestination();

			synth.volume.value = -6; // slightly quieter

			toneTransport = Tone.getTransport();

			// Schedule all notes from the first track
			const notes = midi.tracks.flatMap((t: any) => t.notes);
			totalDuration = Math.max(...notes.map((n: any) => n.time + n.duration), 0);

			tonePart = new Tone.Part(
				(time: number, note: any) => {
					synth.triggerAttackRelease(
						note.name,
						note.duration,
						time,
						note.velocity,
					);
				},
				notes.map((n: any) => ({
					time: n.time,
					name: n.name,
					duration: n.duration,
					velocity: n.velocity,
				})),
			);
			tonePart.start(0);

			isLoaded = true;
		} catch (e: any) {
			error = `Failed to load MIDI: ${e.message}`;
		}
	}

	// Load MIDI when midiB64 changes
	$effect(() => {
		if (midiB64) {
			isLoaded = false;
			loadMidi();
		}
	});

	function updateTime() {
		if (toneTransport) {
			currentTime = toneTransport.seconds;
			if (currentTime >= totalDuration) {
				stop();
				return;
			}
		}
		if (isPlaying) {
			animFrame = requestAnimationFrame(updateTime);
		}
	}

	async function play() {
		if (!isLoaded) return;
		const Tone = await import('tone');
		await Tone.start(); // Required: user gesture to start AudioContext
		toneTransport.start();
		isPlaying = true;
		animFrame = requestAnimationFrame(updateTime);
	}

	function pause() {
		if (!isLoaded || !toneTransport) return;
		toneTransport.pause();
		isPlaying = false;
		if (animFrame) cancelAnimationFrame(animFrame);
	}

	function stop() {
		if (!isLoaded || !toneTransport) return;
		toneTransport.stop();
		toneTransport.seconds = 0;
		currentTime = 0;
		isPlaying = false;
		if (animFrame) cancelAnimationFrame(animFrame);
	}

	function seek(e: Event) {
		const input = e.target as HTMLInputElement;
		const time = parseFloat(input.value);
		if (toneTransport) {
			toneTransport.seconds = time;
			currentTime = time;
		}
	}

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	onDestroy(() => {
		if (animFrame) cancelAnimationFrame(animFrame);
		tonePart?.dispose();
		synth?.dispose();
		toneTransport?.stop();
	});
</script>

<div class="player">
	<div class="player-controls">
		{#if isPlaying}
			<button class="btn-control" onclick={pause} title="Pause">
				<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<rect x="6" y="4" width="4" height="16" />
					<rect x="14" y="4" width="4" height="16" />
				</svg>
			</button>
		{:else}
			<button class="btn-control" onclick={play} disabled={!isLoaded} title="Play">
				<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<polygon points="5,3 19,12 5,21" />
				</svg>
			</button>
		{/if}

		<button class="btn-control" onclick={stop} disabled={!isLoaded} title="Stop">
			<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
				<rect x="6" y="6" width="12" height="12" />
			</svg>
		</button>

		<span class="time-display">
			{formatTime(currentTime)} / {formatTime(totalDuration)}
		</span>

		<input
			type="range"
			class="seek-bar"
			min="0"
			max={totalDuration}
			step="0.1"
			value={currentTime}
			oninput={seek}
			disabled={!isLoaded}
		/>
	</div>

	{#if error}
		<p class="player-error">{error}</p>
	{/if}
</div>

<style>
	.player {
		padding: 0.75rem 1rem;
		background: var(--surface-color, #1a1a2e);
		border-radius: 8px;
		border: 1px solid var(--border-color, #555);
	}

	.player-controls {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.btn-control {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		border: none;
		border-radius: 50%;
		background: var(--accent-color, #7c3aed);
		color: white;
		cursor: pointer;
		transition: background 0.2s;
	}

	.btn-control:hover:not(:disabled) {
		background: var(--accent-hover, #6d28d9);
	}

	.btn-control:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.time-display {
		font-size: 0.85rem;
		color: var(--text-muted, #888);
		font-variant-numeric: tabular-nums;
		min-width: 80px;
	}

	.seek-bar {
		flex: 1;
		height: 4px;
		accent-color: var(--accent-color, #7c3aed);
		cursor: pointer;
	}

	.player-error {
		margin-top: 0.5rem;
		color: var(--error-color, #ef4444);
		font-size: 0.85rem;
	}
</style>
