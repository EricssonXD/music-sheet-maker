<script lang="ts">
	/**
	 * UploadZone — drag-and-drop + click-to-browse file input.
	 * Accepts MP3, WAV, FLAC, OGG, M4A audio files.
	 */

	const ACCEPTED = '.mp3,.wav,.flac,.ogg,.m4a,.wma,.aac';
	const MAX_SIZE_MB = 50;

	interface Props {
		onFileSelected: (file: File) => void;
		disabled?: boolean;
	}

	let { onFileSelected, disabled = false }: Props = $props();

	let dragOver = $state(false);
	let errorMsg = $state('');

	function validateAndEmit(file: File) {
		errorMsg = '';

		const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
		const allowed = ['mp3', 'wav', 'flac', 'ogg', 'm4a', 'wma', 'aac'];
		if (!allowed.includes(ext)) {
			errorMsg = `Unsupported file type ".${ext}". Please upload: ${allowed.join(', ')}`;
			return;
		}

		if (file.size > MAX_SIZE_MB * 1024 * 1024) {
			errorMsg = `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max: ${MAX_SIZE_MB} MB.`;
			return;
		}

		onFileSelected(file);
	}

	function handleDrop(e: DragEvent) {
		dragOver = false;
		if (disabled) return;
		const file = e.dataTransfer?.files[0];
		if (file) validateAndEmit(file);
	}

	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) validateAndEmit(file);
		input.value = ''; // reset so same file can be re-selected
	}

	let fileInputRef: HTMLInputElement;
</script>

<div
	class="upload-zone"
	class:drag-over={dragOver}
	class:disabled
	role="button"
	tabindex="0"
	ondragover={(e) => { e.preventDefault(); if (!disabled) dragOver = true; }}
	ondragleave={() => { dragOver = false; }}
	ondrop={(e) => { e.preventDefault(); handleDrop(e); }}
	onclick={() => { if (!disabled) fileInputRef.click(); }}
	onkeydown={(e) => { if (e.key === 'Enter' && !disabled) fileInputRef.click(); }}
>
	<input
		bind:this={fileInputRef}
		type="file"
		accept={ACCEPTED}
		onchange={handleFileInput}
		hidden
	/>

	<div class="upload-content">
		<svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
			<polyline points="17 8 12 3 7 8" />
			<line x1="12" y1="3" x2="12" y2="15" />
		</svg>
		<p class="upload-text">
			{#if disabled}
				Processing...
			{:else}
				<strong>Drop an audio file here</strong> or click to browse
			{/if}
		</p>
		<p class="upload-hint">MP3, WAV, FLAC, OGG, M4A — up to {MAX_SIZE_MB} MB</p>
	</div>

	{#if errorMsg}
		<p class="upload-error">{errorMsg}</p>
	{/if}
</div>

<style>
	.upload-zone {
		border: 2px dashed var(--border-color, #555);
		border-radius: 12px;
		padding: 3rem 2rem;
		text-align: center;
		cursor: pointer;
		transition: all 0.2s ease;
		background: var(--surface-color, #1a1a2e);
	}

	.upload-zone:hover:not(.disabled) {
		border-color: var(--accent-color, #7c3aed);
		background: var(--surface-hover, #16213e);
	}

	.upload-zone.drag-over {
		border-color: var(--accent-color, #7c3aed);
		background: var(--surface-hover, #16213e);
		transform: scale(1.01);
	}

	.upload-zone.disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.upload-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
	}

	.upload-icon {
		width: 48px;
		height: 48px;
		color: var(--text-muted, #888);
	}

	.upload-text {
		font-size: 1.1rem;
		color: var(--text-primary, #e0e0e0);
		margin: 0;
	}

	.upload-hint {
		font-size: 0.85rem;
		color: var(--text-muted, #888);
		margin: 0;
	}

	.upload-error {
		margin-top: 1rem;
		color: var(--error-color, #ef4444);
		font-size: 0.9rem;
	}
</style>
