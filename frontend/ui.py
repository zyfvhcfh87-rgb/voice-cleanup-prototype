from pathlib import Path
import traceback

from PySide6.QtCore import QThread, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QGraphicsDropShadowEffect,
)

from audio.recorder import AudioRecorder, list_input_devices, log_event
from cleanup.asr_postprocess import ASRPostProcessor
from cleanup.ai_cleanup import NoOpCleaner
from cleanup.ollama_cleanup import OllamaCleaner
from config.settings import AppSettings, load_settings, save_settings
from frontend.hotkey_controller import PushToTalkHotkeyController
from frontend.overlay import MicrophoneOverlay
from transcription.whisper_engine import WhisperCppEngine
from frontend.styles import QSS_STYLING, TitleBar, GlassCard


class TranscriptionWorker(QThread):
    finished_ok = Signal(str, str)
    failed = Signal(str)
    cleanup_warning = Signal(str)

    def __init__(self, engine: WhisperCppEngine, cleaner, wav_path: Path) -> None:
        super().__init__()
        self.engine = engine
        self.cleaner = cleaner
        self.wav_path = wav_path

    def run(self) -> None:
        try:
            log_event("transcription started")
            raw_text = self.engine.transcribe(self.wav_path)
            log_event("transcription finished")
            log_event("cleanup started")
            try:
                cleaned_text = self.cleaner.clean(raw_text)
            except Exception as exc:
                warning = str(exc)
                log_event(f"cleanup failed, falling back to raw text: {repr(exc)}")
                log_event(traceback.format_exc())
                self.cleanup_warning.emit(warning)
                cleaned_text = raw_text
            log_event("cleanup finished")
            self.finished_ok.emit(raw_text, cleaned_text)
        except Exception as exc:
            log_event(f"transcription worker failed: {repr(exc)}")
            log_event(traceback.format_exc())
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Voice Cleanup AI")
        self.resize(1020, 760)  # Expanded slightly to accommodate margins and 2-column grid

        # Modern Frameless Window Setup with Transparent Backplate
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.CustomizeWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.settings = load_settings()
        self.recorder = AudioRecorder()
        self.worker: TranscriptionWorker | None = None
        self.worker_source = "manual"
        self.push_to_talk_state = "idle"
        self.last_cleanup_warning = ""

        self._build_ui()
        self.setStyleSheet(QSS_STYLING)
        self._load_settings_into_ui()
        self._refresh_microphones()
        self.overlay = MicrophoneOverlay()
        self.hotkey_controller = PushToTalkHotkeyController()
        self.hotkey_controller.pressed.connect(self._push_to_talk_pressed)
        self.hotkey_controller.released.connect(self._push_to_talk_released)
        self.hotkey_controller.error.connect(self._push_to_talk_error)
        self._apply_push_to_talk_settings()
        self.hotkey_controller.start()

    def _build_ui(self) -> None:
        # Outer Widget is fully transparent to allow drop shadow of CentralWidget to bleed on desktop
        self.outer_widget = QWidget()
        self.outer_layout = QVBoxLayout(self.outer_widget)
        self.outer_layout.setContentsMargins(15, 15, 15, 15)  # Shadow buffer

        # Central Widget acts as the actual visible window frame
        central = QWidget()
        central.setObjectName("CentralWidget")
        
        # Soft Outer window drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(180, 160, 185, 45))
        shadow.setOffset(0, 8)
        central.setGraphicsEffect(shadow)

        self.outer_layout.addWidget(central)
        self.setCentralWidget(self.outer_widget)

        # Root Layout inside visible frame
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 8, 16, 16)
        root.setSpacing(12)

        # Add Custom Title Bar
        self.title_bar = TitleBar(self)
        root.addWidget(self.title_bar)

        # Main Workspace: 2-Column Split
        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)
        root.addLayout(body_layout)

        # Left Column - Settings Stack (40% width proportional)
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(14)
        body_layout.addLayout(settings_layout, 40)

        # Right Column - Operations Stack (60% width proportional)
        workspace_layout = QVBoxLayout()
        workspace_layout.setSpacing(14)
        body_layout.addLayout(workspace_layout, 60)

        # ------------------- LEFT COLUMN: SETTINGS CARDS -------------------

        # Card 1: Audio Device & Model Setup
        card1 = GlassCard()
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(16, 14, 16, 14)
        card1_layout.setSpacing(10)

        lbl1_title = QLabel("Audio & Model Setup")
        lbl1_title.setProperty("class", "CardHeader")
        lbl1_sub = QLabel("Select active input and transcription model size.")
        lbl1_sub.setProperty("class", "CardSubHeader")
        card1_layout.addWidget(lbl1_title)
        card1_layout.addWidget(lbl1_sub)

        mic_row = QHBoxLayout()
        lbl_mic = QLabel("Microphone:")
        lbl_mic.setFixedWidth(75)
        self.microphone_combo = QComboBox()
        refresh_mics_button = QPushButton("Refresh")
        refresh_mics_button.setObjectName("RefreshBtn")
        refresh_mics_button.clicked.connect(self._refresh_microphones)
        mic_row.addWidget(lbl_mic)
        mic_row.addWidget(self.microphone_combo, 1)
        mic_row.addWidget(refresh_mics_button)
        card1_layout.addLayout(mic_row)

        model_row = QHBoxLayout()
        lbl_model = QLabel("Model Size:")
        lbl_model.setFixedWidth(75)
        self.model_size_combo = QComboBox()
        self.model_size_combo.addItems(["base", "tiny", "small", "medium", "large"])
        model_row.addWidget(lbl_model)
        model_row.addWidget(self.model_size_combo, 1)
        card1_layout.addLayout(model_row)
        
        settings_layout.addWidget(card1)

        # Card 2: System Boundaries
        card2 = GlassCard()
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(16, 14, 16, 14)
        card2_layout.setSpacing(10)

        lbl2_title = QLabel("System Boundaries")
        lbl2_title.setProperty("class", "CardHeader")
        lbl2_sub = QLabel("Configure path boundaries for local AI execution.")
        lbl2_sub.setProperty("class", "CardSubHeader")
        card2_layout.addWidget(lbl2_title)
        card2_layout.addWidget(lbl2_sub)

        exe_row = QHBoxLayout()
        lbl_exe = QLabel("whisper.cpp:")
        lbl_exe.setFixedWidth(80)
        self.whisper_exe_edit = QLineEdit()
        self.whisper_exe_edit.setPlaceholderText("Path to main.exe or whisper-cli.exe")
        whisper_exe_button = QPushButton("Browse")
        whisper_exe_button.setObjectName("BrowseBtn")
        whisper_exe_button.clicked.connect(self._choose_whisper_exe)
        exe_row.addWidget(lbl_exe)
        exe_row.addWidget(self.whisper_exe_edit, 1)
        exe_row.addWidget(whisper_exe_button)
        card2_layout.addLayout(exe_row)

        model_row2 = QHBoxLayout()
        lbl_path = QLabel("Model File:")
        lbl_path.setFixedWidth(80)
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText("Path to ggml-base.bin")
        model_button = QPushButton("Browse")
        model_button.setObjectName("BrowseBtn")
        model_button.clicked.connect(self._choose_model_file)
        model_row2.addWidget(lbl_path)
        model_row2.addWidget(self.model_path_edit, 1)
        model_row2.addWidget(model_button)
        card2_layout.addLayout(model_row2)

        settings_layout.addWidget(card2)

        # Card 3: AI Cleanup Prompt & Shortcuts Options
        card3 = GlassCard()
        card3_layout = QVBoxLayout(card3)
        card3_layout.setContentsMargins(16, 14, 16, 14)
        card3_layout.setSpacing(10)

        lbl3_title = QLabel("AI & Behavioral Parameters")
        lbl3_title.setProperty("class", "CardHeader")
        lbl3_sub = QLabel("Configure instructions, global hotkeys, and triggers.")
        lbl3_sub.setProperty("class", "CardSubHeader")
        card3_layout.addWidget(lbl3_title)
        card3_layout.addWidget(lbl3_sub)

        self.cleanup_prompt_edit = QPlainTextEdit()
        self.cleanup_prompt_edit.setPlaceholderText("Enter AI cleanup instruction prompt...")
        self.cleanup_prompt_edit.setFixedHeight(75)
        card3_layout.addWidget(self.cleanup_prompt_edit)

        cleanup_row = QHBoxLayout()
        self.cleanup_enabled_checkbox = QCheckBox("Enable Cleanup")
        self.cleanup_backend_combo = QComboBox()
        self.cleanup_backend_combo.addItem("None", "none")
        self.cleanup_backend_combo.addItem("ASR postprocess", "asr_postprocess")
        self.cleanup_backend_combo.addItem("Ollama local model", "ollama_llm")
        cleanup_row.addWidget(self.cleanup_enabled_checkbox)
        cleanup_row.addWidget(self.cleanup_backend_combo, 1)
        card3_layout.addLayout(cleanup_row)

        ollama_url_row = QHBoxLayout()
        lbl_ollama_url = QLabel("Ollama URL:")
        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ollama_url_row.addWidget(lbl_ollama_url)
        ollama_url_row.addWidget(self.ollama_url_edit, 1)
        card3_layout.addLayout(ollama_url_row)

        ollama_model_row = QHBoxLayout()
        lbl_ollama_model = QLabel("Ollama Model:")
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setEditable(True)
        self.ollama_model_combo.addItems(["qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:3b"])
        ollama_model_row.addWidget(lbl_ollama_model)
        ollama_model_row.addWidget(self.ollama_model_combo, 1)
        card3_layout.addLayout(ollama_model_row)

        chk_grid = QGridLayout()
        self.enable_ptt_checkbox = QCheckBox("Enable Global PTT")
        self.enable_auto_paste_checkbox = QCheckBox("Auto-Paste Text")
        self.overlay_enabled_checkbox = QCheckBox("Show Overlay")
        chk_grid.addWidget(self.enable_ptt_checkbox, 0, 0)
        chk_grid.addWidget(self.enable_auto_paste_checkbox, 0, 1)
        chk_grid.addWidget(self.overlay_enabled_checkbox, 1, 0)
        card3_layout.addLayout(chk_grid)

        hotkey_row = QHBoxLayout()
        lbl_hotkey = QLabel("PTT Hotkey:")
        self.hotkey_choice_combo = QComboBox()
        self.hotkey_choice_combo.addItem("Ctrl + Windows", "ctrl_win")
        self.hotkey_choice_combo.addItem("Ctrl + Alt", "ctrl_alt")
        self.hotkey_choice_combo.addItem("Ctrl + Shift + Space", "ctrl_shift_space")
        hotkey_row.addWidget(lbl_hotkey)
        hotkey_row.addWidget(self.hotkey_choice_combo, 1)
        card3_layout.addLayout(hotkey_row)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_button = QPushButton("Save Settings")
        save_button.setObjectName("SaveBtn")
        save_button.clicked.connect(lambda: self._save_settings_from_ui())
        save_row.addWidget(save_button)
        card3_layout.addLayout(save_row)

        settings_layout.addWidget(card3)

        # ------------------- RIGHT COLUMN: WORKSPACE CARDS -------------------

        # Recording Control Panel
        controls_card = GlassCard()
        controls_layout = QHBoxLayout(controls_card)
        controls_layout.setContentsMargins(14, 12, 14, 12)
        controls_layout.setSpacing(12)

        self.start_button = QPushButton("Start Recording")
        self.start_button.setObjectName("StartBtn")
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.setObjectName("StopBtn")
        self.stop_button.setEnabled(False)

        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)

        controls_layout.addWidget(self.start_button, 1)
        controls_layout.addWidget(self.stop_button, 1)
        workspace_layout.addWidget(controls_card)

        # Raw Transcription Card
        raw_card = GlassCard()
        raw_layout = QVBoxLayout(raw_card)
        raw_layout.setContentsMargins(14, 12, 14, 12)
        raw_layout.setSpacing(6)

        lbl_raw = QLabel("Raw Transcription")
        lbl_raw.setProperty("class", "CardHeader")
        self.raw_text = QPlainTextEdit()
        self.raw_text.setObjectName("RawText")
        self.raw_text.setPlaceholderText("Spoken audio transcription will appear here...")
        raw_layout.addWidget(lbl_raw)
        raw_layout.addWidget(self.raw_text, 1)
        workspace_layout.addWidget(raw_card, 1)

        # Cleaned Text Card
        clean_card = GlassCard()
        clean_layout = QVBoxLayout(clean_card)
        clean_layout.setContentsMargins(14, 12, 14, 12)
        clean_layout.setSpacing(6)

        lbl_clean = QLabel("Cleaned Text (AI Enhanced)")
        lbl_clean.setProperty("class", "CardHeader")
        self.cleaned_text = QPlainTextEdit()
        self.cleaned_text.setObjectName("CleanText")
        self.cleaned_text.setPlaceholderText("Polished, clean AI text will appear here...")
        clean_layout.addWidget(lbl_clean)
        clean_layout.addWidget(self.cleaned_text, 1)
        workspace_layout.addWidget(clean_card, 1)

        # Status & Action Bar
        bottom_card = GlassCard()
        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(16, 10, 16, 10)

        self.status_label = QLabel("System Status: Ready")
        self.status_label.setObjectName("StatusLabel")

        copy_button = QPushButton("Copy Cleaned Text")
        copy_button.setObjectName("CopyBtn")
        copy_button.clicked.connect(self.copy_cleaned_text)

        bottom_layout.addWidget(self.status_label, 1)
        bottom_layout.addWidget(copy_button)
        workspace_layout.addWidget(bottom_card)

        # True global hotkey activator shortcut inside window
        shortcut = QShortcut(QKeySequence("Ctrl+Meta"), self)
        shortcut.activated.connect(self._toggle_recording)

    def _load_settings_into_ui(self) -> None:
        self.model_size_combo.setCurrentText(self.settings.model_size)
        self.whisper_exe_edit.setText(self.settings.whisper_exe_path)
        self.model_path_edit.setText(self.settings.model_path)
        self.cleanup_prompt_edit.setPlainText(self.settings.cleanup_prompt)
        self.cleanup_enabled_checkbox.setChecked(self.settings.cleanup_enabled)
        cleanup_index = self.cleanup_backend_combo.findData(self.settings.cleanup_backend)
        self.cleanup_backend_combo.setCurrentIndex(cleanup_index if cleanup_index >= 0 else 1)
        self.ollama_url_edit.setText(self.settings.ollama_url)
        ollama_model_index = self.ollama_model_combo.findText(self.settings.ollama_model)
        if ollama_model_index >= 0:
            self.ollama_model_combo.setCurrentIndex(ollama_model_index)
        else:
            self.ollama_model_combo.setEditText(self.settings.ollama_model)
        self.enable_ptt_checkbox.setChecked(self.settings.enable_global_push_to_talk)
        self.enable_auto_paste_checkbox.setChecked(self.settings.enable_auto_paste)
        self.overlay_enabled_checkbox.setChecked(self.settings.overlay_enabled)
        index = self.hotkey_choice_combo.findData(self.settings.hotkey_choice)
        self.hotkey_choice_combo.setCurrentIndex(index if index >= 0 else 0)

    def _settings_from_ui(self) -> AppSettings:
        return AppSettings(
            microphone_name=self.microphone_combo.currentText(),
            model_size=self.model_size_combo.currentText(),
            whisper_exe_path=self.whisper_exe_edit.text().strip(),
            model_path=self.model_path_edit.text().strip(),
            cleanup_prompt=self.cleanup_prompt_edit.toPlainText().strip(),
            cleanup_backend=self.cleanup_backend_combo.currentData(),
            cleanup_enabled=self.cleanup_enabled_checkbox.isChecked(),
            ollama_url=self.ollama_url_edit.text().strip() or "http://localhost:11434",
            ollama_model=self.ollama_model_combo.currentText().strip() or "qwen2.5:1.5b",
            enable_global_push_to_talk=self.enable_ptt_checkbox.isChecked(),
            enable_auto_paste=self.enable_auto_paste_checkbox.isChecked(),
            overlay_enabled=self.overlay_enabled_checkbox.isChecked(),
            hotkey_choice=self.hotkey_choice_combo.currentData(),
        )

    def _save_settings_from_ui(self, apply_hotkey_settings: bool = True) -> None:
        self.settings = self._settings_from_ui()
        save_settings(self.settings)
        if apply_hotkey_settings and hasattr(self, "hotkey_controller"):
            self._apply_push_to_talk_settings()
        self.status_label.setText("System Status: Settings saved")

    def _refresh_microphones(self) -> None:
        current = self.settings.microphone_name
        self.microphone_combo.clear()
        try:
            devices = list_input_devices()
            log_event(f"refresh_microphones found {len(devices)} input devices")
            for device in devices:
                log_event(f"microphone option index={device.index} name={device.name}")
                self.microphone_combo.addItem(device.name, device.index)
        except Exception as exc:
            log_event(f"refresh_microphones failed: {repr(exc)}")
            self._show_error(f"Could not list microphone devices. Original error: {exc}")
            return

        if current:
            matches = self.microphone_combo.findText(current)
            if matches >= 0:
                self.microphone_combo.setCurrentIndex(matches)

        if self.microphone_combo.count() == 0:
            self.status_label.setText("System Status: No microphone devices found")

    def _choose_whisper_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose whisper.cpp executable", "", "Executable (*.exe);;All files (*)")
        if path:
            self.whisper_exe_edit.setText(path)

    def _choose_model_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose whisper.cpp model", "", "Whisper model (*.bin);;All files (*)")
        if path:
            self.model_path_edit.setText(path)

    def _toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        try:
            try:
                log_event("start_recording: saving settings")
                self._save_settings_from_ui()
            except Exception as exc:
                log_event(f"start_recording settings save failed: {repr(exc)}")
                raise RuntimeError(
                    "Settings save failed before recording started. "
                    "Check permissions for the local settings file. "
                    f"Original error: {exc}"
                ) from exc

            device_index = self.microphone_combo.currentData()
            device_name = self.microphone_combo.currentText()
            print(f"[ui] start_recording device_name={device_name}")
            print(f"[ui] start_recording device_index={device_index}")
            log_event(f"start_recording device_name={device_name}")
            log_event(f"start_recording device_index={device_index}")
            self.recorder.start(device_index=device_index)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("System Status: Recording...")
            log_event("start_recording succeeded")
        except Exception as exc:
            log_event(f"start_recording failed: {repr(exc)}")
            self._show_error(str(exc))

    def stop_recording(self) -> None:
        try:
            wav_path = self.recorder.stop()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            log_event(f"audio saved path={wav_path}")

            settings = self._settings_from_ui()
            if not settings.whisper_exe_path or not settings.model_path:
                message = (
                    "Recording saved successfully. Set the whisper.cpp executable and model file "
                    "before transcription."
                )
                log_event(f"stop_recording skipped transcription: {message} wav_path={wav_path}")
                self.start_button.setEnabled(True)
                self.status_label.setText(message)
                return

            self.status_label.setText("System Status: Transcribing...")
            self.last_cleanup_warning = ""
            self.worker_source = "manual"
            engine = WhisperCppEngine(
                executable_path=settings.whisper_exe_path,
                model_path=settings.model_path,
            )
            cleaner = self._create_cleaner(settings)
            self.worker = TranscriptionWorker(engine, cleaner, wav_path)
            self.worker.finished_ok.connect(self._transcription_finished)
            self.worker.failed.connect(self._transcription_failed)
            self.worker.cleanup_warning.connect(self._cleanup_warning)
            self.worker.start()
        except Exception as exc:
            log_event(f"stop_recording failed: {repr(exc)}")
            log_event(traceback.format_exc())
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._show_error(str(exc))

    def _transcription_finished(self, raw_text: str, cleaned_text: str) -> None:
        self.raw_text.setPlainText(raw_text)
        self.cleaned_text.setPlainText(cleaned_text)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self.last_cleanup_warning:
            self.status_label.setText(f"System Status: {self.last_cleanup_warning} Falling back to raw text.")
        else:
            self.status_label.setText("System Status: Ready")
        if self.worker_source == "push_to_talk":
            self._finish_push_to_talk(raw_text, cleaned_text)

    def _transcription_failed(self, message: str) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self.worker_source == "push_to_talk":
            self.push_to_talk_state = "error"
            self._set_overlay_state("error")
        self._show_error(message)

    def copy_cleaned_text(self) -> None:
        QApplication.clipboard().setText(self.cleaned_text.toPlainText())
        log_event("clipboard copied from button")
        self.status_label.setText("System Status: Cleaned text copied to clipboard!")

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"System Status: Error: {message}")
        QMessageBox.warning(self, "Voice Cleanup AI", message)

    def _cleanup_warning(self, message: str) -> None:
        self.last_cleanup_warning = message
        self.status_label.setText(f"System Status: {message} Falling back to raw text.")
        log_event(f"cleanup warning shown: {message}")

    def closeEvent(self, event) -> None:
        if hasattr(self, "hotkey_controller"):
            self.hotkey_controller.stop()
        if hasattr(self, "overlay"):
            self.overlay.close()
        super().closeEvent(event)

    def _apply_push_to_talk_settings(self) -> None:
        settings = self._settings_from_ui()
        self.hotkey_controller.configure(settings.enable_global_push_to_talk, settings.hotkey_choice)
        if not settings.overlay_enabled:
            self.overlay.hide()

    @Slot()
    def _push_to_talk_pressed(self) -> None:
        settings = self._settings_from_ui()
        if not settings.enable_global_push_to_talk:
            return
        if self.push_to_talk_state in ("recording", "processing"):
            log_event(f"push_to_talk press ignored state={self.push_to_talk_state}")
            return
        if self.recorder.is_recording:
            log_event("push_to_talk press ignored because recorder is already recording")
            return

        try:
            log_event("push_to_talk start recording")
            self._save_settings_from_ui(apply_hotkey_settings=False)
            device_index = self.microphone_combo.currentData()
            self.recorder.start(device_index=device_index)
            self.push_to_talk_state = "recording"
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.status_label.setText("System Status: PTT Recording...")
            self._set_overlay_state("recording")
        except Exception as exc:
            self.push_to_talk_state = "error"
            self._set_overlay_state("error")
            log_event(f"push_to_talk start failed: {repr(exc)}")
            log_event(traceback.format_exc())
            self._show_error(str(exc))

    @Slot()
    def _push_to_talk_released(self) -> None:
        if self.push_to_talk_state != "recording":
            log_event(f"push_to_talk release ignored state={self.push_to_talk_state}")
            return

        try:
            log_event("push_to_talk stop recording")
            wav_path = self.recorder.stop()
            log_event(f"audio saved path={wav_path}")
            self.push_to_talk_state = "processing"
            self.status_label.setText("System Status: PTT Processing...")
            self._set_overlay_state("processing")
            self._start_push_to_talk_worker(wav_path)
        except Exception as exc:
            self.push_to_talk_state = "error"
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._set_overlay_state("error")
            log_event(f"push_to_talk stop failed: {repr(exc)}")
            log_event(traceback.format_exc())
            self._show_error(str(exc))

    def _start_push_to_talk_worker(self, wav_path: Path) -> None:
        settings = self._settings_from_ui()
        engine = WhisperCppEngine(
            executable_path=settings.whisper_exe_path,
            model_path=settings.model_path,
        )
        cleaner = self._create_cleaner(settings)
        self.worker_source = "push_to_talk"
        self.last_cleanup_warning = ""
        self.worker = TranscriptionWorker(engine, cleaner, wav_path)
        self.worker.finished_ok.connect(self._transcription_finished)
        self.worker.failed.connect(self._transcription_failed)
        self.worker.cleanup_warning.connect(self._cleanup_warning)
        self.worker.start()

    def _create_cleaner(self, settings: AppSettings):
        if not settings.cleanup_enabled or settings.cleanup_backend == "none":
            log_event("cleanup backend disabled")
            return NoOpCleaner()
        if settings.cleanup_backend == "ollama_llm":
            log_event(f"cleanup backend ollama url={settings.ollama_url} model={settings.ollama_model}")
            return OllamaCleaner(
                base_url=settings.ollama_url,
                model=settings.ollama_model,
                prompt=settings.cleanup_prompt,
            )

        log_event("cleanup backend asr_postprocess")
        return ASRPostProcessor()

    def _finish_push_to_talk(self, raw_text: str, cleaned_text: str) -> None:
        self.push_to_talk_state = "done"
        self._set_overlay_state("done")
        if cleaned_text.strip():
            QApplication.clipboard().setText(cleaned_text)
            log_event("clipboard copied from push_to_talk")
            if self._settings_from_ui().enable_auto_paste:
                log_event("auto-paste scheduled")
                QTimer.singleShot(250, self._auto_paste_cleaned_text)
        else:
            log_event("push_to_talk cleaned text empty; clipboard/paste skipped")

        QTimer.singleShot(900, self._reset_push_to_talk_overlay)

    def _auto_paste_cleaned_text(self) -> None:
        if not self._settings_from_ui().enable_auto_paste:
            return
        try:
            import pyautogui

            pyautogui.hotkey("ctrl", "v")
            log_event("auto-paste attempted")
        except Exception as exc:
            log_event(f"auto-paste failed: {repr(exc)}")
            log_event(traceback.format_exc())

    def _reset_push_to_talk_overlay(self) -> None:
        if self.push_to_talk_state == "done":
            self.push_to_talk_state = "idle"
            self._set_overlay_state("idle")

    def _set_overlay_state(self, state: str) -> None:
        if self._settings_from_ui().overlay_enabled:
            self.overlay.set_state(state)
        else:
            self.overlay.hide()

    @Slot(str)
    def _push_to_talk_error(self, message: str) -> None:
        self.push_to_talk_state = "error"
        self._set_overlay_state("error")
        self._show_error(f"Global push-to-talk failed: {message}")
