"""
FastAPI backend for MP3 → Piano Sheet Music conversion.

Endpoints:
    POST /api/transcribe     Upload MP3, start processing job
    GET  /api/jobs/{id}/stream   SSE progress stream
    GET  /api/jobs/{id}/result   Fetch completed result
    GET  /health                 Liveness check
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from pipeline import separate, transcribe, chords, build_score

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Job tracking
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "pending"
    SEPARATING = "separating"
    TRANSCRIBING = "transcribing"
    DETECTING_CHORDS = "detecting_chords"
    BUILDING_SCORE = "building_score"
    DONE = "done"
    ERROR = "error"


# In-memory job store (sufficient for single-server personal use)
_jobs: dict[str, dict[str, Any]] = {}

# Stale job cleanup threshold
_JOB_TTL = timedelta(minutes=30)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _update_job(job_id: str, **kwargs: Any) -> None:
    """Update job state."""
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)
        _jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()


def _cleanup_stale_jobs() -> None:
    """Remove jobs older than TTL and delete their temp directories."""
    now = datetime.utcnow()
    stale = [
        jid
        for jid, job in _jobs.items()
        if datetime.fromisoformat(job["created_at"]) + _JOB_TTL < now
    ]
    for jid in stale:
        tmp_dir = _jobs[jid].get("tmp_dir")
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        del _jobs[jid]
    if stale:
        logger.info(f"Cleaned up {len(stale)} stale jobs.")


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

async def run_pipeline(job_id: str, audio_path: str, filename: str) -> None:
    """
    Run the full transcription pipeline in the background.

    Steps:
        1. Separate stems (Demucs)
        2. Transcribe melody (basic-pitch)
        3. Detect chords (chord-extractor)
        4. Build score (music21)
    """
    loop = asyncio.get_event_loop()
    tmp_dir = os.path.dirname(audio_path)
    stems_dir = os.path.join(tmp_dir, "stems")

    try:
        # Step 1: Separate stems
        _update_job(job_id, status=JobStatus.SEPARATING, progress=5,
                    message="Separating vocals and instruments...")
        vocals_path, other_path = await loop.run_in_executor(
            None, separate.separate_stems, audio_path, stems_dir
        )
        _update_job(job_id, progress=40, message="Stems separated.")

        # Step 2: Transcribe melody from vocals
        _update_job(job_id, status=JobStatus.TRANSCRIBING, progress=45,
                    message="Transcribing vocal melody...")
        note_events, midi_data = await loop.run_in_executor(
            None, transcribe.transcribe_melody, vocals_path
        )
        _update_job(job_id, progress=65, message=f"Transcribed {len(note_events)} notes.")

        # Step 3: Detect chords from harmonic stem
        _update_job(job_id, status=JobStatus.DETECTING_CHORDS, progress=70,
                    message="Detecting chords...")
        chord_events = await loop.run_in_executor(
            None, chords.detect_chords, other_path
        )
        _update_job(job_id, progress=80,
                    message=f"Detected {len(chord_events)} chord changes.")

        # Step 4: Build MusicXML score
        _update_job(job_id, status=JobStatus.BUILDING_SCORE, progress=85,
                    message="Building sheet music...")
        # Use filename (without extension) as title
        title = os.path.splitext(filename)[0]
        result = await loop.run_in_executor(
            None,
            build_score.build_score,
            note_events,
            chord_events,
            midi_data,
            title,
            None,  # auto-detect BPM
        )
        _update_job(job_id, progress=95, message="Finalizing...")

        # Add chord list to result for frontend display
        result["chords"] = [
            {"time": ce.timestamp, "chord": ce.chord} for ce in chord_events
        ]
        result["title"] = title
        _update_job(
            job_id,
            status=JobStatus.DONE,
            progress=100,
            message="Done!",
            result=result,
        )
        logger.info(f"Job {job_id} completed: {len(note_events)} notes, "
                     f"{len(chord_events)} chords, key={result['key']}, "
                     f"bpm={result['bpm']}")

    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        _update_job(
            job_id,
            status=JobStatus.ERROR,
            progress=0,
            message=f"Error: {str(e)}",
            error=str(e),
        )


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup, cleanup on shutdown."""
    logger.info("=" * 60)
    logger.info("Starting Music Sheet Maker backend...")
    logger.info("Loading ML models (this may take a minute)...")

    separate.load_model()
    transcribe.load_model()
    chords.load_model()

    logger.info("All models loaded. Server ready.")
    logger.info("=" * 60)

    yield

    # Cleanup temp dirs on shutdown
    for job in _jobs.values():
        tmp_dir = job.get("tmp_dir")
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Music Sheet Maker",
    description="Convert MP3 songs to piano sheet music with melody and chords.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for SvelteKit dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Liveness check."""
    return {"status": "ok", "jobs_active": len(_jobs)}


@app.post("/api/transcribe")
async def transcribe_upload(file: UploadFile):
    """
    Upload an audio file and start the transcription pipeline.

    Accepts: MP3, WAV, FLAC, OGG, M4A, WMA, AAC (max 50 MB).
    Returns: { job_id: string }
    """
    # Cleanup stale jobs first
    _cleanup_stale_jobs()

    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(content) / 1024 / 1024:.1f} MB). Max: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB.",
        )

    # Save to temp directory
    tmp_dir = tempfile.mkdtemp(prefix="msm_")
    audio_path = os.path.join(tmp_dir, f"input{ext}")
    with open(audio_path, "wb") as f:
        f.write(content)
    logger.info(f"Saved upload to: {audio_path} ({len(content) / 1024:.0f} KB)")

    # Create job
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": JobStatus.PENDING,
        "progress": 0,
        "message": "Queued...",
        "result": None,
        "error": None,
        "tmp_dir": tmp_dir,
        "filename": file.filename,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Start pipeline in background
    asyncio.create_task(run_pipeline(job_id, audio_path, file.filename))
    logger.info(f"Created job {job_id} for '{file.filename}'")

    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/stream")
async def job_stream(job_id: str):
    """
    Server-Sent Events stream for job progress.

    Events:
        data: { "status": "separating", "progress": 40, "message": "..." }
        data: { "status": "done", "progress": 100, "message": "Done!" }
        data: { "status": "error", "progress": 0, "message": "Error: ..." }
    """
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_generator():
        last_progress = -1
        while True:
            if job_id not in _jobs:
                break

            job = _jobs[job_id]
            current_progress = job.get("progress", 0)

            # Only send updates when progress changes
            if current_progress != last_progress:
                data = {
                    "status": job["status"],
                    "progress": job["progress"],
                    "message": job["message"],
                }
                yield {"event": "progress", "data": json.dumps(data)}
                last_progress = current_progress

                # Terminal states — send and stop
                if job["status"] in (JobStatus.DONE, JobStatus.ERROR):
                    break

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@app.get("/api/jobs/{job_id}/result")
async def job_result(job_id: str):
    """
    Fetch the completed result of a transcription job.

    Returns the full result dict (musicxml, midi_b64, bpm, key, chords, title)
    only when the job status is 'done'.
    """
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = _jobs[job_id]

    if job["status"] == JobStatus.ERROR:
        raise HTTPException(status_code=500, detail=job.get("error", "Unknown error."))

    if job["status"] != JobStatus.DONE:
        raise HTTPException(
            status_code=202,
            detail=f"Job still processing: {job['status']} ({job['progress']}%)",
        )

    return job["result"]
