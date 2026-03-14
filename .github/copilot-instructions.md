# Music Sheet Maker — Copilot Instructions

## Architecture Overview

This is an MP3-to-piano-sheet-music web app with a **FastAPI backend** (Python ML pipeline) and a **SvelteKit frontend** (TypeScript). The backend runs heavy ML models; the frontend is a thin client that uploads files, streams progress via SSE, and renders results.

**Data flow:** Browser uploads audio → FastAPI saves to temp dir → 4-stage pipeline (Demucs → basic-pitch → chord-extractor → music21) → MusicXML + base64 MIDI returned → OSMD renders sheet, Tone.js plays MIDI.

## Backend (`backend/`)

- **Entry point:** `backend/main.py` — FastAPI app with lifespan-managed model loading, in-memory job store, SSE streaming, and background `asyncio` tasks via `run_in_executor`.
- **Pipeline modules** (`backend/pipeline/`): Each stage is a separate module with a `load_model()` singleton loader and a main function:
  - `separate.py` → `separate_stems()` — Demucs htdemucs stem separation
  - `transcribe.py` → `transcribe_melody()` — basic-pitch ONNX vocal transcription (returns `list[NoteEvent]` + `PrettyMIDI`)
  - `chords.py` → `detect_chords()` — Chordino chord extraction (returns `list[ChordEvent]`)
  - `build_score.py` → `build_score()` — music21 MusicXML assembly with BPM estimation, quantization, key analysis
- **Run backend:** `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` (from repo root, not `backend/`)
- **Imports use `backend.pipeline.*`** (not relative `pipeline.*`) — this was a past bug fix.
- Models are loaded once at startup via `lifespan`. Never re-load models per request.
- **Typed data:** `NoteEvent` and `ChordEvent` are `NamedTuple`s defined in their respective modules and imported by `build_score.py`.
- **Dependencies:** `backend/pyproject.toml` — uses hatchling build system. Key constraint: `setuptools<81` (pkg_resources compat), ONNX backend for basic-pitch (tflite incompatible with NumPy 2.x).

## Frontend (`frontend/`)

- **Svelte 5** with runes (`$state`, `$props`, `$effect`) — do NOT use Svelte 4 stores or `export let` syntax.
- **SvelteKit** with Vite; dev proxy in `vite.config.ts` forwards `/api/*` and `/health` to `localhost:8000`.
- **API client:** `src/lib/api.ts` — `uploadFile()`, `subscribeToProgress()` (SSE via `EventSource`), `fetchResult()`.
- **Components** (`src/lib/components/`):
  - `UploadZone.svelte` — drag-and-drop file input
  - `ProgressBar.svelte` — SSE-driven progress display
  - `SheetRenderer.svelte` — dynamic import of OSMD, reactive re-render via `$effect`
  - `AudioPlayer.svelte` — Tone.js `PolySynth` playback from base64 MIDI
- **Heavy libs loaded dynamically:** OSMD and Tone.js are `await import()`-ed inside `onMount`/handlers, not top-level.
- **Run frontend:** `cd frontend && npm run dev` (port 5173)

## API Contract

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/transcribe` | POST | Upload audio (multipart), returns `{ job_id }` |
| `/api/jobs/{id}/stream` | GET | SSE stream with `progress` events (`{ status, progress, message }`) |
| `/api/jobs/{id}/result` | GET | Final result: `{ musicxml, midi_b64, bpm, key, title, chords }` |
| `/health` | GET | Liveness check |

Job statuses flow: `pending → separating → transcribing → detecting_chords → building_score → done | error`

## Development Workflow

1. **Backend:** From repo root: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` (model loading takes ~1 min on first start)
2. **Frontend:** `cd frontend && npm install && npm run dev`
3. **Type-check frontend:** `cd frontend && npm run check`
4. **Run unit tests (fast, no models):** `pytest` (uses `pyproject.toml` config — runs `backend/tests/` with `-m "not slow"`)
5. **Run integration tests (slow, require audio + models):** `pytest -m slow --timeout=600`

## Testing Strategy

