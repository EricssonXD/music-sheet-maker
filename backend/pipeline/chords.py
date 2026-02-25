"""Chord detection from harmonic stem using chord-extractor (Chordino)."""

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

# Module-level singleton
_chordino = None


class ChordEvent(NamedTuple):
    """A detected chord at a specific timestamp."""

    timestamp: float  # seconds
    chord: str  # e.g. "Bb", "Fm", "Am7b5"


def load_model() -> None:
    """Pre-load the Chordino extractor. Call once at server startup."""
    global _chordino
    logger.info("Loading Chordino chord extractor...")
    from chord_extractor.extractors import Chordino

    _chordino = Chordino(roll_on=1)
    logger.info("Chordino loaded.")


def detect_chords(audio_path: str) -> list[ChordEvent]:
    """
    Detect chords from an audio file (ideally the 'other' stem from Demucs).

    Args:
        audio_path: Path to the audio file (WAV preferred).

    Returns:
        List of ChordEvent tuples, sorted by timestamp.
        'N' (no-chord) segments are filtered out.
    """
    if _chordino is None:
        raise RuntimeError("Chordino not loaded. Call load_model() first.")

    logger.info(f"Detecting chords from: {audio_path}")
    raw_chords = _chordino.extract(audio_path)

    # Filter out 'N' (no-chord / silence) and convert to typed events
    chord_events = [
        ChordEvent(timestamp=float(c.timestamp), chord=str(c.chord))
        for c in raw_chords
        if c.chord != "N"
    ]

    logger.info(f"Detected {len(chord_events)} chord changes.")
    if chord_events:
        # Log first few chords for debugging
        preview = chord_events[:8]
        logger.info(
            f"  First chords: {', '.join(f'{c.chord}@{c.timestamp:.1f}s' for c in preview)}"
        )

    return chord_events
