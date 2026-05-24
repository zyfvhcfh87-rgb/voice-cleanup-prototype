# Voice Cleanup AI - Modern Desktop Workspace

A premium, local-first Windows 11 desktop application designed to record spoken speech, transcribe it locally using `whisper.cpp`, perform automated rule-based cleanups, and auto-paste/copy the polished results. 

The application has been styled with a high-end glassmorphic theme (harmonious off-white, light purple-to-pink linear gradients, cyan accents, soft drop shadows, and clean margins) and features a circular, 60 FPS glowing floating desktop overlay widget.

---

## Technical File Structure

```text
.
├── main.py                    # App entrypoint (with dynamic Windows DLL search resolution)
├── build_exe.ps1              # Automation build script for PyInstaller executable compiling
├── audio/
│   ├── __init__.py
│   └── recorder.py            # Local sounddevice microphone recording (16kHz PCM)
├── cleanup/
│   ├── __init__.py
│   └── ai_cleanup.py          # AI Rule-based cleanup engines
├── config/
│   ├── __init__.py
│   └── settings.py            # Local settings management (localized to LOCALAPPDATA)
├── frontend/
│   ├── __init__.py
│   ├── ui.py                  # Visible main application (rounded 2-column card architecture)
│   ├── overlay.py             # Floating circular glassmorphic microphone overlay (pulsing animation)
│   └── styles.py              # Brand styling stylesheets (QSS), GlassCard, and custom TitleBar
├── transcription/
│   ├── __init__.py
│   └── whisper_engine.py      # Local whisper.cpp CLI integration worker
├── requirements.txt           # Main environment dependencies
└── README.md                  # System instruction and documentation
```

---

## Local Development Setup

To run the application from source using Python:

1. **Initialize and Activate Virtual Environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Package Dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Launch Workspace**:
   ```powershell
   .venv\Scripts\python.exe main.py
   ```

---

## Packaging Standalone Executable (.exe)

You can compile the workspace into a standalone Windows directory that runs natively without needing a Python installation.

### How to Build:
1. Open PowerShell in the project directory.
2. Run the automated build script:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\build_exe.ps1
   ```
3. The build compiler will:
   - Compile Python sources into optimized binaries inside `dist/VoiceCleanupPrototype/`.
   - Copy the required `tools/` folder structure (whisper engine assets) directly into the compiled folder.
   - Clean up temporary builder directories.

### Distributable Package Layout:
After packaging completes, your compiled distribution folder in `dist/VoiceCleanupPrototype/` has this layout:

```text
dist/VoiceCleanupPrototype/
├── VoiceCleanupPrototype.exe       # Main compiled application executable
├── tools/                          # AI Engines and Models folder (External to keep binary small)
│   └── whisper.cpp/
│       ├── whisper-cli.exe         # Local transcription engine
│       ├── SDL2.dll, whisper.dll   # Engine dependencies
│       └── models/
│           └── ggml-base.bin       # Whisper AI model weights file
└── [PySide6, sounddevice libraries, etc.]
```

*Note: The Whisper model weights (`.bin`) and local compiler CLI are deliberately kept external rather than bundled inside the `.exe` itself. This keeps loading times extremely fast and memory consumption highly efficient.*

---

## System Configuration & Parameters

- **Settings Directory**: Your configuration files are stored safely outside the installation directories:
  ```text
  %LOCALAPPDATA%\VoiceCleanupPrototype\settings.json
  ```
- **Local Media & Logs**: Temporary wave files and diagnostic audio runtime traces are saved inside:
  ```text
  %LOCALAPPDATA%\VoiceCleanupPrototype\recordings\
  %LOCALAPPDATA%\VoiceCleanupPrototype\recording_debug.log
  ```

---

## Advanced Troubleshooting & Diagnostic Guide

### 1. Windows Defender / Antivirus SmartScreen Blocks
Because PyInstaller bundles Python and custom DLL libraries into a new, unsigned `.exe` on your local machine, Windows SmartScreen or Windows Defender might flag the compiled executable as a warning.
- **Why this happens**: This is a standard security behavior for any custom compiled, unsigned software built on a local developer workstation. 
- **How to resolve**: Click **"More Info"** in the Windows SmartScreen pop-up, then click **"Run Anyway"**. Alternatively, you can add your `dist/` directory to Windows Defender's Exclusion List.

### 2. Qt Platform Plugin Initialization Failure
If you receive the error `Could not find the Qt platform plugin "windows"`, this is typically caused by:
- **Comma in Folder Path**: Qt has a known parsing behavior on Windows where it splits path definitions on commas (`,`). If the path to your folder contains a comma (e.g. `...\Voice to text, and cleanup application\...`), Qt will fail to resolve its libraries!
- **Resolution**: We have built an automated startup guard in `main.py` that dynamically registers `os.add_dll_directory` and sets `QT_QPA_PLATFORM_PLUGIN_PATH` directly to the absolute plugins path, bypassing this bug. If issues persist, ensure the project resides in a parent folder path containing no spaces or special symbols (like commas).

### 3. Microphone Access / PortAudio Failure
If you receive a recording or device access error:
- Ensure your system's global Windows Privacy settings allow desktop applications to access the microphone.
- Close other applications (like Microsoft Teams, Zoom, or Discord) that might have exclusive lock access on your current audio input channel.
- Use the **Refresh** button inside the settings card to reload your active soundcard drivers.
