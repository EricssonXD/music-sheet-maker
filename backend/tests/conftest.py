"""
Shared fixtures and ground-truth reference data for testing.

Reference: https://www.hooktheory.com/theorytab/view/maroon-5/payphone
"""

import os
import pytest

# ---------------------------------------------------------------------------
# Payphone ground truth (from Hooktheory)
# ---------------------------------------------------------------------------

PAYPHONE_AUDIO_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "Maron_5_-_Payphone_(mp3.pm).mp3",
)

# Key: B Major (5 sharps)
PAYPHONE_KEY = "B major"

# BPM: ~94 (verified against metronome; allow ±15 for estimator tolerance)
PAYPHONE_BPM = 94
PAYPHONE_BPM_TOLERANCE = 15

# Chord progression: IV → I → vi → V (repeating throughout all sections)
# In the key of B major: E → B → G#m → F#
PAYPHONE_CHORD_ROOTS = {"B", "E", "G#", "F#"}          # expected root notes
PAYPHONE_CHORD_PROGRESSION = ["E", "B", "G#m", "F#"]   # ordered IV–I–vi–V

# Enharmonic equivalence map (flat → sharp spelling).
# Chordino may return either spelling; treat them as equal when scoring.
ENHARMONIC_SHARPS = {
    "Bb": "A#",
    "Eb": "D#",
    "Ab": "G#",
    "Db": "C#",
    "Gb": "F#",
    "Cb": "B",
    "Fb": "E",
}


def normalize_root_to_sharps(root: str) -> str:
    """Return canonical sharp spelling for a root note."""
    return ENHARMONIC_SHARPS.get(root, root)


def chord_root_matches(detected_root: str, expected_root: str) -> bool:
    """Return True if two root notes are enharmonically equivalent."""
    return normalize_root_to_sharps(detected_root) == normalize_root_to_sharps(expected_root)
