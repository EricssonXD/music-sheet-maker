<script lang="ts">
	let { children } = $props();
</script>

<svelte:head>
	<title>Music Sheet Maker</title>
	<meta name="description" content="Convert MP3 songs to piano sheet music with melody and chords" />
</svelte:head>

<div class="app">
	<header>
		<h1 class="app-title">🎵 Music Sheet Maker</h1>
		<p class="app-subtitle">Upload a song → Get piano sheet music with melody &amp; chords</p>
	</header>

	<main>
		{@render children()}
	</main>

	<footer>
		<p>Powered by Demucs, basic-pitch, music21 &amp; OpenSheetMusicDisplay</p>
	</footer>
</div>

<style>
	:global(*) {
		box-sizing: border-box;
		margin: 0;
		padding: 0;
	}

	:global(body) {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
			Ubuntu, Cantarell, sans-serif;
		background: #0f0f23;
		color: #e0e0e0;
		min-height: 100vh;
	}

	.app {
		max-width: 1100px;
		margin: 0 auto;
		padding: 2rem 1.5rem;
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.app-title {
		font-size: 2rem;
		font-weight: 700;
		background: linear-gradient(135deg, #7c3aed, #a855f7);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.app-subtitle {
		margin-top: 0.5rem;
		color: #888;
		font-size: 1rem;
	}

	main {
		flex: 1;
	}

	footer {
		margin-top: 3rem;
		text-align: center;
		font-size: 0.8rem;
		color: #555;
		padding: 1rem 0;
		border-top: 1px solid #222;
	}

	/* CSS custom properties for components */
	:global(:root) {
		--accent-color: #7c3aed;
		--accent-hover: #6d28d9;
		--surface-color: #1a1a2e;
		--surface-hover: #16213e;
		--border-color: #333;
		--text-primary: #e0e0e0;
		--text-muted: #888;
		--error-color: #ef4444;
		--success-color: #22c55e;
	}

	/* Hide everything except sheet when printing */
	@media print {
		header, footer, :global(.no-print) {
			display: none !important;
		}
		.app {
			padding: 0;
		}
	}
</style>

{@render children()}
