<script lang="ts">
	/**
	 * ProgressBar — displays transcription job progress with animated bar and status label.
	 */

	interface Props {
		progress: number;	// 0-100
		message: string;
		status: string;
	}

	let { progress, message, status }: Props = $props();

	const statusLabels: Record<string, string> = {
		pending: '⏳ Queued',
		separating: '🎵 Separating stems',
		transcribing: '🎹 Transcribing melody',
		detecting_chords: '🎸 Detecting chords',
		building_score: '📝 Building sheet music',
		done: '✅ Done!',
		error: '❌ Error',
	};

	let label = $derived(statusLabels[status] ?? status);
</script>

<div class="progress-container">
	<div class="progress-header">
		<span class="progress-label">{label}</span>
		<span class="progress-pct">{progress}%</span>
	</div>

	<div class="progress-track">
		<div
			class="progress-fill"
			class:error={status === 'error'}
			class:done={status === 'done'}
			style="width: {progress}%"
		></div>
	</div>

	<p class="progress-message">{message}</p>
</div>

<style>
	.progress-container {
		width: 100%;
		max-width: 600px;
		margin: 0 auto;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.progress-label {
		font-size: 1rem;
		font-weight: 600;
		color: var(--text-primary, #e0e0e0);
	}

	.progress-pct {
		font-size: 0.9rem;
		color: var(--text-muted, #888);
		font-variant-numeric: tabular-nums;
	}

	.progress-track {
		width: 100%;
		height: 8px;
		background: var(--surface-color, #1a1a2e);
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent-color, #7c3aed);
		border-radius: 4px;
		transition: width 0.4s ease;
	}

	.progress-fill.done {
		background: var(--success-color, #22c55e);
	}

	.progress-fill.error {
		background: var(--error-color, #ef4444);
	}

	.progress-message {
		margin-top: 0.5rem;
		font-size: 0.85rem;
		color: var(--text-muted, #888);
	}
</style>
