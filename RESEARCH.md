# Research Report: Browser-Based MP3 to Piano Sheet Music Conversion

The transition from raw audio (MP3) to structured musical notation (Sheet Music) is one of the most computationally demanding tasks in music technology, known as **Automatic Music Transcription (AMT)**. In 2026, the technology has matured enough that this entire pipeline can now run **locally in a user's browser** without a backend server, thanks to WebAssembly (WASM) and TensorFlow.js.

---

## 1. The High-Level Architecture

To build this, you need to solve four distinct problems in a linear pipeline. Each step requires a specific tool:

| Layer | Responsibility | Client-Side Tooling |
| --- | --- | --- |
| **1. The Ear** | Decode MP3 and analyze frequencies. | **Web Audio API** & **Essentia.js** |
| **2. The Brain** | Identify polyphonic piano notes (AI). | **@spotify/basic-pitch** or **Magenta.js** |
| **3. The Translator** | Convert raw note data into sheet format. | **musicxml-io** or **midi-xml** |
| **4. The Pen** | Draw the notes, staves, and clefs. | **OpenSheetMusicDisplay (OSMD)** |

---

## 2. Tool Exploration: Picking Your "Brain"

The "Brain" is the most critical part. You need a model that can handle **polyphony** (multiple notes at once), which is standard for piano.

### **Option A: Spotify’s Basic Pitch (Recommended)**

* **What it is:** A lightweight, polyphonic instrument-agnostic model.
* **Pros:** Extremely fast; small footprint (<20MB); very modern TypeScript support.
* **Best for:** General-purpose projects where you want a fast, "snappy" user experience.

### **Option B: Google’s Magenta.js (Onsets and Frames)**

* **What it is:** A specialized model trained specifically for piano transcription.
* **Pros:** Higher accuracy for complex piano pieces (pedal usage, harmonics).
* **Best for:** A dedicated "Piano Transcriber" app where accuracy is prioritized over speed.

---

## 3. The "Notation Gap": MIDI to Sheet Music

The AI models above usually output **MIDI data** (Note C plays at 1.5 seconds). However, sheet music requires **MusicXML** or **ABC Notation** to know which notes are "quarter notes" vs "eighth notes."

* **The Problem:** Transcribing timing into "rhythm" is hard.
* **The Solution:** Use **WebMScore**. This is a WebAssembly port of the MuseScore engine. It can take raw MIDI data and perform "quantization" (snapping notes to a grid) to generate valid MusicXML entirely in the browser.

---

## 4. Framework Selection Matrix

How do you choose which tools to combine? Use this guide:

| If your goal is... | Use this stack |
| --- | --- |
| **Speed & Simplicity** | **Basic Pitch** + **abcjs**. ABC notation is text-based and very easy to render for simple melodies. |
| **Professional Quality** | **Magenta.js** + **OpenSheetMusicDisplay**. This renders "standard" looking sheet music that looks like a printed book. |
| **Lightweight/Mobile** | **Basic Pitch** + **VexFlow**. VexFlow is the lowest-level library; it's harder to code but has the smallest file size. |

---

## 5. Implementation Roadmap (Client-Side)

1. **Audio Ingest:** Use `AudioContext` to decode the MP3 into an `AudioBuffer`.
2. **Inference:** Pass the buffer to `@spotify/basic-pitch`. It will return a list of note events (pitch, start time, end time).
3. **Quantization:** Use a small utility function to round these times to the nearest musical beat (e.g., 120 BPM).
4. **Conversion:** Convert the quantized notes into a **MusicXML** string.
5. **Rendering:** Pass that string to **OpenSheetMusicDisplay**.

### **Recommended Library Cheat Sheet**

* **Transcription:** [`@spotify/basic-pitch`](https://www.google.com/search?q=%5Bhttps://github.com/spotify/basic-pitch-ts%5D(https://github.com/spotify/basic-pitch-ts))
* **Rendering:** [`OpenSheetMusicDisplay`](https://www.google.com/search?q=%5Bhttps://opensheetmusicdisplay.org/%5D(https://opensheetmusicdisplay.org/))
* **Logic/Theory:** [`Tonal.js`](https://www.google.com/search?q=%5Bhttps://github.com/tonaljs/tonal%5D(https://github.com/tonaljs/tonal)) (Great for detecting keys and scales automatically).

---

## 6. Limitations to Keep in Mind

* **Browser Memory:** Large MP3 files (5+ mins) might crash a mobile browser during transcription. Consider chunking the audio.
* **Background Noise:** AMT models work best on "clean" solo piano. If there is singing or drums in the MP3, the sheet music will look like "garbage data."

**Would you like me to generate a starter HTML/JavaScript template that loads the Basic Pitch model and prepares the audio for transcription?**