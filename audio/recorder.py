from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import wave

import numpy as np
import sounddevice as sd


@dataclass
class AudioDevice:
    index: int
    name: str


class MicrophoneAccessError(RuntimeError):
    pass


class RecordingFileWriteError(RuntimeError):
    pass


def recordings_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RecordingFileWriteError("LOCALAPPDATA is not set, so the recording folder cannot be created.")
    return Path(local_app_data) / "VoiceCleanupPrototype" / "recordings"


def log_path() -> Path:
    return recordings_dir().parent / "recording_debug.log"


def log_event(message: str) -> None:
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="seconds")
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{timestamp} {message}\n")
    except Exception as exc:
        print(f"[recording-log-failed] {exc}")


def list_input_devices() -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    try:
        for index, device in enumerate(sd.query_devices()):
            if int(device.get("max_input_channels", 0)) > 0:
                devices.append(AudioDevice(index=index, name=str(device["name"])))
    except Exception as exc:
        log_event(f"list_input_devices failed: {repr(exc)}")
        raise
    return devices


class AudioRecorder:
    def __init__(self, sample_rate: int = 16_000) -> None:
        self.sample_rate = sample_rate
        self.channels = 1
        self.stream: sd.InputStream | None = None
        self.frames: list[np.ndarray] = []
        self.is_recording = False

    def start(self, device_index: int | None = None) -> None:
        if self.is_recording:
            raise RuntimeError("Recording is already running.")

        self._ensure_recording_directory()
        device_name = self._device_name(device_index)
        print(f"[recording] cwd={Path.cwd()}")
        print(f"[recording] selected_device_index={device_index}")
        print(f"[recording] selected_device_name={device_name}")
        log_event(f"cwd={Path.cwd()}")
        log_event(f"selected_device_index={device_index}")
        log_event(f"selected_device_name={device_name}")

        self.frames = []
        try:
            log_event("creating sounddevice.InputStream")
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=device_index,
                callback=self._on_audio,
            )
            log_event("starting sounddevice.InputStream")
            self.stream.start()
            self.is_recording = True
            log_event("recording started")
        except Exception as exc:
            self.stream = None
            self.is_recording = False
            log_event(f"microphone open/start failed: {repr(exc)}")
            raise MicrophoneAccessError(
                "Microphone access failed while opening the selected input device. "
                "Check Windows microphone privacy settings, close other apps using the microphone, "
                f"or try another input device. Device index={device_index}, name={device_name}. "
                f"Original error: {exc}"
            ) from exc

    def stop(self) -> Path:
        if not self.is_recording or self.stream is None:
            raise RuntimeError("Recording is not running.")

        self.stream.stop()
        self.stream.close()
        self.stream = None
        self.is_recording = False

        if not self.frames:
            raise RuntimeError("No audio was recorded.")

        audio = np.concatenate(self.frames, axis=0)
        return self._write_wav(audio)

    def _on_audio(self, indata: np.ndarray, frames: int, time, status) -> None:
        if status:
            # sounddevice reports under/overflows here. The app keeps recording,
            # but these statuses are useful while debugging microphone issues.
            print(status)
        self.frames.append(indata.copy())

    def _write_wav(self, audio: np.ndarray) -> Path:
        output_dir = self._ensure_recording_directory()
        wav_path = output_dir / "recording.wav"
        print(f"[recording] output_path={wav_path}")
        log_event(f"output_path={wav_path}")

        clipped = np.clip(audio, -1.0, 1.0)
        pcm16 = (clipped * 32767).astype(np.int16)

        try:
            with wave.open(str(wav_path), "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(pcm16.tobytes())
        except Exception as exc:
            log_event(f"file save failed: {repr(exc)}")
            raise RecordingFileWriteError(
                "Recording succeeded, but saving the WAV file failed. "
                "Check folder permissions or Windows Controlled Folder Access. "
                f"Output path: {wav_path}. Original error: {exc}"
            ) from exc

        return wav_path

    def _ensure_recording_directory(self) -> Path:
        output_dir = recordings_dir()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            probe_path = output_dir / ".write_test"
            probe_path.write_text("ok", encoding="utf-8")
            probe_path.unlink(missing_ok=True)
        except Exception as exc:
            log_event(f"output directory check failed: folder={output_dir} error={repr(exc)}")
            raise RecordingFileWriteError(
                "The recording output folder is not writable. "
                "Check folder permissions or Windows Controlled Folder Access. "
                f"Folder: {output_dir}. Original error: {exc}"
            ) from exc

        print(f"[recording] output_dir={output_dir}")
        print(f"[recording] output_dir_exists={output_dir.exists()}")
        print("[recording] output_dir_writable=True")
        log_event(f"output_dir={output_dir}")
        log_event(f"output_dir_exists={output_dir.exists()}")
        log_event("output_dir_writable=True")
        return output_dir

    def _device_name(self, device_index: int | None) -> str:
        if device_index is None:
            return "default input device"
        try:
            device = sd.query_devices(device_index)
            return str(device["name"])
        except Exception:
            return "unknown"
