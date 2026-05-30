import tempfile
from pathlib import Path
import unittest
import wave

from audio.recorder import get_wav_duration_seconds


class AudioDurationTests(unittest.TestCase):
    def test_get_wav_duration_seconds_reads_wav_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "sample.wav"
            sample_rate = 16_000
            duration_seconds = 2.5
            frame_count = int(sample_rate * duration_seconds)

            with wave.open(str(wav_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b"\x00\x00" * frame_count)

            self.assertEqual(get_wav_duration_seconds(wav_path), 2.5)


if __name__ == "__main__":
    unittest.main()
