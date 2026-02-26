"""Chord detection from harmonic stem using chord-extractor (Chordino)."""

import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chord name normalisation
# ---------------------------------------------------------------------------

# Enharmonic flat→sharp mapping (consistent with sharp-key spellings)
_FLAT_TO_SHARP: dict[str, str] = {
    "Bb": "A#",
    "Eb": "D#",
    "Ab": "G#",
    "Db": "C#",
    "Gb": "F#",
    "Cb": "B",
    "Fb": "E",
}

# Regex: captures ROOT (e.g. "G#", "Bb"), QUALITY ("m", "dim", "aug" or empty),
# EXTENSIONS (everything up to optional slash), and optional /BASS.
_CHORD_RE = re.compile(
    r"^([A-G][#b]?)"           # group 1: root
    r"(m(?!aj)|dim|aug)?"      # group 2: quality token (minor/dim/aug; not 'maj')
    r"[^/]*"                   # extensions to ignore
    r"(?:/[A-G][#b]?)?$"       # optional /bass to drop
)


def normalize_chord_name(raw: str) -> str:
    """
    Simplify a Chordino chord name to a plain "Root[quality]" string that
    music21 ChordSymbol can reliably parse.

    Examples::

        normalize_chord_name("Emaj7")   → "E"
        normalize_chord_name("G#m7")    → "G#m"
        normalize_chord_name("Ebm7")    → "D#m"   (Eb→D# enharmonic)
        normalize_chord_name("Eb7/G")   → "D#"    (drop extension + bass)
        normalize_chord_name("Bbm")     → "A#m"   (Bb→A# enharmonic)
        normalize_chord_name("Bdim7")   → "Bdim"
        normalize_chord_name("F#6")     → "F#"

    Args:
        raw: Chord name as returned by Chordino (e.g. "Emaj7", "Eb7/G").

    Returns:
        Simplified chord name suitable for music21 and the frontend.
    """
    m = _CHORD_RE.match(raw.strip())
    if not m:
        # Unrecognised format — return as-is so we don't silently drop data
        logger.debug(f"normalize_chord_name: could not parse {raw!r}, returning as-is")
        return raw

    root = m.group(1)
    quality = m.group(2) or ""   # "m", "dim", "aug", or ""

    # Normalise flat spellings → sharp
    root = _FLAT_TO_SHARP.get(root, root)

    return root + quality

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

    # Filter out 'N' (no-chord / silence), normalize names, and convert to typed events
    chord_events = []
    for c in raw_chords:
        if c.chord == "N":
            continue
        raw_name = str(c.chord)
        normalized = normalize_chord_name(raw_name)
        if raw_name != normalized:
            logger.debug(f"  Chord normalized: {raw_name!r} → {normalized!r}")
        chord_events.append(ChordEvent(timestamp=float(c.timestamp), chord=normalized))

    logger.info(f"Detected {len(chord_events)} chord changes.")
    if chord_events:
        # Log first few chords for debugging
        preview = chord_events[:8]
        logger.info(
            f"  First chords: {', '.join(f'{c.chord}@{c.timestamp:.1f}s' for c in preview)}"
        )

    return chord_events
