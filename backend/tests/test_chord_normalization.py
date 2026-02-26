"""
Unit tests for chord name normalization — the function that strips Chordino's
extension-heavy names (e.g. "Emaj7", "F#6", "Eb7/G") down to simple root+quality
that music21 and the frontend can consume cleanly.

Reference chord set for Payphone (B major):  E  B  G#m  F#  (IV–I–vi–V)
"""

import pytest
from backend.pipeline.chords import normalize_chord_name
from backend.tests.conftest import (
    PAYPHONE_CHORD_ROOTS,
    chord_root_matches,
    normalize_root_to_sharps,
)


# ---------------------------------------------------------------------------
# normalize_chord_name — maps Chordino raw strings to simple "Root[m]" form
# ---------------------------------------------------------------------------

class TestNormalizeChordName:
    # Major chords — strip extensions
    @pytest.mark.parametrize("raw,expected", [
        ("B",       "B"),
        ("B6",      "B"),
        ("Emaj7",   "E"),
        ("Emaj9",   "E"),
        ("F#6",     "F#"),
        ("F#",      "F#"),
        ("C#",      "C#"),
        ("C#sus4",  "C#"),
        ("Aadd9",   "A"),
    ])
    def test_major_chords(self, raw, expected):
        assert normalize_chord_name(raw) == expected

    # Minor chords — keep 'm', strip extensions
    @pytest.mark.parametrize("raw,expected", [
        ("G#m",     "G#m"),
        ("G#m7",    "G#m"),
        ("Ebm7",    "D#m"),    # Eb → D# (sharp spelling) + strip 7
        ("Bbm",     "A#m"),    # Bb → A#
        ("C#m7",    "C#m"),
        ("F#m",     "F#m"),
        ("Abm",     "G#m"),    # Ab → G#
    ])
    def test_minor_chords(self, raw, expected):
        assert normalize_chord_name(raw) == expected

    # Slash chords — drop the bass note
    @pytest.mark.parametrize("raw,expected", [
        ("Eb7/G",   "D#"),     # Eb→D#, strip 7, drop /G
        ("F#/A#",   "F#"),
        ("G/B",     "G"),
        ("Am/C",    "Am"),
    ])
    def test_slash_chords(self, raw, expected):
        assert normalize_chord_name(raw) == expected

    # dim/aug — preserve quality
    @pytest.mark.parametrize("raw,expected", [
        ("Bdim",    "Bdim"),
        ("Cdim7",   "Cdim"),
        ("Faug",    "Faug"),
    ])
    def test_dim_aug_chords(self, raw, expected):
        assert normalize_chord_name(raw) == expected

    def test_returns_string(self):
        assert isinstance(normalize_chord_name("B"), str)

    def test_no_crash_on_unusual_input(self):
        # Should return something without raising
        result = normalize_chord_name("Xmaj13#11")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Payphone chord set coverage — after normalization, the Chordino output
# from the actual song (sampled from a real run) should cover B, E, G#, F#
# ---------------------------------------------------------------------------

# Raw strings captured from a Chordino run on the Payphone audio file.
# This acts as a regression fixture — if normalization breaks, these fail.
PAYPHONE_RAW_SAMPLE = [
    "B", "Emaj7", "F#6", "B", "Emaj7", "C#", "B", "Ebm7",
    "Emaj7", "F#", "B", "Eb7/G", "B", "C#m7", "B", "Eb7/G",
    "B6", "E", "F#6", "B", "Bbm", "B",
]

class TestPayphoneNormalizationCoverage:
    def test_expected_roots_mostly_present(self):
        """After normalization, at least 3/4 expected roots (B, E, G#, F#) should
        appear in the sample.

        Known limitation: Chordino consistently misidentifies the vi chord (G#m)
        in Payphone, returning Ebm7/Bbm/C#m instead. This is a Chordino accuracy
        issue, not a normalization bug — we allow 1 missing root.
        """
        normalized = [normalize_chord_name(c) for c in PAYPHONE_RAW_SAMPLE]
        # Extract root notes (strip trailing 'm', 'dim', 'aug')
        import re
        roots_found = set()
        for chord in normalized:
            m = re.match(r'^([A-G][#b]?)', chord)
            if m:
                roots_found.add(normalize_root_to_sharps(m.group(1)))

        expected_sharp_roots = {normalize_root_to_sharps(r) for r in PAYPHONE_CHORD_ROOTS}
        missing = expected_sharp_roots - roots_found
        assert len(missing) <= 1, (
            f"More than 1 expected root missing after normalization: {missing}\n"
            f"Roots found: {roots_found}\n"
            "Known gap: G#m (vi) is frequently misidentified as Ebm/Bbm by Chordino."
        )

    def test_normalized_are_music21_parseable(self):
        """All normalized chords from the sample should be parseable by music21."""
        from music21 import harmony
        normalized = [normalize_chord_name(c) for c in PAYPHONE_RAW_SAMPLE]
        failures = []
        for chord in normalized:
            try:
                harmony.ChordSymbol(chord)
            except Exception as e:
                failures.append((chord, str(e)))
        assert not failures, (
            f"music21 failed to parse these normalized chords:\n"
            + "\n".join(f"  {c!r}: {e}" for c, e in failures)
        )
