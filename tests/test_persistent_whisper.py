import unittest

from transcription.persistent_whisper import PersistentWhisperManager
from transcription.whisper_engine import WhisperTranscriptionResult


class FakeBackend:
    created: list["FakeBackend"] = []

    def __init__(self, executable_path: str, model_path: str, thread_count: int | None = None):
        self.executable_path = executable_path
        self.model_path = model_path
        self.thread_count = thread_count
        self.closed = False
        self.calls = 0
        FakeBackend.created.append(self)

    def transcribe_with_timing(self, wav_path):
        self.calls += 1
        return WhisperTranscriptionResult(text="ok", stages=[], whisper_cpp_timings_ms={})

    def close(self):
        self.closed = True


class PersistentWhisperManagerTests(unittest.TestCase):
    def setUp(self):
        FakeBackend.created = []

    def test_reuses_loaded_backend_for_same_model(self):
        manager = PersistentWhisperManager(
            backend_factory=FakeBackend,
            clock=lambda: 100.0,
        )

        first = manager.transcribe_with_timing("exe", "model-a", "audio.wav")
        second = manager.transcribe_with_timing("exe", "model-a", "audio.wav")

        self.assertEqual(first.text, "ok")
        self.assertEqual(second.text, "ok")
        self.assertEqual(len(FakeBackend.created), 1)
        self.assertEqual(FakeBackend.created[0].calls, 2)

    def test_switching_model_closes_previous_backend(self):
        manager = PersistentWhisperManager(
            backend_factory=FakeBackend,
            clock=lambda: 100.0,
        )

        manager.transcribe_with_timing("exe", "model-a", "audio.wav")
        manager.transcribe_with_timing("exe", "model-b", "audio.wav")

        self.assertTrue(FakeBackend.created[0].closed)
        self.assertFalse(FakeBackend.created[1].closed)

    def test_idle_timeout_closes_backend_after_thirty_minutes(self):
        now = [100.0]
        manager = PersistentWhisperManager(
            backend_factory=FakeBackend,
            idle_timeout_seconds=1800,
            clock=lambda: now[0],
        )

        manager.transcribe_with_timing("exe", "model-a", "audio.wav")
        now[0] = 1901.0
        manager.close_if_idle()

        self.assertTrue(FakeBackend.created[0].closed)
        self.assertFalse(manager.is_loaded)

    def test_close_releases_loaded_backend(self):
        manager = PersistentWhisperManager(
            backend_factory=FakeBackend,
            clock=lambda: 100.0,
        )

        manager.transcribe_with_timing("exe", "model-a", "audio.wav")
        manager.close()

        self.assertTrue(FakeBackend.created[0].closed)
        self.assertFalse(manager.is_loaded)


if __name__ == "__main__":
    unittest.main()
