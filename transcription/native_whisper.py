from __future__ import annotations

from array import array
import ctypes
from ctypes import (
    POINTER,
    Structure,
    c_bool,
    c_char_p,
    c_float,
    c_int,
    c_int64,
    c_size_t,
    c_void_p,
)
import os
from pathlib import Path
from time import perf_counter
import wave

from transcription.timing import StageTiming
from transcription.whisper_engine import (
    WhisperTranscriptionResult,
    default_thread_count,
)


WHISPER_SAMPLING_GREEDY = 0


class WhisperAhead(Structure):
    _fields_ = [
        ("n_text_layer", c_int),
        ("n_head", c_int),
    ]


class WhisperAheads(Structure):
    _fields_ = [
        ("n_heads", c_size_t),
        ("heads", POINTER(WhisperAhead)),
    ]


class WhisperContextParams(Structure):
    _fields_ = [
        ("use_gpu", c_bool),
        ("flash_attn", c_bool),
        ("gpu_device", c_int),
        ("dtw_token_timestamps", c_bool),
        ("dtw_aheads_preset", c_int),
        ("dtw_n_top", c_int),
        ("dtw_aheads", WhisperAheads),
        ("dtw_mem_size", c_size_t),
    ]


class WhisperVadParams(Structure):
    _fields_ = [
        ("threshold", c_float),
        ("min_speech_duration_ms", c_int),
        ("min_silence_duration_ms", c_int),
        ("max_speech_duration_s", c_float),
        ("speech_pad_ms", c_int),
        ("samples_overlap", c_float),
    ]


class WhisperGreedyParams(Structure):
    _fields_ = [("best_of", c_int)]


class WhisperBeamSearchParams(Structure):
    _fields_ = [
        ("beam_size", c_int),
        ("patience", c_float),
    ]


class WhisperFullParams(Structure):
    _fields_ = [
        ("strategy", c_int),
        ("n_threads", c_int),
        ("n_max_text_ctx", c_int),
        ("offset_ms", c_int),
        ("duration_ms", c_int),
        ("translate", c_bool),
        ("no_context", c_bool),
        ("no_timestamps", c_bool),
        ("single_segment", c_bool),
        ("print_special", c_bool),
        ("print_progress", c_bool),
        ("print_realtime", c_bool),
        ("print_timestamps", c_bool),
        ("token_timestamps", c_bool),
        ("thold_pt", c_float),
        ("thold_ptsum", c_float),
        ("max_len", c_int),
        ("split_on_word", c_bool),
        ("max_tokens", c_int),
        ("debug_mode", c_bool),
        ("audio_ctx", c_int),
        ("tdrz_enable", c_bool),
        ("suppress_regex", c_char_p),
        ("initial_prompt", c_char_p),
        ("carry_initial_prompt", c_bool),
        ("prompt_tokens", c_void_p),
        ("prompt_n_tokens", c_int),
        ("language", c_char_p),
        ("detect_language", c_bool),
        ("suppress_blank", c_bool),
        ("suppress_nst", c_bool),
        ("temperature", c_float),
        ("max_initial_ts", c_float),
        ("length_penalty", c_float),
        ("temperature_inc", c_float),
        ("entropy_thold", c_float),
        ("logprob_thold", c_float),
        ("no_speech_thold", c_float),
        ("greedy", WhisperGreedyParams),
        ("beam_search", WhisperBeamSearchParams),
        ("new_segment_callback", c_void_p),
        ("new_segment_callback_user_data", c_void_p),
        ("progress_callback", c_void_p),
        ("progress_callback_user_data", c_void_p),
        ("encoder_begin_callback", c_void_p),
        ("encoder_begin_callback_user_data", c_void_p),
        ("abort_callback", c_void_p),
        ("abort_callback_user_data", c_void_p),
        ("logits_filter_callback", c_void_p),
        ("logits_filter_callback_user_data", c_void_p),
        ("grammar_rules", c_void_p),
        ("n_grammar_rules", c_size_t),
        ("i_start_rule", c_size_t),
        ("grammar_penalty", c_float),
        ("vad", c_bool),
        ("vad_model_path", c_char_p),
        ("vad_params", WhisperVadParams),
    ]


class WhisperTimings(Structure):
    _fields_ = [
        ("sample_ms", c_float),
        ("encode_ms", c_float),
        ("decode_ms", c_float),
        ("batchd_ms", c_float),
        ("prompt_ms", c_float),
    ]


