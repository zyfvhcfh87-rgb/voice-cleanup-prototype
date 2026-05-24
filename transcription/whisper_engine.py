from pathlib import Path
import subprocess


class WhisperCppEngine:
    def __init__(self, executable_path: str, model_path: str) -> None:
        self.executable_path = executable_path
        self.model_path = model_path

    def transcribe(self, wav_path: Path) -> str:
        exe = Path(self.executable_path)
        model = Path(self.model_path)

        if not self.executable_path.strip() or not exe.is_file():
            raise FileNotFoundError("whisper.cpp executable was not found. Set it in Settings.")
        if not self.model_path.strip() or not model.is_file():
            raise FileNotFoundError("Whisper model file was not found. Set the ggml-base.bin path in Settings.")
        if not wav_path.exists():
            raise FileNotFoundError(f"Recording file does not exist: {wav_path}")

        output_base = wav_path.with_suffix("")
        command = [
            str(exe),
            "-m",
            str(model),
            "-f",
            str(wav_path),
            "-otxt",
            "-of",
            str(output_base),
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"whisper.cpp failed: {details}")

        text_path = output_base.with_suffix(".txt")
        if text_path.exists():
            return text_path.read_text(encoding="utf-8").strip()

        # Some whisper.cpp builds print transcription to stdout instead.
        return result.stdout.strip()