Benchmark song: **"Payphone" by Maroon 5** — audio file is at `Maron_5_-_Payphone_(mp3.pm).mp3` in the repo root.

Reference (from [Hooktheory](https://www.hooktheory.com/theorytab/view/maroon-5/payphone)):
- **Key:** B major
- **BPM:** ~94
- **Chord progression:** E → B → G#m → F# (IV–I–vi–V, repeating)

Test modules in `backend/tests/`:
| File | Type | What it covers |
|---|---|---|
| `test_bpm_estimation.py` | Unit | `estimate_bpm()`, `_quantize_to_grid()`, `_duration_to_quarter_lengths()` |
| `test_chord_normalization.py` | Unit | `normalize_chord_name()` — strips extensions, normalises flat→sharp |
| `test_key_detection.py` | Unit | `detect_key_from_chords()` with idealised chord events |
| `test_payphone_integration.py` | Integration (`@slow`) | Full pipeline on the actual MP3; checks roots, BPM, key |

**Known Chordino accuracy gap:** The vi chord (G#m) is consistently misidentified as Ebm7/Bbm/C#m. B, E, and F# are detected reliably. Integration tests accept ≤1 missing expected root.

## Conventions & Patterns

- **Pipeline modules follow a pattern:** module-level `_model = None` singleton, `load_model()` to initialize, main function that raises `RuntimeError` if model not loaded.
- **Chord normalization:** `chords.normalize_chord_name()` strips extensions (e.g. `"Emaj7"→"E"`, `"G#m7"→"G#m"`) and normalises flat→sharp (`"Ebm7"→"D#m"`). Always call this before passing chord names to music21 or the frontend.
- **Key detection prefers chords over melody:** `build_score.detect_key_from_chords()` runs Krumhansl-Schmuckler analysis on the chord stream; `build_score()` falls back to melody analysis only if chord analysis returns `None`.
- **CSS uses custom properties** (`--text-primary`, `--surface-color`, `--accent-color`, etc.) defined in `+layout.svelte`.
- **Print/export support:** `.no-print` class hides UI chrome; `SheetRenderer` exposes `exportPng()` and `exportPdf()` methods.
- **Temp file cleanup:** Jobs have a 30-min TTL; temp dirs are cleaned on stale job removal and on shutdown.
- **Allowed audio formats:** `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`, `.wma`, `.aac` — max 50 MB.

## Known Pitfalls

- Demucs API changed: use `demucs.pretrained.get_model` + `demucs.apply.apply_model`, NOT `demucs.api`.
- basic-pitch must use ONNX backend (`FilenameSuffix.onnx`), not tflite — NumPy 2.x breaks tflite_runtime.
- Backend must be started from repo root so `backend.pipeline.*` imports resolve correctly.
- `torchaudio.save` requires `torchcodec` package to be installed.

## context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect the context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

### BLOCKED commands — do NOT attempt these

- **curl / wget** — BLOCKED. Any terminal command containing `curl` or `wget` will be intercepted and blocked. Do NOT retry. Instead use `ctx_fetch_and_index(url, source)` to fetch and index web pages, or `ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox.
- **Inline HTTP** — BLOCKED. Any terminal command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` will be intercepted and blocked. Instead use `ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context.
- **WebFetch / fetch** — BLOCKED. Direct web fetching tools are blocked. Instead use `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` to query the indexed content.

### REDIRECTED tools — use sandbox equivalents

- **Terminal / run_in_terminal (>20 lines output)** — Terminal is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands. For everything else, use `ctx_batch_execute(commands, queries)` or `ctx_execute(language: "shell", code: "...")`.
- **read_file (for analysis)** — If reading a file to **edit** it → `read_file` is correct. If reading to **analyze, explore, or summarize** → use `ctx_execute_file(path, language, code)` instead.
- **grep / search (large results)** — Use `ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox.

### Tool selection hierarchy

1. **GATHER**: `ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

### Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `ctx_search(source: "label")` later.

### ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `ctx_stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `ctx_doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `ctx_upgrade` MCP tool, run the returned shell command, display as checklist |
