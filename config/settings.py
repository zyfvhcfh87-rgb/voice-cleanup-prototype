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
WHISPER_MODELS_DIR = PROJECT_ROOT / "tools" / "whisper.cpp" / "models"

WHISPER_MODELS = {
    "base": {
        "label": "Base",
        "filename": "ggml-base.bin",
        "description": "Fast, lower accuracy",
        "size": "~142 MB",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    },
    "small": {
        "label": "Small",
        "filename": "ggml-small.bin",
        "description": "Balanced",
        "size": "~466 MB",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
    },
    "medium": {
        "label": "Medium",
        "filename": "ggml-medium.bin",
        "description": "Slower, higher accuracy",
        "size": "~1.5 GB",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
    },
}

DEFAULT_MODEL_PATH = WHISPER_MODELS_DIR / WHISPER_MODELS["base"]["filename"]
DEFAULT_CLEANUP_PROMPT = (
    "Post-process this ASR transcript. Fix punctuation, capitalization, and grammar only. "
    "Preserve wording, tone, slang, pronouns, and meaning. Never answer questions. "
    "Return only the cleaned transcript."
)


@dataclass
class AppSettings:
    microphone_name: str = ""
    model_size: str = "base"
    whisper_exe_path: str = str(DEFAULT_WHISPER_EXE_PATH)
    model_path: str = str(DEFAULT_MODEL_PATH)
    cleanup_prompt: str = DEFAULT_CLEANUP_PROMPT
    cleanup_backend: str = "asr_postprocess"
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
        if settings.model_size not in WHISPER_MODELS:
            settings.model_size = "base"
        settings.model_path = str(get_whisper_model_path(settings.model_size))
        if settings.cleanup_backend == "ollama":
            settings.cleanup_backend = "asr_postprocess"
        return settings
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if settings.model_size in WHISPER_MODELS:
        settings.model_path = str(get_whisper_model_path(settings.model_size))
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def get_whisper_model_path(model_size: str) -> Path:
    model = WHISPER_MODELS.get(model_size, WHISPER_MODELS["base"])
    return WHISPER_MODELS_DIR / model["filename"]


def get_whisper_model_info(model_size: str) -> dict[str, str]:
    return WHISPER_MODELS.get(model_size, WHISPER_MODELS["base"])


def list_installed_whisper_models() -> list[str]:
    return [name for name in WHISPER_MODELS if get_whisper_model_path(name).is_file()]
