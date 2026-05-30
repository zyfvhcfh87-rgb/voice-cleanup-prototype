import subprocess
import tempfile
from pathlib import Path
import unittest

from transcription.whisper_engine import WhisperCppEngine


class WhisperEngineInstrumentationTests(unittest.TestCase):
    def test_transcribe_with_timing_cleans_stale_output_and_uses_safe_flags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            exe_path = temp_path / "whisper-cli.exe"
            model_path = temp_path / "ggml-base.bin"
            wav_path = temp_path / "recording.wav"
            output_path = temp_path / "recording.txt"
            exe_path.write_text("fake exe", encoding="utf-8")
            model_path.write_text("fake model", encoding="utf-8")
            wav_path.write_bytes(b"fake wav")
            output_path.write_text("stale text", encoding="utf-8")
            captured_command: list[str] = []

            def fake_runner(command, **kwargs):
                captured_command.extend(command)
                self.assertFalse(output_path.exists())
                output_path.write_text("fresh transcript", encoding="utf-8")
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="",
                    stderr=(
                        "whisper_print_timings:     load time =   700.00 ms\n"
                        "whisper_print_timings:   encode time =  1000.00 ms\n"
                        "whisper_print_timings:   decode time =   500.00 ms\n"
                        "whisper_print_timings:    total time =  2400.00 ms\n"
                    ),
                )

            engine = WhisperCppEngine(
                executable_path=str(exe_path),
                model_path=str(model_path),
                thread_count=4,
                runner=fake_runner,
            )

            result = engine.transcribe_with_timing(wav_path)

            self.assertEqual(result.text, "fresh transcript")
            self.assertIn("-m", captured_command)
            self.assertIn(str(model_path), captured_command)
            self.assertIn("-f", captured_command)
            self.assertIn(str(wav_path), captured_command)
            self.assertIn("-otxt", captured_command)
            self.assertIn("-nt", captured_command)
            self.assertIn("-t", captured_command)
            self.assertIn("4", captured_command)
            self.assertEqual(result.whisper_cpp_timings_ms["load"], 700.0)
            self.assertEqual(result.whisper_cpp_timings_ms["total"], 2400.0)
            self.assertIn(
                "whisper_file_prepare",
                [stage.name for stage in result.stages],
            )
            self.assertIn(
                "whisper_process_elapsed",
                [stage.name for stage in result.stages],
            )
            self.assertIn("whisper_output_read", [stage.name for stage in result.stages])
            self.assertIn("whisper_total", [stage.name for stage in result.stages])

    def test_transcribe_with_timing_falls_back_to_stdout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            exe_path = temp_path / "whisper-cli.exe"
            model_path = temp_path / "ggml-base.bin"
            wav_path = temp_path / "recording.wav"
            exe_path.write_text("fake exe", encoding="utf-8")
            model_path.write_text("fake model", encoding="utf-8")
            wav_path.write_bytes(b"fake wav")

            def fake_runner(command, **kwargs):
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout="stdout transcript",
                    stderr="",
                )

            engine = WhisperCppEngine(
                executable_path=str(exe_path),
                model_path=str(model_path),
                thread_count=2,
                runner=fake_runner,
            )

            result = engine.transcribe_with_timing(wav_path)

            self.assertEqual(result.text, "stdout transcript")
            self.assertEqual(result.whisper_cpp_timings_ms, {})


if __name__ == "__main__":
    unittest.main()
