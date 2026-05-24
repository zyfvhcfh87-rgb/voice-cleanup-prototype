from pathlib import Path
import sys
import wave

import numpy as np
import sounddevice as sd

from audio.recorder import recordings_dir


SAMPLE_RATE = 16_000
CHANNELS = 1
SECONDS = 3


def write_wav(path: Path, audio: np.ndarray) -> None:
    clipped = np.clip(audio, -1.0, 1.0)
    pcm16 = (clipped * 32767).astype(np.int16)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm16.tobytes())


def list_inputs() -> None:
    print("Input devices:")
    for index, device in enumerate(sd.query_devices()):
        if int(device.get("max_input_channels", 0)) > 0:
            print(f"  {index}: {device['name']} ({device['hostapi']}) inputs={device['max_input_channels']}")


def main() -> int:
    print(f"cwd: {Path.cwd()}")
    print(f"default device: {sd.default.device}")
    list_inputs()

    device_index = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(f"test device index: {device_index if device_index is not None else 'default'}")

    try:
        device_info = sd.query_devices(device_index, "input")
        print(f"test device name: {device_info['name']}")
    except Exception as exc:
        print(f"DEVICE LOOKUP FAILED: {exc}")
        return 1

    try:
        output_dir = recordings_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        probe_path = output_dir / ".write_test"
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
        print(f"output directory writable: {output_dir}")
    except Exception as exc:
        print(f"FILE DIRECTORY CHECK FAILED: {exc}")
        return 1

    try:
        print("opening input stream...")
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", device=device_index):
            print("device open succeeded")
    except Exception as exc:
        print(f"DEVICE OPEN FAILED: {exc}")
        return 1

    try:
        print(f"recording {SECONDS} seconds...")
        audio = sd.rec(int(SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", device=device_index)
        sd.wait()
        print("recording succeeded")
    except Exception as exc:
        print(f"RECORDING FAILED: {exc}")
        return 1

    try:
        wav_path = output_dir / "test_recording.wav"
        write_wav(wav_path, audio)
        print(f"file save succeeded: {wav_path}")
    except Exception as exc:
        print(f"FILE SAVE FAILED: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
