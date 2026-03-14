# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

MP3-to-piano-sheet-music web app. Users upload audio → 4-stage ML pipeline → interactive sheet music with MIDI playback.

**Data flow:** Browser upload → FastAPI → Demucs (stem separation) → basic-pitch ONNX (melody transcription) → chord-extractor (Chordino) → music21 (MusicXML assembly) → OSMD renders sheet, Tone.js plays MIDI.

## Commands

**Backend** (run from repo root, not `backend/`):
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev   # port 5173
cd frontend && npm run check               # TypeScript type-check
```

**Tests:**
```bash
pytest                              # unit tests only (fast, no models)
pytest -m slow --timeout=600        # integration tests (require audio + models)
pytest backend/tests/test_bpm_estimation.py  # single test file
```

## Architecture

### Backend (`backend/`)

- `main.py` — FastAPI app with lifespan model loading, in-memory job store, SSE streaming, background tasks via `run_in_executor`
- `pipeline/` — four modules, each with a `_model = None` singleton, `load_model()` initializer, and a main function that raises `RuntimeError` if model not loaded:
  - `separate.py` → `separate_stems()` — Demucs htdemucs
  - `transcribe.py` → `transcribe_melody()` → `list[NoteEvent]` + `PrettyMIDI`
  - `chords.py` → `detect_chords()` → `list[ChordEvent]`
  - `build_score.py` → `build_score()` — BPM estimation, quantization, key analysis, MusicXML output

Job status flow: `pending → separating → transcribing → detecting_chords → building_score → done | error`

### Frontend (`frontend/`)

- Svelte 5 with runes (`$state`, `$props`, `$effect`) — do NOT use Svelte 4 stores or `export let`
- `src/lib/api.ts` — `uploadFile()`, `subscribeToProgress()` (SSE via `EventSource`), `fetchResult()`
- `src/lib/components/` — `UploadZone`, `ProgressBar`, `SheetRenderer` (OSMD), `AudioPlayer` (Tone.js)
- OSMD and Tone.js are dynamically imported (`await import()`) inside `onMount`/handlers, not top-level
- Dev proxy in `vite.config.ts` forwards `/api/*` and `/health` to `localhost:8000`
- CSS custom properties defined in `+layout.svelte`: `--text-primary`, `--surface-color`, `--accent-color`, etc.

### API Contract

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/transcribe` | POST | Upload audio (multipart) → `{ job_id }` |
| `/api/jobs/{id}/stream` | GET | SSE `progress` events: `{ status, progress, message }` |
| `/api/jobs/{id}/result` | GET | `{ musicxml, midi_b64, bpm, key, title, chords }` |
| `/health` | GET | Liveness check |

## Key Conventions

- **Imports:** Always `backend.pipeline.*` (not relative `pipeline.*`) — backend must start from repo root
- **Chord normalization:** Call `chords.normalize_chord_name()` before passing chord names to music21 or frontend — strips extensions (`"Emaj7"→"E"`) and normalizes flat→sharp (`"Ebm7"→"D#m"`)
- **Key detection:** `build_score.detect_key_from_chords()` uses Krumhansl-Schmuckler on chord stream; falls back to melody analysis only if chord analysis returns `None`
- **Temp cleanup:** Jobs have 30-min TTL; temp dirs cleaned on stale job removal and shutdown
- **Allowed audio:** `.mp3 .wav .flac .ogg .m4a .wma .aac`, max 50 MB

## Known Pitfalls

- **Demucs API:** Use `demucs.pretrained.get_model` + `demucs.apply.apply_model` — NOT `demucs.api`
- **basic-pitch:** Must use ONNX backend (`FilenameSuffix.onnx`) — tflite breaks with NumPy 2.x
- **torchaudio.save:** Requires `torchcodec` package
- **setuptools:** Pinned to `<81` for `pkg_resources` compatibility
- **Chordino accuracy:** vi chord (G#m) is consistently misidentified as Ebm7/Bbm/C#m — integration tests accept ≤1 missing expected root

## Testing Reference

Benchmark song: **"Payphone" by Maroon 5** (`Maron_5_Payphone.mp3` in repo root)
- Key: B major, BPM: ~94, Chords: E → B → G#m → F# (IV–I–vi–V)

Test files in `backend/tests/`: `test_bpm_estimation.py`, `test_chord_normalization.py`, `test_key_detection.py`, `test_payphone_integration.py` (slow/integration)
