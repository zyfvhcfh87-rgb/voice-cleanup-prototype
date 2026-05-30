from pathlib import Path
from dataclasses import dataclass
import os
import subprocess
from time import perf_counter

from transcription.timing import StageTiming, parse_whisper_cpp_timings


@dataclass
class WhisperTranscriptionResult:
    text: str
    stages: list[StageTiming]
    whisper_cpp_timings_ms: dict[str, float]


class WhisperCppEngine:
    def __init__(
        self,
        executable_path: str,
        model_path: str,
        thread_count: int | None = None,
        runner=subprocess.run,
    ) -> None:
        self.executable_path = executable_path
        self.model_path = model_path
        self.thread_count = thread_count or default_thread_count()
        self.runner = runner

    def transcribe(self, wav_path: Path) -> str:
        return self.transcribe_with_timing(wav_path).text

    def transcribe_with_timing(self, wav_path: Path) -> WhisperTranscriptionResult:
        total_started = perf_counter()
        stages: list[StageTiming] = []

        prepare_started = perf_counter()
        exe = Path(self.executable_path)
        model = Path(self.model_path)

        if not self.executable_path.strip() or not exe.is_file():
            raise FileNotFoundError("whisper.cpp executable was not found. Set it in Settings.")
        if not self.model_path.strip() or not model.is_file():
            raise FileNotFoundError(f"Whisper model file was not found: {model}")
        if not wav_path.exists():
            raise FileNotFoundError(f"Recording file does not exist: {wav_path}")

        output_base = wav_path.with_suffix("")
        text_path = output_base.with_suffix(".txt")
        text_path.unlink(missing_ok=True)
        command = [
            str(exe),
            "-m",
            str(model),
            "-f",
            str(wav_path),
            "-t",
            str(self.thread_count),
            "-nt",
            "-otxt",
            "-of",
            str(output_base),
        ]
        stages.append(elapsed_stage("whisper_file_prepare", prepare_started))

        startupinfo = None
        creationflags = 0
        if hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        process_started = perf_counter()
        result = self.runner(
            command,
            startupinfo=startupinfo,
            creationflags=creationflags,
            capture_output=True,
            text=True,
        )
        stages.append(elapsed_stage("whisper_process_elapsed", process_started))
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"whisper.cpp failed: {details}")

        output_started = perf_counter()
        if text_path.exists():
            text = text_path.read_text(encoding="utf-8").strip()
        else:
            # Some whisper.cpp builds print transcription to stdout instead.
            text = result.stdout.strip()
        stages.append(elapsed_stage("whisper_output_read", output_started))
        stages.append(elapsed_stage("whisper_total", total_started))

        return WhisperTranscriptionResult(
            text=text,
            stages=stages,
            whisper_cpp_timings_ms=parse_whisper_cpp_timings(
                "\n".join([result.stderr, result.stdout]),
            ),
        )


def default_thread_count() -> int:
    cpu_count = os.cpu_count() or 2
    return max(1, min(cpu_count - 1, 8))


def elapsed_stage(name: str, started_at: float) -> StageTiming:
    return StageTiming(name, (perf_counter() - started_at) * 1000)
