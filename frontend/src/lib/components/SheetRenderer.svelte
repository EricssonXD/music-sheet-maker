<script lang="ts">
	/**
	 * SheetRenderer — renders MusicXML as SVG sheet music using OpenSheetMusicDisplay.
	 */
	import { onMount, onDestroy } from 'svelte';

	interface Props {
		musicXml: string;
		title?: string;
		keySignature?: string;
		bpm?: number;
	}

	let { musicXml, title = '', keySignature = '', bpm = 0 }: Props = $props();

	let containerRef: HTMLDivElement;
	let osmd: any = null;
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		try {
			const { OpenSheetMusicDisplay } = await import('opensheetmusicdisplay');
			osmd = new OpenSheetMusicDisplay(containerRef, {
				autoResize: true,
				backend: 'svg',
				drawTitle: true,
				drawComposer: false,
				drawingParameters: 'default',
			});
			loading = false;
		} catch (e: any) {
			error = `Failed to load sheet renderer: ${e.message}`;
			loading = false;
		}
	});

	// Reactive: re-render when musicXml changes
	$effect(() => {
		if (osmd && musicXml) {
			loading = true;
			error = '';
			osmd.clear();
			osmd
				.load(musicXml)
				.then(() => {
					osmd.render();
					loading = false;
				})
				.catch((e: any) => {
					error = `Failed to render sheet: ${e.message}`;
					loading = false;
				});
		}
	});

	onDestroy(() => {
		if (osmd) {
			osmd.clear();
		}
	});

	/**
	 * Export the sheet as PNG.
	 */
	export function exportPng() {
		if (!containerRef) return;

		const svgEl = containerRef.querySelector('svg');
		if (!svgEl) return;

		const svgData = new XMLSerializer().serializeToString(svgEl);
		const canvas = document.createElement('canvas');
		const ctx = canvas.getContext('2d')!;

		const img = new Image();
		const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
		const url = URL.createObjectURL(svgBlob);

		img.onload = () => {
			// Scale up for higher resolution
			const scale = 2;
			canvas.width = img.width * scale;
			canvas.height = img.height * scale;
			ctx.scale(scale, scale);
			ctx.fillStyle = 'white';
			ctx.fillRect(0, 0, img.width, img.height);
			ctx.drawImage(img, 0, 0);

			canvas.toBlob((blob) => {
				if (!blob) return;
				const a = document.createElement('a');
				a.href = URL.createObjectURL(blob);
				a.download = `${title || 'sheet-music'}.png`;
				a.click();
				URL.revokeObjectURL(a.href);
			}, 'image/png');

			URL.revokeObjectURL(url);
		};
		img.src = url;
	}

	/**
	 * Export as PDF via browser print dialog.
	 */
	export function exportPdf() {
		window.print();
	}
</script>

{#if keySignature || bpm}
	<div class="sheet-meta">
		{#if bpm}
			<span class="meta-badge">♩ = {bpm}</span>
		{/if}
		{#if keySignature}
			<span class="meta-badge">Key: {keySignature}</span>
		{/if}
		{#if title}
			<span class="meta-badge title-badge">{title}</span>
		{/if}
	</div>
{/if}

<div class="sheet-container" bind:this={containerRef}>
	{#if loading}
		<div class="sheet-loading">
			<div class="spinner"></div>
			<p>Rendering sheet music...</p>
		</div>
	{/if}
	{#if error}
		<div class="sheet-error">
			<p>{error}</p>
		</div>
	{/if}
</div>

<style>
	.sheet-meta {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
		margin-bottom: 1rem;
		padding: 0.75rem 1rem;
		background: var(--surface-color, #1a1a2e);
		border-radius: 8px;
	}

	.meta-badge {
		display: inline-flex;
		align-items: center;
		padding: 0.25rem 0.75rem;
		font-size: 0.85rem;
		font-weight: 500;
		color: var(--text-primary, #e0e0e0);
		background: var(--surface-hover, #16213e);
		border-radius: 20px;
		border: 1px solid var(--border-color, #555);
	}

	.title-badge {
		font-weight: 700;
		color: var(--accent-color, #7c3aed);
	}

	.sheet-container {
		width: 100%;
		min-height: 200px;
		background: white;
		border-radius: 8px;
		padding: 1rem;
		overflow-x: auto;
	}

	.sheet-loading,
	.sheet-error {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		color: #666;
	}

	.sheet-error {
		color: var(--error-color, #ef4444);
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid #ddd;
		border-top-color: var(--accent-color, #7c3aed);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Print styles: only show the sheet */
	@media print {
		.sheet-meta {
			display: none;
		}
		.sheet-container {
			padding: 0;
			border-radius: 0;
		}
	}
</style>
