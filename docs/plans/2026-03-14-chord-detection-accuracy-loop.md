# Chord Detection Accuracy Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the audio path in conftest, then run chord detection on Payphone in a loop to measure and report accuracy against the known E→B→G#m→F# progression.

**Architecture:** Fix the filename mismatch in conftest.py, add a loop-based accuracy script that runs `detect_chords` N times and aggregates coverage stats, then run the existing slow integration tests to confirm they pass.

**Tech Stack:** Python, pytest, chord-extractor (Chordino), music21

---

### Task 1: Fix audio file path in conftest.py

**Files:**
- Modify: `backend/tests/conftest.py`

**Step 1: Verify the actual filename**

```bash
ls /home/ericsson/Code/Python/music-sheet-maker/*.mp3
```
Expected: `Maron_5_Payphone.mp3`

**Step 2: Update PAYPHONE_AUDIO_PATH in conftest.py**

Change:
```python
PAYPHONE_AUDIO_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "Maron_5_-_Payphone_(mp3.pm).mp3",
)
```
To:
```python
PAYPHONE_AUDIO_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "Maron_5_Payphone.mp3",
)
```

**Step 3: Verify the path resolves**

```bash
cd /home/ericsson/Code/Python/music-sheet-maker && python -c "
from backend.tests.conftest import PAYPHONE_AUDIO_PATH
import os
print('exists:', os.path.exists(PAYPHONE_AUDIO_PATH))
print('path:', PAYPHONE_AUDIO_PATH)
"
```
Expected: `exists: True`

**Step 4: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "fix(tests): correct Payphone audio filename in conftest"
```

---

### Task 2: Add chord detection accuracy loop script

**Files:**
- Create: `backend/tests/chord_accuracy_loop.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
Chord detection accuracy loop for Payphone by Maroon 5.

Runs Chordino N times on the full audio file and reports:
- Per-run coverage (% of detected chords matching expected roots)
- Whether all 4 expected roots were found each run
- Aggregate stats across all runs

Usage (from repo root):
    python -m backend.tests.chord_accuracy_loop [--runs N]

Expected chords: E → B → G#m → F#  (IV–I–vi–V in B major)
"""

import argparse
import re
import sys

from backend.pipeline.chords import load_model, detect_chords, normalize_chord_name
from backend.tests.conftest import (
    PAYPHONE_AUDIO_PATH,
    PAYPHONE_CHORD_ROOTS,
    normalize_root_to_sharps,
)


def extract_root(chord_str: str) -> str:
    m = re.match(r'^([A-G][#b]?)', chord_str)
    return normalize_root_to_sharps(m.group(1)) if m else chord_str


def run_once() -> dict:
    """Run chord detection once and return accuracy metrics."""
    chords = detect_chords(PAYPHONE_AUDIO_PATH)

    expected_roots = {normalize_root_to_sharps(r) for r in PAYPHONE_CHORD_ROOTS}
    detected_roots = set()
    hits = total = 0

    for ce in chords:
        norm = normalize_chord_name(ce.chord)
        root = extract_root(norm)
        detected_roots.add(root)
        total += 1
        if root in expected_roots:
            hits += 1

    coverage = hits / total if total else 0.0
    missing = expected_roots - detected_roots

    return {
        "total_chords": total,
        "hits": hits,
        "coverage": coverage,
        "detected_roots": sorted(detected_roots),
        "missing_roots": sorted(missing),
        "all_roots_found": len(missing) == 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Chord detection accuracy loop")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs (default: 3)")
    args = parser.parse_args()

    import os
    if not os.path.exists(PAYPHONE_AUDIO_PATH):
        print(f"ERROR: Audio file not found: {PAYPHONE_AUDIO_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading Chordino model...")
    load_model()
    print(f"Running chord detection {args.runs} time(s) on Payphone...\n")

    results = []
    for i in range(1, args.runs + 1):
        print(f"--- Run {i}/{args.runs} ---")
        r = run_once()
        results.append(r)
        print(f"  Total chords detected : {r['total_chords']}")
        print(f"  Hits (expected roots) : {r['hits']}")
        print(f"  Coverage              : {r['coverage']:.1%}")
        print(f"  Detected roots        : {r['detected_roots']}")
        print(f"  Missing roots         : {r['missing_roots'] or 'none'}")
        print(f"  All 4 roots found     : {r['all_roots_found']}")
        print()

    # Aggregate
    avg_coverage = sum(r["coverage"] for r in results) / len(results)
    runs_all_found = sum(1 for r in results if r["all_roots_found"])

    print("=== AGGREGATE SUMMARY ===")
    print(f"  Runs              : {args.runs}")
    print(f"  Avg coverage      : {avg_coverage:.1%}  (threshold: 40%)")
    print(f"  All-roots runs    : {runs_all_found}/{args.runs}")
    print(f"  PASS (avg ≥ 40%)  : {'YES' if avg_coverage >= 0.40 else 'NO'}")

    # Exit non-zero if below threshold
    sys.exit(0 if avg_coverage >= 0.40 else 1)


if __name__ == "__main__":
    main()
```

**Step 2: Run it (single pass to verify it works)**

```bash
cd /home/ericsson/Code/Python/music-sheet-maker && python -m backend.tests.chord_accuracy_loop --runs 1
```
Expected: prints coverage ≥ 40%, exits 0.

**Step 3: Commit**

```bash
git add backend/tests/chord_accuracy_loop.py
git commit -m "feat(tests): add chord detection accuracy loop script"
```

---

### Task 3: Run the full accuracy loop (3 runs)

**Step 1: Run 3 times and capture output**

```bash
cd /home/ericsson/Code/Python/music-sheet-maker && python -m backend.tests.chord_accuracy_loop --runs 3
```

Expected output shape:
```
--- Run 1/3 ---
  Total chords detected : <N>
  Coverage              : XX.X%   ← should be ≥ 40%
  Missing roots         : ['G#'] or none   ← G#m is the known weak spot
...
=== AGGREGATE SUMMARY ===
  Avg coverage      : XX.X%
  PASS (avg ≥ 40%)  : YES
```

**Step 2: If coverage < 40% on any run, investigate**

Check which roots are consistently missing. The known Chordino limitation is G#m (vi chord) being misidentified as Ebm7/Bbm/C#m. If B, E, or F# are also missing, that indicates a deeper issue — check that the full audio file is being passed (not a stem).

---

### Task 4: Run the existing pytest integration suite

**Step 1: Run slow integration tests**

```bash
cd /home/ericsson/Code/Python/music-sheet-maker && pytest -m slow --timeout=600 -v backend/tests/test_payphone_integration.py
```

Expected: all tests pass (or at most `test_expected_roots_present` allows 1 missing root).

**Step 2: Run fast unit tests to confirm nothing broke**

```bash
cd /home/ericsson/Code/Python/music-sheet-maker && pytest -v
```
Expected: all pass.

**Step 3: Commit results note to PLAN.md**

Update `PLAN.md` Step 16 checkbox and add a results line:
```markdown
- [x] **Step 16:** Test with "Payphone" by Maroon 5
  - Chord coverage: ~XX% avg over 3 runs; B/E/F# detected reliably; G#m known gap
```

```bash
git add PLAN.md
git commit -m "docs: mark Step 16 complete, record chord accuracy results"
```
