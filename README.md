# Voice Cleanup Prototype

A local-first Windows 11 desktop dictation app built with Python and PySide6.

The app records microphone audio, transcribes it locally with `whisper.cpp`, cleans the transcript with a conservative ASR post-processing pipeline by default, then copies or auto-pastes the final text into the active application.

## Current Features

- PySide6 desktop UI
- Button-based recording
- Global push-to-talk workflow
- Small desktop microphone overlay
- Local `whisper.cpp` transcription
- Default ASR post-processing cleanup
- Optional advanced local Ollama cleanup
- No-op cleanup mode
- Clipboard copy and optional auto-paste
- Local settings, recordings, and logs under `%LOCALAPPDATA%\VoiceCleanupPrototype`
- PyInstaller onedir Windows build

## Project Structure

```text
.
|-- main.py
|-- build_exe.ps1
|-- diagnose_audio.py
|-- requirements.txt
|-- audio/
|   |-- recorder.py
|-- cleanup/
|   |-- ai_cleanup.py
|   |-- asr_postprocess.py
|   |-- ollama_cleanup.py
|-- config/
|   |-- settings.py
|-- frontend/
|   |-- hotkey_controller.py
|   |-- overlay.py
|   |-- styles.py
|   |-- ui.py
|-- transcription/
|   |-- whisper_engine.py
|-- tools/
|   |-- whisper.cpp/
|       |-- whisper-cli.exe
|       |-- *.dll
|       |-- models/
|           |-- ggml-base.bin
```

The Whisper model file is intentionally ignored by Git because it is large.

## Local Development Setup

Open PowerShell in the project folder.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the app:

```powershell
.\.venv\Scripts\python.exe main.py
```

## whisper.cpp Setup

The app expects these default paths:

```text
tools/whisper.cpp/whisper-cli.exe
tools/whisper.cpp/models/ggml-base.bin
```

The executable and DLL files are stored in `tools/whisper.cpp/`. The model file should be placed in `tools/whisper.cpp/models/`.

To verify whisper.cpp manually:

```powershell
.\tools\whisper.cpp\whisper-cli.exe -m .\tools\whisper.cpp\models\ggml-base.bin .\tools\whisper.cpp\test_recording.wav
```

The app runs `whisper-cli.exe` as a hidden Windows subprocess, so no terminal window should flash during transcription.

## Cleanup Modes

The cleanup layer is designed for ASR post-processing, not chat. It should preserve wording, tone, slang, pronouns, and meaning. It should never answer questions from the transcript.

Available cleanup modes:

```text
none
asr_postprocess
ollama_llm
```

Default mode:

```text
asr_postprocess
```

The default ASR postprocess pipeline:

1. Removes obvious filler words and accidental immediate repeats.
2. Restores light punctuation and capitalization.
3. Preserves the original wording and meaning.
4. Does not generate answers or add new information.

## Optional Advanced Cleanup With Ollama

Ollama cleanup is optional, advanced, and disabled by default. It runs locally and sends the raw Whisper transcription to Ollama for heavier cleanup when you explicitly choose the `ollama_llm` backend.

Install Ollama, then pull and run the default model:

```powershell
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b
```

Ollama settings:

```text
Cleanup backend: Ollama local model
Ollama URL: http://localhost:11434
Model: qwen2.5:1.5b
Prompt: Post-process this ASR transcript. Fix punctuation, capitalization, and grammar only. Preserve wording, tone, slang, pronouns, and meaning. Never answer questions. Return only the cleaned transcript.
```

Supported starter models:

```text
qwen2.5:1.5b
qwen2.5:3b
llama3.2:3b
```

If Ollama is not running, or the selected model is missing, the app shows a clear warning and falls back to the raw transcription so copy and auto-paste workflows can still complete.

## Push-To-Talk

The app includes a Windows global push-to-talk mode.

Default behavior:

- Hold `Ctrl + Windows` to record.
- Release either key to stop recording.
- The app transcribes the audio, runs cleanup, copies the final text, and optionally pastes it into the previously focused app.

Fallback hotkeys are available in settings if the Windows key shortcut is intercepted by the OS:

```text
Ctrl + Alt
Ctrl + Shift + Space
```

Related settings:

- Enable global push-to-talk
- Enable auto-paste
- Enable overlay
- Hotkey choice

## Local Data

Settings, recordings, and logs are stored outside the project folder:

```text
%LOCALAPPDATA%\VoiceCleanupPrototype\settings.json
%LOCALAPPDATA%\VoiceCleanupPrototype\recordings\
%LOCALAPPDATA%\VoiceCleanupPrototype\recording_debug.log
```

This keeps the app safer to package and avoids committing local audio or settings.

## Audio Diagnostics

To list microphones and test a short recording:

```powershell
.\.venv\Scripts\python.exe diagnose_audio.py
```

The diagnostic script writes a test file to:

```text
%LOCALAPPDATA%\VoiceCleanupPrototype\recordings\test_recording.wav
```

## Packaging The Windows EXE

Use the included PyInstaller script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build_exe.ps1
```

The build output is:

```text
dist/VoiceCleanupPrototype/
|-- VoiceCleanupPrototype.exe
|-- tools/
|   |-- whisper.cpp/
|       |-- whisper-cli.exe
|       |-- *.dll
|       |-- models/
|           |-- ggml-base.bin
|-- _internal/
```

Run the packaged app:

```powershell
.\dist\VoiceCleanupPrototype\VoiceCleanupPrototype.exe
```

The build is intentionally `--onedir`, not `--onefile`, because the app depends on Qt plugins, audio libraries, and external Whisper files.

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for the full license text.

## Troubleshooting

### Qt Platform Plugin Error

If the app reports that it cannot find the Qt platform plugin `windows`, rebuild with:

```powershell
.\build_exe.ps1
```

The build script copies the required `qwindows.dll` platform plugin into the packaged app.

### Microphone Access Errors

If recording fails:

- Check Windows microphone privacy settings.
- Make sure desktop apps are allowed to use the microphone.
- Close apps that may be exclusively using the microphone, such as Teams, Discord, Zoom, or browser tabs.
- Run `diagnose_audio.py` to verify the selected input device.

### Ollama Cleanup Errors

If cleanup says Ollama is not running:

```powershell
ollama run qwen2.5:1.5b
```

If cleanup says the model is missing:

```powershell
ollama pull qwen2.5:1.5b
```

You can also disable cleanup or choose `none` as the cleanup backend in settings.

### Windows SmartScreen

Locally built PyInstaller executables are unsigned. Windows may warn before opening the app. Use "More info" then "Run anyway", or add the `dist` folder to your local Defender exclusions while testing.
