import unittest

from transcription.timing import (
    StageTiming,
    TranscriptionTimingReport,
    emit_timing_report,
    parse_whisper_cpp_timings,
)


class WhisperTimingParsingTests(unittest.TestCase):
    def test_parses_whisper_cpp_timing_lines(self):
        stderr = """
whisper_print_timings:     load time =   712.34 ms
whisper_print_timings:   sample time =    12.00 ms /    25 runs
whisper_print_timings:   encode time =  1024.50 ms /     1 runs
whisper_print_timings:   decode time =   455.25 ms /    12 runs
whisper_print_timings:    total time =  2250.75 ms
"""

        parsed = parse_whisper_cpp_timings(stderr)

        self.assertEqual(parsed["load"], 712.34)
        self.assertEqual(parsed["sample"], 12.0)
        self.assertEqual(parsed["encode"], 1024.5)
        self.assertEqual(parsed["decode"], 455.25)
        self.assertEqual(parsed["total"], 2250.75)

    def test_formats_readable_report_with_audio_model_and_stages(self):
        report = TranscriptionTimingReport(
            model_mode="Fast",
            model_name="ggml-base.bin",
            audio_duration_seconds=10.0,
            stages=[
                StageTiming("recording_stop_total", 120.0),
                StageTiming("whisper_process_elapsed", 3000.0),
                StageTiming("cleanup_total", 20.0),
                StageTiming("end_to_end_after_release", 3300.0),
            ],
            whisper_cpp_timings_ms={
                "load": 700.0,
                "encode": 1100.0,
                "decode": 500.0,
                "total": 2500.0,
            },
        )

        lines = report.format_lines()

        self.assertIn(
            "[timing] Fast (ggml-base.bin): 10.0s audio -> 3.3s end-to-end",
            lines,
        )
        self.assertIn(
            "[timing] whisper.cpp reported: load=0.70s, encode=1.10s, decode=0.50s, total=2.50s",
            lines,
        )
        self.assertIn(
            "[timing] startup/model-load estimate: load=0.70s, cli_overhead=0.50s",
            lines,
        )
        self.assertIn(
            "[timing] stages: recording_stop_total=0.12s, whisper_process_elapsed=3.00s, cleanup_total=0.02s, end_to_end_after_release=3.30s",
            lines,
        )

    def test_emit_timing_report_prints_and_logs_each_line(self):
        report = TranscriptionTimingReport(
            model_mode="Balanced",
            model_name="ggml-small.bin",
            audio_duration_seconds=30.0,
            stages=[StageTiming("end_to_end_after_release", 8000.0)],
        )
        printed: list[str] = []
        logged: list[str] = []

        emit_timing_report(report, printer=printed.append, logger=logged.append)

        self.assertEqual(printed, report.format_lines())
        self.assertEqual(logged, report.format_lines())


if __name__ == "__main__":
    unittest.main()
