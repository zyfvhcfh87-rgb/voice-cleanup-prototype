# Whisper Batch Timing Design

## Goal

Measure the existing local whisper.cpp batch transcription path before considering a persistent worker. The first implementation keeps the current model quality, does not chunk recordings, and does not implement a long-lived Whisper process.

## Scope

Instrument the current path from recording stop through final cleaned text. Each run should show the selected quality mode (`Fast`, `Balanced`, or `Accurate`), the model file name, audio duration in seconds, and readable timing lines in terminal output and the app log.

## Timing Data

Each dictation run records:

- `recording_stop_total`: stopping the stream, concatenating frames, and writing WAV.
- `whisper_total`: full `whisper-cli.exe` call from Python.
- `whisper_file_prepare`: validation, stale output cleanup, and command construction.
- `whisper_process_elapsed`: subprocess wall time.
- `whisper_output_read`: generated text/stdout read time.
- `cleanup_total`: ASR post-processing or selected cleanup backend.
- `end_to_end_after_release`: release/stop action through final UI completion.
- `audio_duration_seconds`: WAV duration or recorder duration.
- `model_mode`: user-facing quality mode.
- `model_name`: model file name.

Whisper startup/model loading and inference both happen inside one CLI subprocess. The implementation parses whisper.cpp timing lines such as `load time`, `encode time`, `decode time`, and `total time` when the bundled build emits them. If available, these lines answer how much time is spent loading the model versus transcribing. If unavailable, the report clearly marks those fields as unavailable.

## Whisper Invocation

The implementation may add safe speed flags only when they do not lower model quality:

- Keep the selected model unchanged.
- Prefer explicit language when configured later.
- Avoid unused output formats.
- Set thread count conservatively based on CPU count.
- Do not switch to smaller models, quantization changes, aggressive beam changes, or chunking.

## Output Handling

Before invoking whisper.cpp, remove stale `.txt` output for the target WAV base path. After the subprocess exits, read the generated `.txt` if present, otherwise fall back to stdout.

## Persistent Worker Gate

Do not implement a persistent worker in this pass. After timing data is collected, decide whether startup/model load is significant enough to justify a persistent whisper.cpp server, wrapper process, or binding-backed service that keeps the model loaded between dictations.

## Testing

Add focused tests for:

- Parsing whisper.cpp timing lines.
- Formatting readable timing reports with model mode and audio duration.
- Building commands with safe speed flags while preserving the selected model.
- Cleaning stale output before a run.
- Recording cleanup and end-to-end timing in the worker path.
