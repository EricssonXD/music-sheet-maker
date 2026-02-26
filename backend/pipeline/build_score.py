"""Score assembly: combine melody notes + chord symbols into MusicXML via music21."""

import base64
import io
import logging
import tempfile
from pathlib import Path

import pretty_midi
from music21 import (
    clef,
    duration,
    harmony,
    instrument,
    key,
    metadata,
    meter,
    note,
    pitch,
    stream,
    tempo,
)

from .transcribe import NoteEvent
from .chords import ChordEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key detection from chord events
# ---------------------------------------------------------------------------

def detect_key_from_chords(chord_events: list[ChordEvent]) -> str | None:
    """
    Detect the musical key by analysing the set of chords using music21.

    Builds a short music21 stream of ChordSymbol objects and runs the
    Krumhansl-Schmuckler key-finding algorithm on the pitch content.
    This is more reliable than running it on sparse vocal melody alone.

    Args:
        chord_events: List of ChordEvent objects (normalized chord names).

    Returns:
        Key string (e.g. "B major", "G# minor") or None if detection fails
        or there is insufficient data.
    """
    if not chord_events:
        return None

    from music21 import harmony, stream as m21stream

    s = m21stream.Stream()
    for ce in chord_events:
        try:
            cs = harmony.ChordSymbol(ce.chord)
            s.append(cs)
        except Exception:
            continue

    if len(s) < 3:
        return None

    try:
        detected = s.analyze("key")
        return str(detected)
    except Exception as e:
        logger.warning(f"Chord-based key analysis failed: {e}")
        return None


