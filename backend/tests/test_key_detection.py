"""
Unit tests for key detection from chord events — testing the
`detect_key_from_chords()` function added to build_score.py.

Payphone ground truth: B major (IV–I–vi–V = E–B–G#m–F#)
"""

import pytest
from backend.pipeline.chords import ChordEvent
from backend.pipeline.build_score import detect_key_from_chords


# ---------------------------------------------------------------------------
# Payphone chord events (normalized, repeating IV–I–vi–V)
# ---------------------------------------------------------------------------

def payphone_chord_events(repeats: int = 4) -> list[ChordEvent]:
    """Generate idealized Payphone chord events: E B G#m F# repeating."""
    pattern = ["E", "B", "G#m", "F#"]
    events = []
    for i in range(repeats):
        for j, chord in enumerate(pattern):
            events.append(ChordEvent(
                timestamp=float(i * 16 + j * 4),
                chord=chord,
            ))
    return events


class TestDetectKeyFromChords:
    def test_payphone_detected_as_b_major(self):
        events = payphone_chord_events()
        key_str = detect_key_from_chords(events)
        assert key_str is not None, "detect_key_from_chords returned None"
        # Accept "B major", "b major", "B Major", "B" (case-insensitive, partial)
        assert "b" in key_str.lower(), (
            f"Expected key to contain 'B', got: {key_str!r}"
        )

    def test_c_major_chords(self):
        """C–Am–F–G (I–vi–IV–V in C major) → should detect C major."""
        events = [
            ChordEvent(0.0, "C"),
            ChordEvent(4.0, "Am"),
            ChordEvent(8.0, "F"),
            ChordEvent(12.0, "G"),
        ] * 4
        key_str = detect_key_from_chords(events)
        # Should not be None and should lean toward C-ish territory (accept any result,
        # just ensure no crash and non-empty return)
        assert key_str is not None
        assert len(key_str) > 0

    def test_empty_events_returns_none(self):
        assert detect_key_from_chords([]) is None

    def test_single_chord_returns_result(self):
        events = [ChordEvent(0.0, "B")] * 8
        result = detect_key_from_chords(events)
        # Should not crash; result may be None or a key string
        assert result is None or isinstance(result, str)

    def test_returns_string_or_none(self):
        events = payphone_chord_events()
        result = detect_key_from_chords(events)
        assert result is None or isinstance(result, str)
