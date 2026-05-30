from pathlib import Path
import traceback

from PySide6.QtCore import QThread, QTimer, Signal, Slot, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut, QColor
from PySide6.QtWidgets import (
    QApplication,
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
    QGraphicsDropShadowEffect,
)

from audio.recorder import AudioRecorder, list_input_devices, log_event
from cleanup.asr_postprocess import ASRPostProcessor
from cleanup.ai_cleanup import NoOpCleaner
from cleanup.ollama_cleanup import OllamaCleaner
from config.dictation_stats import load_today_stats, record_dictation_session
from config.settings import (
    AppSettings,
    WHISPER_MODELS,
    get_whisper_model_info,
    get_whisper_model_path,
    load_settings,
    save_settings,
    WHISPER_MODELS_DIR,
)
from frontend.hotkey_controller import PushToTalkHotkeyController
from frontend.overlay import MicrophoneOverlay
from transcription.whisper_engine import WhisperCppEngine
from frontend.styles import QSS_STYLING, TitleBar, GlassCard, SwitchToggle, SegmentedControl
from frontend.stats_dialog import StatisticsDashboardDialog


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
        self.setWindowTitle("Voice Cleanup")
        self.resize(1020, 600)  # Wider, calmer proportions

        # Frameless Window Setup with Translucent Backplate
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

        # Set initial status dot & visibility
        self.set_app_status("idle")
        if self.settings.overlay_enabled:
            self.overlay.set_state("idle")
            self.overlay.show()

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
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 6)
        central.setGraphicsEffect(shadow)

        self.outer_layout.addWidget(central)
        self.setCentralWidget(self.outer_widget)

        # Root Layout inside visible frame
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 10, 20, 20)
        root.setSpacing(14)

        # Add Custom Title Bar
        self.title_bar = TitleBar(self)
        root.addWidget(self.title_bar)

        # Main Workspace: 2-Column Split
        body_layout = QHBoxLayout()
        body_layout.setSpacing(20)
        root.addLayout(body_layout)

        # Left Column - Compact Settings card & stretch (40% width)
        settings_column = QVBoxLayout()
        settings_column.setSpacing(0)
        body_layout.addLayout(settings_column, 40)

        # Right Column - Document stacked cards (60% width)
        text_column = QVBoxLayout()
        text_column.setSpacing(16)
        body_layout.addLayout(text_column, 60)

        # ------------------- LEFT COLUMN: SINGLE SETTINGS CARD -------------------
        settings_card = GlassCard()
        card_layout = QVBoxLayout(settings_card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # Header Title
        lbl_settings_title = QLabel("Settings")
        lbl_settings_title.setProperty("class", "CardHeader")
        card_layout.addWidget(lbl_settings_title)

        # Field 1: Microphone Dropdown
        lbl_mic_head = QLabel("Microphone")
        lbl_mic_head.setStyleSheet("font-weight: bold; color: #1D1D1F;")
        card_layout.addWidget(lbl_mic_head)

        mic_row = QHBoxLayout()
        mic_row.setSpacing(8)
        self.microphone_combo = QComboBox()
        self.microphone_combo.setFixedHeight(30)
        refresh_mics_button = QPushButton("Refresh")
        refresh_mics_button.setObjectName("RefreshBtn")
        refresh_mics_button.setFixedHeight(30)
        refresh_mics_button.clicked.connect(self._refresh_microphones)
        mic_row.addWidget(self.microphone_combo, 1)
        mic_row.addWidget(refresh_mics_button)
        card_layout.addLayout(mic_row)

        # Field 2: Transcription Quality (macOS Segmented Control)
        lbl_quality_head = QLabel("Transcription Quality")
        lbl_quality_head.setStyleSheet("font-weight: bold; color: #1D1D1F; margin-top: 4px;")
        card_layout.addWidget(lbl_quality_head)

        self.model_size_segmented = SegmentedControl([
            ("Fast", "base"),
            ("Balanced", "small"),
            ("Accurate", "medium")
        ])
        self.model_size_segmented.valueChanged.connect(self._model_selection_changed)
        card_layout.addWidget(self.model_size_segmented)

        self.model_status_label = QLabel("")
        self.model_status_label.setWordWrap(True)
        self.model_status_label.setProperty("class", "CardSubHeader")
        card_layout.addWidget(self.model_status_label)

        # Field 3: Dictation Toggles
        lbl_toggles_head = QLabel("Dictation Toggles")
        lbl_toggles_head.setStyleSheet("font-weight: bold; color: #1D1D1F; margin-top: 4px;")
        card_layout.addWidget(lbl_toggles_head)

        # Switch Toggle 1: Smart Cleanup
        t1_row = QHBoxLayout()
        self.cleanup_enabled_switch = SwitchToggle("Smart Cleanup")
        t1_row.addWidget(self.cleanup_enabled_switch, 1)
        card_layout.addLayout(t1_row)

        # Switch Toggle 2: Auto Paste
        t2_row = QHBoxLayout()
        self.enable_auto_paste_switch = SwitchToggle("Auto Paste")
        t2_row.addWidget(self.enable_auto_paste_switch, 1)
        card_layout.addLayout(t2_row)

        # Switch Toggle 3: Push-to-Talk
        t3_row = QHBoxLayout()
        self.enable_ptt_switch = SwitchToggle("Push-to-Talk")
        t3_row.addWidget(self.enable_ptt_switch, 1)
        card_layout.addLayout(t3_row)

        card_layout.addSpacing(4)

        # Advanced Settings collapsible trigger row
        self.adv_toggle_btn = QPushButton("Advanced Settings ▸")
        self.adv_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv_toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #007AFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                padding: 4px 0px;
                min-height: 20px;
            }
            QPushButton:hover {
                color: #0056B3;
            }
        """)
        self.adv_toggle_btn.clicked.connect(self._toggle_advanced_settings)
        card_layout.addWidget(self.adv_toggle_btn)

        # Collapsible technical advanced container widget
        self.adv_container = QWidget()
        adv_sub_layout = QVBoxLayout(self.adv_container)
        adv_sub_layout.setContentsMargins(0, 4, 0, 4)
        adv_sub_layout.setSpacing(10)

        # Show Desktop Overlay switch
        self.overlay_enabled_switch = SwitchToggle("Show Desktop Overlay")
        adv_sub_layout.addWidget(self.overlay_enabled_switch)

        # Shortcut choice dropdown
        shortcut_row = QHBoxLayout()
        lbl_shortcut = QLabel("PTT Shortcut:")
        lbl_shortcut.setStyleSheet("color: #6E6E73;")
        self.hotkey_choice_combo = QComboBox()
        self.hotkey_choice_combo.addItem("Ctrl + Windows", "ctrl_win")
        self.hotkey_choice_combo.addItem("Ctrl + Alt", "ctrl_alt")
        self.hotkey_choice_combo.addItem("Ctrl + Shift + Space", "ctrl_shift_space")
        shortcut_row.addWidget(lbl_shortcut)
        shortcut_row.addWidget(self.hotkey_choice_combo, 1)
        adv_sub_layout.addLayout(shortcut_row)

        # Speech Engine path
        exe_row = QHBoxLayout()
        lbl_exe = QLabel("Speech Engine:")
        lbl_exe.setStyleSheet("color: #6E6E73;")
        self.whisper_exe_edit = QLineEdit()
        self.whisper_exe_edit.setPlaceholderText("Path to whisper-cli.exe")
        whisper_exe_button = QPushButton("Browse")
        whisper_exe_button.setObjectName("BrowseBtn")
        whisper_exe_button.setFixedHeight(26)
        whisper_exe_button.clicked.connect(self._choose_whisper_exe)
        exe_row.addWidget(lbl_exe)
        exe_row.addWidget(self.whisper_exe_edit, 1)
        exe_row.addWidget(whisper_exe_button)
        adv_sub_layout.addLayout(exe_row)

        # Model file
        model_row2 = QHBoxLayout()
        lbl_path = QLabel("Model File:")
        lbl_path.setStyleSheet("color: #6E6E73;")
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setReadOnly(True)
        model_folder_button = QPushButton("Folder")
        model_folder_button.setObjectName("BrowseBtn")
        model_folder_button.setFixedHeight(26)
        model_folder_button.clicked.connect(self._open_models_folder)
        model_row2.addWidget(lbl_path)
        model_row2.addWidget(self.model_path_edit, 1)
        model_row2.addWidget(model_folder_button)
        adv_sub_layout.addLayout(model_row2)

        # Cleanup Style backend selector
        cleanup_backend_row = QHBoxLayout()
        lbl_cleanup_backend = QLabel("Cleanup Style:")
        lbl_cleanup_backend.setStyleSheet("color: #6E6E73;")
        self.cleanup_backend_combo = QComboBox()
        self.cleanup_backend_combo.addItem("None", "none")
        self.cleanup_backend_combo.addItem("Smart Cleanup", "asr_postprocess")
        self.cleanup_backend_combo.addItem("AI Rewrite Cleanup", "ollama_llm")
        cleanup_backend_row.addWidget(lbl_cleanup_backend)
        cleanup_backend_row.addWidget(self.cleanup_backend_combo, 1)
        adv_sub_layout.addLayout(cleanup_backend_row)

        # AI Server URL
        ollama_url_row = QHBoxLayout()
        lbl_ollama_url = QLabel("AI Server URL:")
        lbl_ollama_url.setStyleSheet("color: #6E6E73;")
        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ollama_url_row.addWidget(lbl_ollama_url)
        ollama_url_row.addWidget(self.ollama_url_edit, 1)
        adv_sub_layout.addLayout(ollama_url_row)

        # AI Model dropdown
        ollama_model_row = QHBoxLayout()
        lbl_ollama_model = QLabel("AI Model:")
        lbl_ollama_model.setStyleSheet("color: #6E6E73;")
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setEditable(True)
        self.ollama_model_combo.addItems(["qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:3b"])
        ollama_model_row.addWidget(lbl_ollama_model)
        ollama_model_row.addWidget(self.ollama_model_combo, 1)
        adv_sub_layout.addLayout(ollama_model_row)

        # Smart Cleanup Advanced Instructions
        lbl_adv_prompt = QLabel("Smart Cleanup Instructions:")
        lbl_adv_prompt.setStyleSheet("color: #6E6E73; font-weight: bold;")
        self.cleanup_prompt_edit = QPlainTextEdit()
        self.cleanup_prompt_edit.setPlaceholderText("Advanced cleanup instructions...")
        self.cleanup_prompt_edit.setFixedHeight(64)
        adv_sub_layout.addWidget(lbl_adv_prompt)
        adv_sub_layout.addWidget(self.cleanup_prompt_edit)

        self.adv_container.setVisible(False)
        card_layout.addWidget(self.adv_container)

        # Save Settings button at the bottom of settings card
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.setObjectName("SaveBtn")
        self.save_settings_btn.setFixedHeight(34)
        self.save_settings_btn.clicked.connect(lambda: self._save_settings_from_ui())
        card_layout.addWidget(self.save_settings_btn)

        settings_column.addWidget(settings_card)
        settings_column.addStretch()  # Pack tightly at the top

        # ------------------- RIGHT COLUMN: ORIGINAL & CLEANED READABLE CARDS -------------------
        
        # Card 1: Original Text Card
        original_card = GlassCard()
        original_layout = QVBoxLayout(original_card)
        original_layout.setContentsMargins(20, 16, 20, 16)
        original_layout.setSpacing(8)

        lbl_original = QLabel("Original Text")
        lbl_original.setProperty("class", "CardHeader")
        self.raw_text = QPlainTextEdit()
        self.raw_text.setObjectName("RawText")
        self.raw_text.setPlaceholderText("Spoken audio transcription will appear here...")
        self.raw_text.setStyleSheet("""
            QPlainTextEdit#RawText {
                border: none;
                background-color: transparent;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 14px;
                color: #1D1D1F;
                padding: 0px;
            }
        """)
        
        # Style placeholder palette to clean gray #AEAEB2
        p_raw = self.raw_text.palette()
        p_raw.setColor(p_raw.ColorRole.PlaceholderText, QColor("#AEAEB2"))
        self.raw_text.setPalette(p_raw)
        
        original_layout.addWidget(lbl_original)
        original_layout.addWidget(self.raw_text, 1)
        text_column.addWidget(original_card, 1)

        # Card 2: Cleaned Text Card
        cleaned_card = GlassCard()
        cleaned_layout = QVBoxLayout(cleaned_card)
        cleaned_layout.setContentsMargins(20, 16, 20, 16)
        cleaned_layout.setSpacing(8)

        lbl_cleaned = QLabel("Cleaned Text")
        lbl_cleaned.setProperty("class", "CardHeader")
        self.cleaned_text = QPlainTextEdit()
        self.cleaned_text.setObjectName("CleanText")
        self.cleaned_text.setPlaceholderText("AI-cleaned text will appear here...")
        self.cleaned_text.setStyleSheet("""
            QPlainTextEdit#CleanText {
                border: none;
                background-color: transparent;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 14px;
                color: #1D1D1F;
                padding: 0px;
            }
        """)
        
        # Style placeholder palette to clean gray #AEAEB2
        p_clean = self.cleaned_text.palette()
        p_clean.setColor(p_clean.ColorRole.PlaceholderText, QColor("#AEAEB2"))
        self.cleaned_text.setPalette(p_clean)
        
        cleaned_layout.addWidget(lbl_cleaned)
        cleaned_layout.addWidget(self.cleaned_text, 1)
        text_column.addWidget(cleaned_card, 1)

        # ------------------- BOTTOM UTILITY BAR (EMOJI-FREE) -------------------
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(2, 6, 2, 2)
        bottom_row.setSpacing(10)

        # Left side buttons: Record, Copy, Settings, Stats
        self.record_button = QPushButton("Start Recording")
        self.record_button.setObjectName("RecordToggleBtn")
        self.record_button.setFixedHeight(34)
        self.record_button.clicked.connect(self._toggle_recording)
        
        copy_button = QPushButton("Copy Cleaned Text")
        copy_button.setFixedHeight(34)
        copy_button.clicked.connect(self.copy_cleaned_text)

        settings_button = QPushButton("Settings")
        settings_button.setFixedHeight(34)
        settings_button.clicked.connect(self._toggle_advanced_settings)

        stats_button = QPushButton("Stats")
        stats_button.setFixedHeight(34)
        stats_button.clicked.connect(self.show_stats_dashboard)

        bottom_row.addWidget(self.record_button)
        bottom_row.addWidget(copy_button)
        bottom_row.addWidget(settings_button)
        bottom_row.addWidget(stats_button)

        bottom_row.addStretch()

        # Right side status indicator label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 12px; color: #6E6E73; font-weight: 500; font-family: 'Segoe UI';")
        bottom_row.addWidget(self.status_label)

        root.addLayout(bottom_row)

        # Global hotkey shortcut inside active window as well
        shortcut = QShortcut(QKeySequence("Ctrl+Meta"), self)
        shortcut.activated.connect(self._toggle_recording)

    def _load_settings_into_ui(self) -> None:
        self.model_size_segmented.set_value(self.settings.model_size)
        self.whisper_exe_edit.setText(self.settings.whisper_exe_path)
        self._model_selection_changed()
        
        self.cleanup_prompt_edit.setPlainText(self.settings.cleanup_prompt)
        self.cleanup_enabled_switch.setChecked(self.settings.cleanup_enabled)
        
        cleanup_index = self.cleanup_backend_combo.findData(self.settings.cleanup_backend)
        self.cleanup_backend_combo.setCurrentIndex(cleanup_index if cleanup_index >= 0 else 1)
        
        self.ollama_url_edit.setText(self.settings.ollama_url)
        ollama_model_index = self.ollama_model_combo.findText(self.settings.ollama_model)
        if ollama_model_index >= 0:
            self.ollama_model_combo.setCurrentIndex(ollama_model_index)
        else:
            self.ollama_model_combo.setEditText(self.settings.ollama_model)
            
        self.enable_ptt_switch.setChecked(self.settings.enable_global_push_to_talk)
        self.enable_auto_paste_switch.setChecked(self.settings.enable_auto_paste)
        self.overlay_enabled_switch.setChecked(self.settings.overlay_enabled)
        
        index = self.hotkey_choice_combo.findData(self.settings.hotkey_choice)
        self.hotkey_choice_combo.setCurrentIndex(index if index >= 0 else 0)

    def _settings_from_ui(self) -> AppSettings:
        return AppSettings(
            microphone_name=self.microphone_combo.currentText(),
            model_size=self.model_size_segmented.currentData(),
            whisper_exe_path=self.whisper_exe_edit.text().strip(),
            model_path=str(get_whisper_model_path(self.model_size_segmented.currentData())),
            cleanup_prompt=self.cleanup_prompt_edit.toPlainText().strip(),
            cleanup_backend=self.cleanup_backend_combo.currentData(),
            cleanup_enabled=self.cleanup_enabled_switch.isChecked(),
            ollama_url=self.ollama_url_edit.text().strip() or "http://localhost:11434",
            ollama_model=self.ollama_model_combo.currentText().strip() or "qwen2.5:1.5b",
            enable_global_push_to_talk=self.enable_ptt_switch.isChecked(),
            enable_auto_paste=self.enable_auto_paste_switch.isChecked(),
            overlay_enabled=self.overlay_enabled_switch.isChecked(),
            hotkey_choice=self.hotkey_choice_combo.currentData(),
        )

    def _save_settings_from_ui(self, apply_hotkey_settings: bool = True) -> None:
        self.settings = self._settings_from_ui()
        save_settings(self.settings)
        if apply_hotkey_settings and hasattr(self, "hotkey_controller"):
            self._apply_push_to_talk_settings()
        self.set_app_status("idle", "Settings saved")

    def _toggle_advanced_settings(self) -> None:
        visible = not self.adv_container.isVisible()
        self.adv_container.setVisible(visible)
        self.adv_toggle_btn.setText("Advanced Settings ▾" if visible else "Advanced Settings ▸")

    def _record_dictation_stats(self, raw_text: str, cleaned_text: str) -> None:
        stats_text = cleaned_text.strip() or raw_text.strip()
        if not stats_text:
            return
        
        duration = getattr(self.recorder, "last_duration", 0.0)
        mic_name = self.microphone_combo.currentText() or "Default Microphone"
        
        record_dictation_session(stats_text, duration_seconds=duration, microphone=mic_name)

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
            self.set_app_status("idle", "No microphone devices found")

    def _choose_whisper_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose whisper.cpp executable", "", "Executable (*.exe);;All files (*)")
        if path:
            self.whisper_exe_edit.setText(path)

    def _open_models_folder(self) -> None:
        WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(WHISPER_MODELS_DIR)))

    def _model_selection_changed(self) -> None:
        model_size = self.model_size_segmented.currentData() or "base"
        model_path = get_whisper_model_path(model_size)
        model_info = get_whisper_model_info(model_size)
        installed_text = "Installed" if model_path.is_file() else "Missing"
        self.model_path_edit.setText(str(model_path))
        self.model_status_label.setText(
            f"{model_info['label']}: {model_info['description']} ({model_info['size']}) - {installed_text}"
        )

    def _toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        try:
            try:
                log_event("start_recording: saving settings")
                self._save_settings_from_ui(apply_hotkey_settings=False)
            except Exception as exc:
                log_event(f"start_recording settings save failed: {repr(exc)}")
                raise RuntimeError(
                    "Settings save failed before recording started. "
                    "Check permissions for the local settings file. "
                    f"Original error: {exc}"
                ) from exc

            device_index = self.microphone_combo.currentData()
            device_name = self.microphone_combo.currentText()
            log_event(f"start_recording device_name={device_name} index={device_index}")
            
            self.recorder.start(device_index=device_index)
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("QPushButton#RecordToggleBtn { color: #FF3B30; font-weight: bold; }")
            
            self.set_app_status("recording")
            log_event("start_recording succeeded")
        except Exception as exc:
            log_event(f"start_recording failed: {repr(exc)}")
            self.set_app_status("error", f"Error: {exc}")
            self._show_error(str(exc))

    def stop_recording(self) -> None:
        try:
            wav_path = self.recorder.stop()
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("")
            log_event(f"audio saved path={wav_path}")

            settings = self._settings_from_ui()
            if not settings.whisper_exe_path or not settings.model_path:
                message = "Recording saved. Select executable and model."
                log_event(f"stop_recording skipped transcription: {message} wav_path={wav_path}")
                self.set_app_status("idle", message)
                return
            if not self._ensure_selected_model_available(settings):
                self.set_app_status("idle", "Selected Whisper model is missing")
                return

            self.set_app_status("processing")
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
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("")
            self.set_app_status("error", f"Error: {exc}")
            self._show_error(str(exc))

    def _transcription_finished(self, raw_text: str, cleaned_text: str) -> None:
        self.raw_text.setPlainText(raw_text)
        self.cleaned_text.setPlainText(cleaned_text)
        self._record_dictation_stats(raw_text, cleaned_text)
        
        if self.last_cleanup_warning:
            self.set_app_status("idle", f"Ready (Warning: {self.last_cleanup_warning})")
        else:
            self.set_app_status("idle", "Ready")
            
        if self.worker_source == "push_to_talk":
            self._finish_push_to_talk(raw_text, cleaned_text)

    def _transcription_failed(self, message: str) -> None:
        self.record_button.setText("Start Recording")
        self.record_button.setStyleSheet("")
        
        self.set_app_status("error", f"Error: {message}")
        QTimer.singleShot(2500, lambda: self.set_app_status("idle"))
        
        if self.worker_source == "push_to_talk":
            self.push_to_talk_state = "error"
            
        self._show_error(message)

    def copy_cleaned_text(self) -> None:
        QApplication.clipboard().setText(self.cleaned_text.toPlainText())
        log_event("clipboard copied from button")
        self.status_label.setText("Cleaned text copied!")

    def show_stats_dashboard(self) -> None:
        dialog = StatisticsDashboardDialog(self)
        dialog.exec()

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Voice Cleanup", message)

    def _cleanup_warning(self, message: str) -> None:
        self.last_cleanup_warning = message
        self.status_label.setText(f"Warning: {message}")
        log_event(f"cleanup warning: {message}")

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
        else:
            self.overlay.set_state("idle")
            self.overlay.show()

    def set_app_status(self, state: str, message: str = "") -> None:
        # Sync Status dot & text on Title bar
        self.title_bar.set_status(state)
        
        # Sync bottom label status text
        if message:
            self.status_label.setText(message)
        else:
            if state == "idle":
                self.status_label.setText("Ready")
            elif state == "recording":
                self.status_label.setText("Listening...")
            elif state == "processing":
                self.status_label.setText("Processing...")
            elif state == "error":
                self.status_label.setText("Error")
                
        # Sync Floating overlay state
        self._set_overlay_state(state)

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
            self.set_app_status("recording")
        except Exception as exc:
            self.push_to_talk_state = "error"
            self.set_app_status("error", f"PTT Error: {exc}")
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
            self.set_app_status("processing")
            self._start_push_to_talk_worker(wav_path)
        except Exception as exc:
            self.push_to_talk_state = "error"
            self.set_app_status("error", f"PTT Error: {exc}")
            log_event(f"push_to_talk stop failed: {repr(exc)}")
            log_event(traceback.format_exc())
            self._show_error(str(exc))

    def _start_push_to_talk_worker(self, wav_path: Path) -> None:
        settings = self._settings_from_ui()
        if not self._ensure_selected_model_available(settings):
            self.push_to_talk_state = "error"
            self.set_app_status("error", "Whisper model missing")
            return
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

    def _ensure_selected_model_available(self, settings: AppSettings) -> bool:
        model_path = get_whisper_model_path(settings.model_size)
        if model_path.is_file():
            return True

        model_info = get_whisper_model_info(settings.model_size)
        message = (
            f"The selected Whisper model is not installed yet.\n\n"
            f"Model: {model_info['label']} - {model_info['description']} ({model_info['size']})\n"
            f"Expected file:\n{model_path}\n\n"
            "Do you want to download it now?"
        )
        choice = QMessageBox.question(
            self,
            "Download Whisper Model",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            self._download_selected_model(settings.model_size)
        self._model_selection_changed()
        return model_path.is_file()

    def _download_selected_model(self, model_size: str) -> None:
        try:
            from download_models import download_model

            self.status_label.setText("Downloading Whisper model...")
            QApplication.processEvents()
            download_model(model_size)
            self.status_label.setText("Whisper model downloaded")
            log_event(f"downloaded whisper model size={model_size}")
        except Exception as exc:
            log_event(f"model download failed: {repr(exc)}")
            log_event(traceback.format_exc())
            self._show_error(f"Could not download the Whisper model. Original error: {exc}")

    def _finish_push_to_talk(self, raw_text: str, cleaned_text: str) -> None:
        self.push_to_talk_state = "done"
        self.set_app_status("idle")
        
        # Set text in window
        self.raw_text.setPlainText(raw_text)
        self.cleaned_text.setPlainText(cleaned_text)
        
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
            self.set_app_status("idle")

    def _set_overlay_state(self, state: str) -> None:
        if self._settings_from_ui().overlay_enabled:
            self.overlay.set_state(state)
        else:
            self.overlay.hide()

    @Slot(str)
    def _push_to_talk_error(self, message: str) -> None:
        self.push_to_talk_state = "error"
        self.set_app_status("error", f"PTT error: {message}")
        self._show_error(f"Global push-to-talk failed: {message}")
