from __future__ import annotations

import argparse
from pathlib import Path
import sys

import requests

from config.settings import WHISPER_MODELS, WHISPER_MODELS_DIR, get_whisper_model_path


def download_model(model_size: str, overwrite: bool = False) -> Path:
    if model_size not in WHISPER_MODELS:
        choices = ", ".join(WHISPER_MODELS)
        raise ValueError(f"Unknown model '{model_size}'. Choose one of: {choices}")

    model_info = WHISPER_MODELS[model_size]
    destination = get_whisper_model_path(model_size)
    if destination.exists() and not overwrite:
        print(f"{model_info['label']} already installed: {destination}")
        return destination

    WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".part")
    url = model_info["url"]
    print(f"Downloading {model_info['label']} ({model_info['size']})")
    print(f"From: {url}")
    print(f"To:   {destination}")

    resume_at = temp_path.stat().st_size if temp_path.exists() and not overwrite else 0
    headers = {"Range": f"bytes={resume_at}-"} if resume_at else {}
    if resume_at:
        print(f"Resuming from {resume_at / (1024 * 1024):.1f} MB")

    with requests.get(url, headers=headers, stream=True, timeout=(10, 120)) as response:
        response.raise_for_status()
        if resume_at and response.status_code != 206:
            print("Server did not resume the partial download; starting over.")
            resume_at = 0
        content_length = int(response.headers.get("content-length", "0"))
        total = resume_at + content_length if content_length else 0
        downloaded = resume_at
        mode = "ab" if resume_at else "wb"
        with temp_path.open(mode) as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                file.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded * 100 / total
                    print(f"\r{percent:5.1f}% complete", end="", flush=True)
                else:
                    print(f"\r{downloaded / (1024 * 1024):.1f} MB downloaded", end="", flush=True)

    print()
    temp_path.replace(destination)
    print(f"Installed: {destination}")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Download whisper.cpp GGML models.")
    parser.add_argument(
        "models",
        nargs="+",
        choices=sorted(WHISPER_MODELS),
        help="Model size(s) to download: base, small, medium",
    )
    parser.add_argument("--overwrite", action="store_true", help="Re-download even if the file already exists.")
    args = parser.parse_args()

    for model_size in args.models:
        download_model(model_size, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
