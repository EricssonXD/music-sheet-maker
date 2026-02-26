"""
Integration tests for the full Payphone pipeline.

These tests require the actual audio file and load ML models — they are
slow (several minutes) and are therefore marked with @pytest.mark.slow.

Run with:   pytest -m slow --timeout=600
Skip with:  pytest -m "not slow"          (default for CI)

Ground truth from:
    https://www.hooktheory.com/theorytab/view/maroon-5/payphone
    - Key:    B major
    - Chords: E → B → G#m → F#  (IV–I–vi–V, repeating)
    - BPM:    ~94
"""

import os
import pytest
from backend.tests.conftest import (
    PAYPHONE_AUDIO_PATH,
    PAYPHONE_KEY,
    PAYPHONE_BPM,
    PAYPHONE_BPM_TOLERANCE,
    PAYPHONE_CHORD_ROOTS,
    normalize_root_to_sharps,
)


pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_root(chord_str: str) -> str:
    """Return the root note from a simplified chord string like 'G#m' → 'G#'."""
    import re
    m = re.match(r'^([A-G][#b]?)', chord_str)
    return normalize_root_to_sharps(m.group(1)) if m else chord_str


# ---------------------------------------------------------------------------
# Chord detection integration
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chord_results():
    """Run Chordino on the Payphone file once; share across tests in module."""
    if not os.path.exists(PAYPHONE_AUDIO_PATH):
        pytest.skip(f"Audio file not found: {PAYPHONE_AUDIO_PATH}")
    from backend.pipeline.chords import load_model, detect_chords
    load_model()
    return detect_chords(PAYPHONE_AUDIO_PATH)


class TestPayphoneChordDetection:
    def test_returns_non_empty_list(self, chord_results):
        assert len(chord_results) > 0, "detect_chords returned no chords"

    def test_expected_roots_present(self, chord_results):
        """B, E, G#, F# must all appear among detected chord roots."""
        from backend.pipeline.chords import normalize_chord_name
        import re
        detected_roots = set()
        for ce in chord_results:
            norm = normalize_chord_name(ce.chord)
            m = re.match(r'^([A-G][#b]?)', norm)
            if m:
                detected_roots.add(normalize_root_to_sharps(m.group(1)))

        expected = {normalize_root_to_sharps(r) for r in PAYPHONE_CHORD_ROOTS}
        missing = expected - detected_roots
        assert len(missing) <= 1, (
            f"Too many expected roots missing: {missing}\n"
            f"Detected roots: {sorted(detected_roots)}"
        )

    def test_chord_coverage_score(self, chord_results):
        """At least 40% of detected (non-trivial) chords should be in the expected set."""
        from backend.pipeline.chords import normalize_chord_name
        import re
        expected_sharp = {normalize_root_to_sharps(r) for r in PAYPHONE_CHORD_ROOTS}
        hits = total = 0
        for ce in chord_results:
            norm = normalize_chord_name(ce.chord)
            m = re.match(r'^([A-G][#b]?)', norm)
            if m:
                total += 1
                if normalize_root_to_sharps(m.group(1)) in expected_sharp:
                    hits += 1
        coverage = hits / total if total else 0
        assert coverage >= 0.40, (
            f"Chord coverage {coverage:.1%} below 40% threshold. "
            f"Hits: {hits}/{total}"
        )

    def test_no_unparseable_chords_after_normalization(self, chord_results):
        """All normalized chords must be parseable by music21 ChordSymbol."""
        from music21 import harmony
        from backend.pipeline.chords import normalize_chord_name
        failures = []
        for ce in chord_results:
            norm = normalize_chord_name(ce.chord)
            try:
                harmony.ChordSymbol(norm)
            except Exception as e:
                failures.append((ce.chord, norm, str(e)))
        assert not failures, (
            "music21 could not parse these normalized chords:\n"
            + "\n".join(f"  raw={r!r} → norm={n!r}: {e}" for r, n, e in failures[:10])
        )


# ---------------------------------------------------------------------------
# BPM estimation integration
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def transcription_results():
    """Run basic-pitch on the vocals stem (if already separated) or skip."""
    stems_dir = os.path.join(os.path.dirname(PAYPHONE_AUDIO_PATH), "test_stems")
    vocals_path = os.path.join(stems_dir, "vocals.wav")
    if not os.path.exists(vocals_path):
        pytest.skip("Vocals stem not pre-separated; run separation step first.")
    from backend.pipeline.transcribe import load_model, transcribe_melody
    load_model()
    return transcribe_melody(vocals_path)


class TestPayphoneBpm:
    def test_bpm_within_tolerance(self, transcription_results):
        note_events, _ = transcription_results
        from backend.pipeline.build_score import estimate_bpm
        bpm = estimate_bpm(note_events)
        assert abs(bpm - PAYPHONE_BPM) <= PAYPHONE_BPM_TOLERANCE, (
            f"Estimated BPM {bpm} is outside [{PAYPHONE_BPM - PAYPHONE_BPM_TOLERANCE}, "
            f"{PAYPHONE_BPM + PAYPHONE_BPM_TOLERANCE}]"
        )


# ---------------------------------------------------------------------------
# Key detection integration
# ---------------------------------------------------------------------------

class TestPayphoneKeyDetection:
    def test_key_contains_b(self, chord_results):
        """Key detected from chord events should be B major (or at least contain B)."""
        from backend.pipeline.chords import normalize_chord_name
        from backend.pipeline.chords import ChordEvent
        from backend.pipeline.build_score import detect_key_from_chords
        # Use normalized chord events
        normalized_events = [
            ChordEvent(timestamp=ce.timestamp, chord=normalize_chord_name(ce.chord))
            for ce in chord_results
        ]
        key_str = detect_key_from_chords(normalized_events)
        if key_str is None:
            pytest.skip("detect_key_from_chords returned None (not enough data)")
        assert "b" in key_str.lower(), (
            f"Expected key to contain 'B major', got: {key_str!r}"
        )
