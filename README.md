# Voice Cleanup Prototype

A local-first Windows 11 desktop dictation app built with Python and PySide6.

The app records microphone audio, transcribes it locally with `whisper.cpp`, optionally cleans the transcription with a local Ollama model, then copies or auto-pastes the final text into the active application.

## Current Features

- PySide6 desktop UI
- Button-based recording
- Global push-to-talk workflow
- Small desktop microphone overlay
- Local `whisper.cpp` transcription
- Optional local Ollama cleanup
- Rule/no-op fallback cleanup behavior
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

## Optional Local AI Cleanup with Ollama

Ollama cleanup is optional and runs fully locally. It sends the raw Whisper transcription to Ollama for punctuation, capitalization, and grammar cleanup.

Install Ollama, then pull and run the default model:

```powershell
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b
```

Default cleanup settings:

```text
Cleanup backend: Ollama local model
Ollama URL: http://localhost:11434
Model: qwen2.5:1.5b
Prompt: Clean up this dictation. Fix punctuation, capitalization, and grammar. Keep the original meaning. Do not add new information. Return only the cleaned text.
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
