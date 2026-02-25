"""Melody transcription: vocal audio → MIDI note events via basic-pitch."""

import logging
from typing import NamedTuple

import numpy as np
import pretty_midi

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once at server startup
_model = None


class NoteEvent(NamedTuple):
    """A single transcribed note."""

    start_time: float  # seconds
    end_time: float  # seconds
    pitch_midi: int  # MIDI note number (0-127)
    amplitude: float  # 0.0-1.0
    pitch_bends: list[float] | None  # pitch bend values, if any


def load_model() -> None:
    """Pre-load the basic-pitch model. Call once at server startup."""
    global _model
    logger.info("Loading basic-pitch model...")
    from basic_pitch import FilenameSuffix, build_icassp_2022_model_path

    # Use ONNX model — tflite_runtime is incompatible with NumPy 2.x
    _model = build_icassp_2022_model_path(FilenameSuffix.onnx)
    logger.info(f"basic-pitch ONNX model loaded: {_model}")


def transcribe_melody(
    vocals_path: str,
    minimum_frequency: float = 80.0,
    maximum_frequency: float = 1100.0,
    onset_threshold: float = 0.5,
    frame_threshold: float = 0.3,
) -> tuple[list[NoteEvent], pretty_midi.PrettyMIDI]:
    """
    Transcribe a vocal stem to MIDI note events.

    Args:
        vocals_path: Path to the isolated vocals WAV file.
        minimum_frequency: Lower bound Hz (80 = ~E2, covers bass vocals).
        maximum_frequency: Upper bound Hz (1100 = ~C#6, covers soprano).
        onset_threshold: Sensitivity for note onset detection (0-1).
        frame_threshold: Sensitivity for pitch frame detection (0-1).

    Returns:
        Tuple of (note_events, midi_data):
        - note_events: List of NoteEvent tuples
        - midi_data: PrettyMIDI object for MIDI export
    """
    if _model is None:
        raise RuntimeError("basic-pitch model not loaded. Call load_model() first.")

    from basic_pitch.inference import predict

    logger.info(f"Transcribing melody from: {vocals_path}")
    logger.info(
        f"  freq range: {minimum_frequency}-{maximum_frequency} Hz, "
        f"onset={onset_threshold}, frame={frame_threshold}"
    )

    model_output, midi_data, note_events_raw = predict(
        vocals_path,
        model_or_model_path=_model,
        onset_threshold=onset_threshold,
        frame_threshold=frame_threshold,
        minimum_frequency=minimum_frequency,
        maximum_frequency=maximum_frequency,
        melodia_trick=True,  # Smooth melodic lines — critical for vocals
        midi_tempo=120.0,  # Default tempo for MIDI output
    )

    # Convert raw tuples to typed NoteEvents
    note_events = []
    for event in note_events_raw:
        start_time, end_time, pitch_midi, amplitude, pitch_bends = event
        note_events.append(
            NoteEvent(
                start_time=float(start_time),
                end_time=float(end_time),
                pitch_midi=int(pitch_midi),
                amplitude=float(amplitude),
                pitch_bends=pitch_bends if pitch_bends is not None else None,
            )
        )

    logger.info(f"Transcribed {len(note_events)} note events.")
    return note_events, midi_data
