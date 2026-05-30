from __future__ import annotations

from dataclasses import dataclass, field
import re


WHISPER_TIMING_PATTERN = re.compile(
    r"whisper_print_timings:\s+([a-z_ ]+?)\s+=\s+([0-9.]+)\s+ms",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class StageTiming:
    name: str
    elapsed_ms: float

    def format(self) -> str:
        return f"{self.name}={self.elapsed_ms / 1000:.2f}s"


@dataclass
class TranscriptionTimingReport:
    model_mode: str
    model_name: str
    audio_duration_seconds: float
    stages: list[StageTiming] = field(default_factory=list)
    whisper_cpp_timings_ms: dict[str, float] = field(default_factory=dict)

    def add_stage(self, name: str, elapsed_ms: float) -> None:
        self.stages.append(StageTiming(name, elapsed_ms))

    def stage_seconds(self, name: str) -> float | None:
        for stage in self.stages:
            if stage.name == name:
                return stage.elapsed_ms / 1000
        return None

    def format_lines(self) -> list[str]:
        end_to_end = self.stage_seconds("end_to_end_after_release")
        whisper_process = self.stage_seconds("whisper_process_elapsed")
        total = end_to_end if end_to_end is not None else whisper_process
        total_text = f"{total:.1f}s" if total is not None else "unknown"

        lines = [
            (
                f"[timing] {self.model_mode} ({self.model_name}): "
                f"{self.audio_duration_seconds:.1f}s audio -> {total_text} end-to-end"
            )
        ]

        if self.whisper_cpp_timings_ms:
            ordered_keys = ["load", "sample", "encode", "decode", "prompt", "total"]
            parts = [
                f"{key}={self.whisper_cpp_timings_ms[key] / 1000:.2f}s"
                for key in ordered_keys
                if key in self.whisper_cpp_timings_ms
            ]
            lines.append(f"[timing] whisper.cpp reported: {', '.join(parts)}")
        else:
            lines.append("[timing] whisper.cpp reported: unavailable")

        process_seconds = self.stage_seconds("whisper_process_elapsed")
        reported_total_ms = self.whisper_cpp_timings_ms.get("total")
        load_ms = self.whisper_cpp_timings_ms.get("load")
        if (
            process_seconds is not None
            and reported_total_ms is not None
            and load_ms is not None
        ):
            cli_overhead_seconds = max(process_seconds - (reported_total_ms / 1000), 0)
            lines.append(
                "[timing] startup/model-load estimate: "
                f"load={load_ms / 1000:.2f}s, "
                f"cli_overhead={cli_overhead_seconds:.2f}s"
            )

        if self.stages:
            lines.append(
                "[timing] stages: "
                + ", ".join(stage.format() for stage in self.stages)
            )

        return lines


def parse_whisper_cpp_timings(output: str) -> dict[str, float]:
    timings: dict[str, float] = {}

    for match in WHISPER_TIMING_PATTERN.finditer(output):
        label = "_".join(match.group(1).strip().lower().split())
        if label.endswith("_time"):
            label = label[: -len("_time")]
        timings[label] = float(match.group(2))

    return timings


def emit_timing_report(
    report: TranscriptionTimingReport,
    printer=print,
    logger=lambda message: None,
) -> None:
    for line in report.format_lines():
        printer(line)
        logger(line)
