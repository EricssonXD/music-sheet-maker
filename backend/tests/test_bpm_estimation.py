"""
Unit tests for backend.pipeline.build_score — pure-function BPM estimation
and time quantization. No ML models are required.
"""

import pytest
from backend.pipeline.build_score import estimate_bpm, _quantize_to_grid, _duration_to_quarter_lengths
from backend.pipeline.transcribe import NoteEvent
from backend.tests.conftest import PAYPHONE_BPM, PAYPHONE_BPM_TOLERANCE


def _make_notes_at_bpm(bpm: float, count: int = 16) -> list[NoteEvent]:
    """Generate perfectly-timed quarter-note onsets at a given BPM."""
    interval = 60.0 / bpm
    return [
        NoteEvent(
            start_time=i * interval,
            end_time=(i + 0.9) * interval,
            pitch_midi=60,
            amplitude=0.8,
            pitch_bends=None,
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# estimate_bpm
# ---------------------------------------------------------------------------

class TestEstimateBpm:
    def test_exact_100bpm(self):
        notes = _make_notes_at_bpm(100.0)
        result = estimate_bpm(notes)
        assert abs(result - 100) <= 5

    def test_exact_94bpm_payphone_range(self):
        """BPM estimator should produce a result within tolerance of Payphone's 94 BPM."""
        notes = _make_notes_at_bpm(PAYPHONE_BPM)
        result = estimate_bpm(notes)
        assert abs(result - PAYPHONE_BPM) <= PAYPHONE_BPM_TOLERANCE, (
            f"estimate_bpm returned {result}, expected {PAYPHONE_BPM} ± {PAYPHONE_BPM_TOLERANCE}"
        )

    def test_exact_120bpm(self):
        notes = _make_notes_at_bpm(120.0)
        result = estimate_bpm(notes)
        assert abs(result - 120) <= 5

    def test_too_few_notes_returns_default(self):
        notes = _make_notes_at_bpm(100.0, count=2)
        result = estimate_bpm(notes, default_bpm=120.0)
        assert result == 120.0

    def test_empty_notes_returns_default(self):
        assert estimate_bpm([], default_bpm=100.0) == 100.0

    def test_bpm_folded_into_range(self):
        """Very fast raw BPM (e.g. 32nd-note grid) should be halved into [60,200]."""
        # Notes spaced at 1/4 of a quarter note at 120 BPM → raw BPM would be 480
        notes = _make_notes_at_bpm(480.0)
        result = estimate_bpm(notes)
        assert 60 <= result <= 200, f"estimate_bpm returned {result}, expected value in [60,200]"

    def test_returns_integer(self):
        notes = _make_notes_at_bpm(98.7)
        result = estimate_bpm(notes)
        assert isinstance(result, (int, float))
        assert result == round(result), "estimate_bpm should return rounded integer BPM"


# ---------------------------------------------------------------------------
# _quantize_to_grid
# ---------------------------------------------------------------------------

class TestQuantizeToGrid:
    def test_exact_quarter_note(self):
        # At 120 BPM, 0.5s = 1 quarter note
        result = _quantize_to_grid(0.5, bpm=120.0)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_zero_time(self):
        assert _quantize_to_grid(0.0, bpm=120.0) == 0.0

    def test_snaps_to_grid(self):
        # At 120 BPM, 1/16 note = 0.125s. 0.13s should snap to 1/16 = 0.25 QL
        result = _quantize_to_grid(0.13, bpm=120.0, grid_divisions=16)
        assert result == pytest.approx(0.25, abs=0.01)

    def test_never_negative(self):
        result = _quantize_to_grid(-0.1, bpm=120.0)
        assert result >= 0.0


# ---------------------------------------------------------------------------
# _duration_to_quarter_lengths
# ---------------------------------------------------------------------------

class TestDurationToQuarterLengths:
    def test_quarter_note_at_120bpm(self):
        # 0.5s at 120 BPM = 1 quarter note
        result = _duration_to_quarter_lengths(0.0, 0.5, bpm=120.0)
        assert result == pytest.approx(1.0, abs=0.1)

    def test_minimum_duration_enforced(self):
        # Very short event should be at least 1 grid unit
        result = _duration_to_quarter_lengths(0.0, 0.001, bpm=120.0, grid_divisions=16)
        assert result >= 1.0 / 16
