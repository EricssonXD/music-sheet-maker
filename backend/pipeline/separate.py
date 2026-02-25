"""Demucs source separation: split audio into vocals + other stems."""

import os
import logging
from pathlib import Path

import torch
from demucs.apply import apply_model
from demucs.audio import save_audio
from demucs.pretrained import get_model

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once at server startup
_model = None
_model_name = "htdemucs"


def load_model() -> None:
    """Pre-load the Demucs htdemucs model. Call once at server startup."""
    global _model
    logger.info(f"Loading Demucs {_model_name} model...")
    _model = get_model(_model_name)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model.to(device)
    _model.eval()
    logger.info(f"Demucs model loaded on {device}. Sources: {_model.sources}")


def separate_stems(audio_path: str, output_dir: str) -> tuple[str, str]:
    """
    Separate an audio file into vocals and other (harmonic) stems.

    Args:
        audio_path: Path to the input audio file (mp3/wav/flac/ogg).
        output_dir: Directory to write the separated stem WAV files.

    Returns:
        Tuple of (vocals_path, other_path) — paths to the saved WAV files.
    """
    if _model is None:
        raise RuntimeError("Demucs model not loaded. Call load_model() first.")

    os.makedirs(output_dir, exist_ok=True)
    device = next(_model.parameters()).device

    logger.info(f"Separating stems for: {audio_path}")

    # Load audio using demucs's own loader
    from demucs.audio import AudioFile, convert_audio
    import torchaudio

    try:
        wav = AudioFile(audio_path).read(
            streams=0,
            samplerate=_model.samplerate,
            channels=_model.audio_channels,
        )
    except Exception:
        # Fallback to torchaudio
        wav, sr = torchaudio.load(str(audio_path))
        wav = convert_audio(wav, sr, _model.samplerate, _model.audio_channels)

    # Normalize
    ref = wav.mean(0)
    wav -= ref.mean()
    wav /= ref.std() + 1e-8

    # Run the model
    logger.info("Running Demucs inference...")
    with torch.no_grad():
        sources = apply_model(
            _model,
            wav[None].to(device),
            device=device,
            shifts=1,
            split=True,
            overlap=0.25,
            progress=True,
        )[0]  # [0] removes batch dimension

    # Denormalize
    sources *= ref.std() + 1e-8
    sources += ref.mean()

    # Find indices for vocals and other
    source_names = _model.sources  # e.g., ['drums', 'bass', 'other', 'vocals']
    vocals_idx = source_names.index("vocals")
    other_idx = source_names.index("other")

    vocals_path = os.path.join(output_dir, "vocals.wav")
    other_path = os.path.join(output_dir, "other.wav")

    # Save stems
    save_audio(
        sources[vocals_idx].cpu(),
        vocals_path,
        samplerate=_model.samplerate,
    )
    logger.info(f"Saved vocals stem: {vocals_path}")

    save_audio(
        sources[other_idx].cpu(),
        other_path,
        samplerate=_model.samplerate,
    )
    logger.info(f"Saved other stem: {other_path}")

    return vocals_path, other_path
