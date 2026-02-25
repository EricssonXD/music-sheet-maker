<script lang="ts">
	import UploadZone from '$lib/components/UploadZone.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import SheetRenderer from '$lib/components/SheetRenderer.svelte';
	import AudioPlayer from '$lib/components/AudioPlayer.svelte';
	import { uploadFile, subscribeToProgress, fetchResult } from '$lib/api';
	import type { ProgressEvent, TranscriptionResult } from '$lib/api';

	// App state
	type AppState = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

	let appState = $state<AppState>('idle');
	let fileName = $state('');
	let errorMsg = $state('');

	// Progress state
	let progress = $state(0);
	let progressMsg = $state('');
	let progressStatus = $state('pending');

	// Result state
	let result = $state<TranscriptionResult | null>(null);

	// Sheet renderer ref for export
	let sheetRenderer = $state<SheetRenderer>();

	async function handleFileSelected(file: File) {
		fileName = file.name;
		errorMsg = '';
		result = null;

		try {
			// Upload
			appState = 'uploading';
			progress = 0;
			progressMsg = 'Uploading...';
			progressStatus = 'pending';

			const { job_id } = await uploadFile(file);

			// Subscribe to progress
			appState = 'processing';
			await subscribeToProgress(job_id, (event: ProgressEvent) => {
				progress = event.progress;
				progressMsg = event.message;
				progressStatus = event.status;
			});

			// Fetch result
			const data = await fetchResult(job_id);
			result = data;
			appState = 'done';
		} catch (e: any) {
			errorMsg = e.message || 'An error occurred.';
			appState = 'error';
		}
	}

	function reset() {
		appState = 'idle';
		fileName = '';
		errorMsg = '';
		result = null;
		progress = 0;
		progressMsg = '';
		progressStatus = 'pending';
	}
</script>

<div class="page">
	{#if appState === 'idle'}
		<UploadZone onFileSelected={handleFileSelected} />
	{:else if appState === 'uploading' || appState === 'processing'}
		<div class="processing-section">
			<p class="file-name no-print">🎵 {fileName}</p>
			<ProgressBar {progress} message={progressMsg} status={progressStatus} />
		</div>
	{:else if appState === 'done' && result}
		<div class="result-section">
			<div class="toolbar no-print">
				<button class="btn" onclick={reset}>← Upload another</button>
				<div class="toolbar-right">
					<button class="btn btn-accent" onclick={() => sheetRenderer?.exportPng()}>
						📷 Export PNG
					</button>
					<button class="btn btn-accent" onclick={() => sheetRenderer?.exportPdf()}>
						📄 Export PDF
					</button>
				</div>
			</div>

			<SheetRenderer
				bind:this={sheetRenderer}
				musicXml={result.musicxml}
				title={result.title}
				keySignature={result.key}
				bpm={result.bpm}
			/>

			<div class="no-print" style="margin-top: 1rem;">
				<AudioPlayer midiB64={result.midi_b64} />
			</div>

			{#if result.chords.length > 0}
				<div class="chords-summary no-print">
					<h3>Chord Progression</h3>
					<div class="chord-tags">
						{#each dedupChords(result.chords) as chord}
							<span class="chord-tag">{chord}</span>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{:else if appState === 'error'}
		<div class="error-section">
			<p class="error-text">❌ {errorMsg}</p>
			<button class="btn" onclick={reset}>Try again</button>
		</div>
	{/if}
</div>

<script lang="ts" module>
	// Helper: deduplicate chord names while preserving order
	function dedupChords(chords: { time: number; chord: string }[]): string[] {
		const seen = new Set<string>();
		const unique: string[] = [];
		for (const c of chords) {
			if (!seen.has(c.chord)) {
				seen.add(c.chord);
				unique.push(c.chord);
			}
		}
		return unique;
	}
</script>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.processing-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.5rem;
		padding: 2rem 0;
	}

	.file-name {
		font-size: 1.1rem;
		color: var(--text-primary);
		font-weight: 500;
	}

	.result-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.toolbar-right {
		display: flex;
		gap: 0.5rem;
	}

	.btn {
		padding: 0.5rem 1rem;
		font-size: 0.9rem;
		border: 1px solid var(--border-color);
		border-radius: 6px;
		background: var(--surface-color);
		color: var(--text-primary);
		cursor: pointer;
		transition: background 0.2s;
	}

	.btn:hover {
		background: var(--surface-hover);
	}

	.btn-accent {
		background: var(--accent-color);
		border-color: var(--accent-color);
		color: white;
	}

	.btn-accent:hover {
		background: var(--accent-hover);
	}

	.chords-summary {
		padding: 1rem;
		background: var(--surface-color);
		border-radius: 8px;
		border: 1px solid var(--border-color);
	}

	.chords-summary h3 {
		font-size: 0.95rem;
		color: var(--text-muted);
		margin-bottom: 0.75rem;
	}

	.chord-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.chord-tag {
		padding: 0.3rem 0.75rem;
		font-size: 0.9rem;
		font-weight: 600;
		background: var(--surface-hover);
		color: var(--accent-color);
		border-radius: 20px;
		border: 1px solid var(--border-color);
	}

	.error-section {
		text-align: center;
		padding: 3rem 0;
	}

	.error-text {
		color: var(--error-color);
		font-size: 1.1rem;
		margin-bottom: 1rem;
	}
</style>
