from dataclasses import asdict, dataclass
from pathlib import Path
import json


import os
import sys

local_app_data = os.environ.get("LOCALAPPDATA")
if local_app_data:
    APP_DIR = Path(local_app_data) / "VoiceCleanupPrototype"
else:
    APP_DIR = Path.home() / "VoiceCleanupPrototype"

SETTINGS_FILE = APP_DIR / "settings.json"

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_WHISPER_EXE_PATH = PROJECT_ROOT / "tools" / "whisper.cpp" / "whisper-cli.exe"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "tools" / "whisper.cpp" / "models" / "ggml-base.bin"
DEFAULT_CLEANUP_PROMPT = (
    "Clean up this dictation. Fix punctuation, capitalization, and grammar. "
    "Keep the original meaning. Do not add new information. Return only the cleaned text."
)


@dataclass
class AppSettings:
    microphone_name: str = ""
    model_size: str = "base"
    whisper_exe_path: str = str(DEFAULT_WHISPER_EXE_PATH)
    model_path: str = str(DEFAULT_MODEL_PATH)
    cleanup_prompt: str = DEFAULT_CLEANUP_PROMPT
    cleanup_backend: str = "ollama"
    cleanup_enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    enable_global_push_to_talk: bool = True
    enable_auto_paste: bool = True
    overlay_enabled: bool = True
    hotkey_choice: str = "ctrl_win"


def load_settings() -> AppSettings:
    if not SETTINGS_FILE.exists():
        return AppSettings()

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        settings = AppSettings(**{**asdict(AppSettings()), **data})
        if getattr(sys, "frozen", False):
            settings.whisper_exe_path = str(DEFAULT_WHISPER_EXE_PATH)
            settings.model_path = str(DEFAULT_MODEL_PATH)
        if not settings.whisper_exe_path:
            settings.whisper_exe_path = str(DEFAULT_WHISPER_EXE_PATH)
        if not settings.model_path:
            settings.model_path = str(DEFAULT_MODEL_PATH)
        return settings
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
