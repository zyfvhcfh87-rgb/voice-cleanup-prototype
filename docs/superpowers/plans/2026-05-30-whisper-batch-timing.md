# Whisper Batch Timing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add timing instrumentation to the current local whisper.cpp batch transcription path without lowering model quality or adding persistent workers.

**Architecture:** Add a small `transcription.timing` module for timing data, parsing, and readable logs. Extend `WhisperCppEngine` to return transcription text plus subprocess timing metadata, and let the UI worker add cleanup/end-to-end timing and model/audio context.

**Tech Stack:** Python 3, PySide6 `QThread`, `subprocess`, `wave`, stdlib `unittest`.

---

### Task 1: Timing Helpers

**Files:**
- Create: `transcription/timing.py`
- Test: `tests/test_timing.py`

- [ ] **Step 1: Write tests for timing parsing and readable formatting**

Use `unittest` to verify whisper.cpp stderr parsing and human-readable summaries include model mode, model name, audio duration, and stage timings.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_timing -v`
Expected: import failure for `transcription.timing`.

- [ ] **Step 3: Implement timing helpers**

Create dataclasses for `StageTiming` and `TranscriptionTimingReport`, parse whisper.cpp timing lines, and format readable log lines.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_timing -v`
Expected: all tests pass.

### Task 2: Whisper Engine Instrumentation

**Files:**
- Modify: `transcription/whisper_engine.py`
- Test: `tests/test_whisper_engine.py`

- [ ] **Step 1: Write tests for command construction and stale output cleanup**

Use a fake subprocess runner and temporary WAV/text files to verify command flags, stale text removal, output fallback, and timing metadata.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_whisper_engine -v`
Expected: missing timing-aware API.

- [ ] **Step 3: Implement minimal timing-aware engine**

Return a `WhisperTranscriptionResult` from a new `transcribe_with_timing()` method, keep `transcribe()` as compatibility wrapper, add safe thread flag, parse whisper timings, and measure file prepare/process/output read stages.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_whisper_engine -v`
Expected: all tests pass.

### Task 3: UI Worker Timing Integration

**Files:**
- Modify: `frontend/ui.py`
- Modify: `audio/recorder.py`

- [ ] **Step 1: Pass audio/model context into `TranscriptionWorker`**

Include model mode label, model file name, audio duration seconds, and release/start time.

- [ ] **Step 2: Measure cleanup and end-to-end timing**

Wrap cleaner execution and final worker timing with monotonic timers.

- [ ] **Step 3: Emit readable timing logs**

Print `[timing]` lines to terminal and write the same lines through `log_event`.

- [ ] **Step 4: Run full verification**

Run: `python -m unittest discover -s tests -v`
Expected: all tests pass.