def estimate_bpm(note_events: list[NoteEvent], default_bpm: float = 120.0) -> float:
    """
    Estimate BPM from inter-onset intervals of note events.

    Falls back to default_bpm if there aren't enough notes.
    """
    if len(note_events) < 4:
        return default_bpm

    # Collect onset times
    onsets = sorted(set(n.start_time for n in note_events))
    if len(onsets) < 4:
        return default_bpm

    # Calculate inter-onset intervals
    intervals = [onsets[i + 1] - onsets[i] for i in range(len(onsets) - 1)]
    # Filter out very short intervals (< 0.1s) and very long ones (> 2s)
    intervals = [iv for iv in intervals if 0.1 <= iv <= 2.0]
    if not intervals:
        return default_bpm

    # Median interval → BPM
    intervals.sort()
    median_interval = intervals[len(intervals) // 2]
    raw_bpm = 60.0 / median_interval

    # Snap BPM to reasonable range and common values
    # If raw BPM is too high, halve it; if too low, double it
    while raw_bpm > 200:
        raw_bpm /= 2
    while raw_bpm < 60:
        raw_bpm *= 2

    # Round to nearest integer
    return round(raw_bpm)


def _quantize_to_grid(
    time_seconds: float, bpm: float, grid_divisions: int = 16
) -> float:
    """
    Quantize a time in seconds to the nearest grid position in quarter-note lengths.

    Args:
        time_seconds: Time in seconds.
        bpm: Beats per minute.
        grid_divisions: Grid resolution per quarter note (16 = 1/16 note).

    Returns:
        Quantized offset in quarter-note lengths.
    """
    # Convert seconds to quarter-note lengths
    quarter_notes = time_seconds * (bpm / 60.0)
    # Snap to grid
    quantized = round(quarter_notes * grid_divisions) / grid_divisions
    return max(0.0, quantized)


def _duration_to_quarter_lengths(
    start_s: float, end_s: float, bpm: float, grid_divisions: int = 16
) -> float:
    """
    Convert a duration in seconds to quantized quarter-note lengths.

    Enforces a minimum duration of 1 grid unit.
    """
    dur_seconds = end_s - start_s
    dur_quarters = dur_seconds * (bpm / 60.0)
    # Quantize to grid
    quantized = round(dur_quarters * grid_divisions) / grid_divisions
    min_dur = 1.0 / grid_divisions  # minimum 1 grid unit
    return max(min_dur, quantized)


def build_score(
    note_events: list[NoteEvent],
    chord_events: list[ChordEvent],
    midi_data: pretty_midi.PrettyMIDI | None = None,
    title: str = "Transcription",
    bpm: float | None = None,
) -> dict:
    """
    Build a MusicXML score from melody notes and chord symbols.

    Args:
        note_events: Melody note events from basic-pitch.
        chord_events: Chord events from chord-extractor.
        midi_data: Optional PrettyMIDI object for MIDI export.
        title: Score title (e.g., song name).
        bpm: Tempo in BPM. If None, estimated from note events.

    Returns:
        Dict with keys:
        - musicxml: MusicXML string
        - midi_b64: Base64-encoded MIDI bytes
        - bpm: Detected/estimated BPM
        - key: Detected key signature string (e.g., "Bb major")
    """
    # Estimate BPM if not provided
    if bpm is None:
        bpm = estimate_bpm(note_events)
    logger.info(f"Building score: title='{title}', bpm={bpm}")

    # Create the score
    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = title

    # Create a piano part (treble clef for melody)
    part = stream.Part()
    part.partName = "Piano"
    piano = instrument.Piano()
    part.insert(0, piano)
    part.insert(0, clef.TrebleClef())
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark(number=bpm))

    # Add melody notes
    logger.info(f"Adding {len(note_events)} melody notes...")
    for ne in note_events:
        offset_ql = _quantize_to_grid(ne.start_time, bpm)
        dur_ql = _duration_to_quarter_lengths(ne.start_time, ne.end_time, bpm)

        n = note.Note()
        n.pitch = pitch.Pitch(midi=ne.pitch_midi)
        n.duration = duration.Duration(quarterLength=dur_ql)
        # Scale volume by amplitude (0-127 MIDI velocity range)
        n.volume.velocity = int(min(127, max(20, ne.amplitude * 127)))
        part.insert(offset_ql, n)

    # Add chord symbols
    logger.info(f"Adding {len(chord_events)} chord symbols...")
    for ce in chord_events:
        offset_ql = _quantize_to_grid(ce.timestamp, bpm)
        try:
            cs = harmony.ChordSymbol(ce.chord)
            part.insert(offset_ql, cs)
        except Exception as e:
            # Some chord names from Chordino may not parse in music21
            logger.warning(f"Could not parse chord '{ce.chord}' at {ce.timestamp}s: {e}")
            continue

    # Add part to score
    score.insert(0, part)

    # Create proper measures with bar lines
    logger.info("Creating measures...")
    score.makeMeasures(inPlace=True)

    # Analyze key signature — prefer chord-based analysis (more reliable)
    key_str = "Unknown"
    try:
        chord_key = detect_key_from_chords(chord_events)
        if chord_key:
            key_str = chord_key
            logger.info(f"Key from chords: {key_str}")
        else:
            # Fallback: analyze melody stream
            detected_key = score.analyze("key")
            key_str = str(detected_key)
            logger.info(f"Key from melody: {key_str}")
    except Exception as e:
        logger.warning(f"Key analysis failed: {e}")

    # Serialize to MusicXML
    logger.info("Writing MusicXML...")
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tmp:
        tmp_path = tmp.name
    score.write("musicxml", fp=tmp_path)
    musicxml_str = Path(tmp_path).read_text(encoding="utf-8")
    Path(tmp_path).unlink(missing_ok=True)

    # Serialize MIDI
    midi_b64 = ""
    if midi_data is not None:
        logger.info("Encoding MIDI...")
        midi_buffer = io.BytesIO()
        midi_data.write(midi_buffer)
        midi_b64 = base64.b64encode(midi_buffer.getvalue()).decode("ascii")

    return {
        "musicxml": musicxml_str,
        "midi_b64": midi_b64,
        "bpm": bpm,
        "key": key_str,
    }
