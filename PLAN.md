# MP3 → Piano Sheet Music Web App

## Overview

Upload an MP3 song (e.g., "Payphone" by Maroon 5). The app separates the audio into stems, transcribes the vocal melody, detects chords from the harmonic content, and renders a piano sheet with the main melody on the treble staff and chord symbols above.

## Architecture

```
Browser (SvelteKit)                    Server (FastAPI + Python ML)
┌─────────────────────┐               ┌──────────────────────────────┐
│  UploadZone.svelte  │──POST /api/──▶│  Save file, create job       │
│  ProgressBar.svelte │◀──SSE stream──│  run_pipeline():             │
│  SheetRenderer.svelte│              │    1. Demucs → vocals + other│
│  AudioPlayer.svelte │              │    2. basic-pitch → melody    │
│  Export (PDF/PNG)   │◀──GET result──│    3. chord-extractor → chords│
└─────────────────────┘               │    4. music21 → MusicXML     │
                                      └──────────────────────────────┘
```

## Tech Stack

| Layer | Tool | Version | Role |
|-------|------|---------|------|
| Backend framework | FastAPI | latest | REST API + SSE |
| Source separation | Demucs (htdemucs) | v4 | Split vocals/harmony |
| Melody transcription | basic-pitch | 0.4.0 | Vocal → MIDI notes |
| Chord detection | chord-extractor | 0.1.3 | Harmony → chord labels |
| Score assembly | music21 | 9.x | Build MusicXML + key/BPM |
| Frontend framework | SvelteKit | latest | SPA with TypeScript |
| Sheet rendering | OpenSheetMusicDisplay | 1.9.x | MusicXML → SVG |
| MIDI playback | Tone.js + @tonejs/midi | latest | Piano playback |
| Chord utilities | Tonal.js | latest | Chord name formatting |

## Project Structure

```
music-sheet-maker/
├── backend/
│   ├── main.py              ← FastAPI app, model loading, SSE jobs
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── separate.py      ← Demucs stem separation
│   │   ├── transcribe.py    ← basic-pitch vocal melody → notes
│   │   ├── chords.py        ← chord-extractor harmonic analysis
│   │   └── build_score.py   ← music21 MusicXML + MIDI assembly
│   └── pyproject.toml
└── frontend/                ← SvelteKit app
    ├── src/
    │   ├── routes/
    │   │   ├── +page.svelte
    │   │   └── +layout.svelte
    │   └── lib/
    │       ├── components/
    │       │   ├── UploadZone.svelte
    │       │   ├── ProgressBar.svelte
    │       │   ├── SheetRenderer.svelte
    │       │   └── AudioPlayer.svelte
    │       └── api.ts
    ├── package.json
    └── vite.config.ts
```

## Implementation Progress

- [x] **Step 1:** Project setup — git init, .gitignore, PLAN.md
- [x] **Step 2:** Backend project structure + pyproject.toml with dependencies
- [x] **Step 3:** FastAPI main.py — endpoints, model loading, SSE job queue
- [x] **Step 4:** pipeline/separate.py — Demucs stem separation
- [x] **Step 5:** pipeline/transcribe.py — basic-pitch melody transcription
- [x] **Step 6:** pipeline/chords.py — chord-extractor chord detection
- [x] **Step 7:** pipeline/build_score.py — music21 score assembly
- [x] **Step 8:** Scaffold SvelteKit frontend with dependencies
- [x] **Step 9:** UploadZone component — drag-and-drop + file browse
- [x] **Step 10:** ProgressBar component — SSE progress display
- [x] **Step 11:** SheetRenderer component — OSMD MusicXML rendering
- [x] **Step 12:** AudioPlayer component — Tone.js MIDI playback
- [x] **Step 13:** Export — PDF (print) + PNG (canvas)
- [x] **Step 14:** Wire up main +page.svelte + api.ts
- [x] **Step 15:** Dependency fixes & smoke test (torchcodec, ONNX, import paths)
- [ ] **Step 16:** Test with "Payphone" by Maroon 5

## Bugs Fixed

| Date | Issue | Fix |
|------|-------|-----|
| 2026-02-26 | `demucs.api` module doesn't exist | Rewrote separate.py using `demucs.pretrained` + `demucs.apply` |
| 2026-02-26 | `pkg_resources` missing (setuptools 82) | Pinned `setuptools<81` |
| 2026-02-26 | `torchaudio.save` requires torchcodec | Installed `torchcodec` package |
| 2026-02-26 | `tflite_runtime` incompatible with NumPy 2.x | Switched basic-pitch to ONNX backend |
| 2026-02-26 | `from pipeline import ...` ModuleNotFoundError | Changed to `from backend.pipeline import ...` |

## Test Reference

**Primary test song:** "Payphone" by Maroon 5
- Key: Bb major
- BPM: ~110
- Expected chords: Bb → Fm → Ab → Eb (repeating)
- Rap section (~2:30–3:10): expect sparse/noisy melody notes (acceptable)

## System Requirements

- Python 3.10+
- Node.js 18+
- ffmpeg (for audio processing)
- libsndfile1 (for chord-extractor)
