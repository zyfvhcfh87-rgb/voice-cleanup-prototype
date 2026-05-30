from __future__ import annotations

from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Callable, Protocol

from transcription.whisper_engine import (
    WhisperCppEngine,
    WhisperTranscriptionResult,
    default_thread_count,
)
from transcription.native_whisper import NativeWhisperCppEngine


class PersistentWhisperBackend(Protocol):
    def transcribe_with_timing(self, wav_path: Path | str) -> WhisperTranscriptionResult:
        ...

    def close(self) -> None:
        ...


BackendFactory = Callable[[str, str, int | None], PersistentWhisperBackend]


class PersistentWhisperManager:
    def __init__(
        self,
        backend_factory: BackendFactory | None = None,
        idle_timeout_seconds: float = 30 * 60,
        clock: Callable[[], float] = monotonic,
        thread_count: int | None = None,
    ) -> None:
        self.backend_factory = backend_factory or create_persistent_backend
        self.idle_timeout_seconds = idle_timeout_seconds
        self.clock = clock
        self.thread_count = thread_count or default_thread_count()
        self._backend: PersistentWhisperBackend | None = None
        self._key: tuple[str, str, int] | None = None
        self._last_used_at = 0.0
        self._lock = Lock()

    @property
    def is_loaded(self) -> bool:
        return self._backend is not None

    def transcribe_with_timing(
        self,
        executable_path: str,
        model_path: str,
        wav_path: Path | str,
    ) -> WhisperTranscriptionResult:
        with self._lock:
            backend = self._get_or_create_backend(executable_path, model_path)
            try:
                return backend.transcribe_with_timing(wav_path)
            finally:
                self._last_used_at = self.clock()

    def close_if_idle(self) -> None:
        with self._lock:
            if self._backend is None:
                return
            if self.clock() - self._last_used_at >= self.idle_timeout_seconds:
                self._close_locked()

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def _get_or_create_backend(
        self,
        executable_path: str,
        model_path: str,
    ) -> PersistentWhisperBackend:
        key = (str(Path(executable_path)), str(Path(model_path)), self.thread_count)

        if self._backend is not None and self._key == key:
            return self._backend

        self._close_locked()
        self._backend = self.backend_factory(
            executable_path,
            model_path,
            self.thread_count,
        )
        self._key = key
        return self._backend

    def _close_locked(self) -> None:
        if self._backend is not None:
            self._backend.close()
        self._backend = None
        self._key = None
        self._last_used_at = 0.0


class ManagedWhisperEngine:
    def __init__(
        self,
        manager: PersistentWhisperManager,
        executable_path: str,
        model_path: str,
    ) -> None:
        self.manager = manager
        self.executable_path = executable_path
        self.model_path = model_path

    def transcribe_with_timing(self, wav_path: Path | str) -> WhisperTranscriptionResult:
        return self.manager.transcribe_with_timing(
            self.executable_path,
            self.model_path,
            wav_path,
        )

    def transcribe(self, wav_path: Path | str) -> str:
        return self.transcribe_with_timing(wav_path).text


def create_persistent_backend(
    executable_path: str,
    model_path: str,
    thread_count: int | None = None,
) -> PersistentWhisperBackend:
    try:
        return NativeWhisperCppEngine(executable_path, model_path, thread_count)
    except Exception:
        return WhisperCppEngine(executable_path, model_path, thread_count)
