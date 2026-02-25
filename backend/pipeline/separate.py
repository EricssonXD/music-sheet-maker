"""Demucs source separation: split audio into vocals + other stems."""

import os
import logging
from pathlib import Path

import demucs.api
import torch

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once at server startup
_separator: demucs.api.Separator | None = None


def load_model() -> None:
    """Pre-load the Demucs htdemucs model. Call once at server startup."""
    global _separator
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading Demucs htdemucs model on {device}...")
    _separator = demucs.api.Separator(model="htdemucs", device=device)
    logger.info("Demucs model loaded.")


def separate_stems(audio_path: str, output_dir: str) -> tuple[str, str]:
    """
    Separate an audio file into vocals and other (harmonic) stems.

    Args:
        audio_path: Path to the input audio file (mp3/wav/flac/ogg).
        output_dir: Directory to write the separated stem WAV files.

    Returns:
        Tuple of (vocals_path, other_path) — paths to the saved WAV files.
    """
    if _separator is None:
        raise RuntimeError("Demucs model not loaded. Call load_model() first.")

    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Separating stems for: {audio_path}")
    origin, separated = _separator.separate_audio_file(audio_path)

    vocals_path = os.path.join(output_dir, "vocals.wav")
    other_path = os.path.join(output_dir, "other.wav")

    # Save vocals stem (for melody transcription)
    demucs.api.save_audio(
        separated["vocals"],
        vocals_path,
        samplerate=_separator.samplerate,
    )
    logger.info(f"Saved vocals stem: {vocals_path}")

    # Save other stem (for chord detection)
    demucs.api.save_audio(
        separated["other"],
        other_path,
        samplerate=_separator.samplerate,
    )
    logger.info(f"Saved other stem: {other_path}")

    return vocals_path, other_path