class NativeWhisperCppEngine:
    def __init__(
        self,
        executable_path: str,
        model_path: str,
        thread_count: int | None = None,
    ) -> None:
        self.executable_path = executable_path
        self.model_path = model_path
        self.thread_count = thread_count or default_thread_count()
        self._dll_dir = Path(executable_path).parent
        self._dll_handle = None
        self._ctx = None
        self._load_ms: float | None = None
        self._load()

    def transcribe_with_timing(self, wav_path: Path | str) -> WhisperTranscriptionResult:
        total_started = perf_counter()
        stages: list[StageTiming] = []
        if self._load_ms is not None:
            stages.append(StageTiming("whisper_model_load", self._load_ms))
            self._load_ms = None

        read_started = perf_counter()
        samples = read_wav_as_float32(Path(wav_path))
        stages.append(elapsed_stage("whisper_audio_read", read_started))

        params = self._lib.whisper_full_default_params(WHISPER_SAMPLING_GREEDY)
        params.n_threads = self.thread_count
        params.no_timestamps = True
        params.print_progress = False
        params.print_realtime = False
        params.print_timestamps = False
        params.translate = False

        sample_buffer = (c_float * len(samples))(*samples)
        process_started = perf_counter()
        return_code = self._lib.whisper_full(
            self._ctx,
            params,
            sample_buffer,
            len(samples),
        )
        stages.append(elapsed_stage("whisper_process_elapsed", process_started))
        if return_code != 0:
            raise RuntimeError(f"persistent whisper.cpp failed with code {return_code}")

        text_started = perf_counter()
        text_parts: list[str] = []
        segment_count = self._lib.whisper_full_n_segments(self._ctx)
        for index in range(segment_count):
            segment = self._lib.whisper_full_get_segment_text(self._ctx, index)
            if segment:
                text_parts.append(segment.decode("utf-8", errors="replace"))
        stages.append(elapsed_stage("whisper_output_read", text_started))
        stages.append(elapsed_stage("whisper_total", total_started))

        timings = self._lib.whisper_get_timings(self._ctx).contents
        self._lib.whisper_reset_timings(self._ctx)

        return WhisperTranscriptionResult(
            text="".join(text_parts).strip(),
            stages=stages,
            whisper_cpp_timings_ms={
                "sample": float(timings.sample_ms),
                "encode": float(timings.encode_ms),
                "decode": float(timings.decode_ms),
                "batchd": float(timings.batchd_ms),
                "prompt": float(timings.prompt_ms),
                "total": float(
                    timings.sample_ms
                    + timings.encode_ms
                    + timings.decode_ms
                    + timings.batchd_ms
                    + timings.prompt_ms
                ),
            },
        )

    def close(self) -> None:
        if self._ctx is not None:
            self._lib.whisper_free(self._ctx)
            self._ctx = None
        if self._dll_handle is not None:
            self._dll_handle.close()
        self._dll_handle = None

    def _load(self) -> None:
        dll_path = self._dll_dir / "whisper.dll"
        if not dll_path.is_file():
            raise FileNotFoundError(f"whisper.dll was not found next to whisper-cli.exe: {dll_path}")
        if not Path(self.model_path).is_file():
            raise FileNotFoundError(f"Whisper model file was not found: {self.model_path}")

        load_started = perf_counter()
        if hasattr(os, "add_dll_directory"):
            self._dll_handle = os.add_dll_directory(str(self._dll_dir))
        self._lib = ctypes.CDLL(str(dll_path))
        configure_library(self._lib)
        context_params = self._lib.whisper_context_default_params()
        self._ctx = self._lib.whisper_init_from_file_with_params(
            str(self.model_path).encode("utf-8"),
            context_params,
        )
        if not self._ctx:
            raise RuntimeError(f"Could not load Whisper model: {self.model_path}")
        self._load_ms = (perf_counter() - load_started) * 1000


def configure_library(lib) -> None:
    lib.whisper_context_default_params.argtypes = []
    lib.whisper_context_default_params.restype = WhisperContextParams
    lib.whisper_init_from_file_with_params.argtypes = [c_char_p, WhisperContextParams]
    lib.whisper_init_from_file_with_params.restype = c_void_p
    lib.whisper_free.argtypes = [c_void_p]
    lib.whisper_free.restype = None
    lib.whisper_full_default_params.argtypes = [c_int]
    lib.whisper_full_default_params.restype = WhisperFullParams
    lib.whisper_full.argtypes = [c_void_p, WhisperFullParams, POINTER(c_float), c_int]
    lib.whisper_full.restype = c_int
    lib.whisper_full_n_segments.argtypes = [c_void_p]
    lib.whisper_full_n_segments.restype = c_int
    lib.whisper_full_get_segment_text.argtypes = [c_void_p, c_int]
    lib.whisper_full_get_segment_text.restype = c_char_p
    lib.whisper_get_timings.argtypes = [c_void_p]
    lib.whisper_get_timings.restype = POINTER(WhisperTimings)
    lib.whisper_reset_timings.argtypes = [c_void_p]
    lib.whisper_reset_timings.restype = None


def read_wav_as_float32(wav_path: Path) -> list[float]:
    with wave.open(str(wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if channels != 1 or sample_width != 2 or sample_rate != 16_000:
        raise ValueError(
            "Persistent Whisper expects mono 16-bit PCM WAV at 16 kHz; "
            f"got channels={channels}, sample_width={sample_width}, sample_rate={sample_rate}"
        )

    pcm = array("h")
    pcm.frombytes(frames)
    if os.sys.byteorder != "little":
        pcm.byteswap()
    return [sample / 32768.0 for sample in pcm]


def elapsed_stage(name: str, started_at: float) -> StageTiming:
    return StageTiming(name, (perf_counter() - started_at) * 1000)
