from dataclasses import asdict

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config.settings import AppSettings, WHISPER_MODELS_DIR, get_whisper_model_path


class PreferencesDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.setModal(True)
        self.resize(560, 560)
        self.settings = AppSettings(**asdict(settings))
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header = QLabel("Advanced Settings")
        header.setStyleSheet("font-size: 22px; font-weight: 700; color: #1D1D1F;")
        root.addWidget(header)

        subheader = QLabel("Local engine paths, shortcut behavior, and optional AI cleanup settings.")
        subheader.setStyleSheet("color: #6E6E73; font-size: 13px;")
        root.addWidget(subheader)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        root.addWidget(scroll, 1)

        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 4, 4, 4)
        layout.setSpacing(14)

        overlay_row = QHBoxLayout()
        overlay_row.addWidget(self._label("Desktop Overlay"))
        self.overlay_visibility_combo = QComboBox()
        self.overlay_visibility_combo.addItem("Always show", "always")
        self.overlay_visibility_combo.addItem("Only while active", "active")
        self.overlay_visibility_combo.addItem("Never show", "never")
        overlay_row.addWidget(self.overlay_visibility_combo, 1)
        layout.addLayout(overlay_row)

        shortcut_row = QHBoxLayout()
        shortcut_row.addWidget(self._label("Push-to-Talk Shortcut"))
        self.hotkey_choice_combo = QComboBox()
        self.hotkey_choice_combo.addItem("Ctrl + Windows", "ctrl_win")
        self.hotkey_choice_combo.addItem("Ctrl + Alt", "ctrl_alt")
        self.hotkey_choice_combo.addItem("Ctrl + Shift + Space", "ctrl_shift_space")
        shortcut_row.addWidget(self.hotkey_choice_combo, 1)
        layout.addLayout(shortcut_row)

        exe_row = QHBoxLayout()
        exe_row.addWidget(self._label("Speech Engine"))
        self.whisper_exe_edit = QLineEdit()
        self.whisper_exe_edit.setPlaceholderText("Path to whisper-cli.exe")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._choose_whisper_exe)
        exe_row.addWidget(self.whisper_exe_edit, 1)
        exe_row.addWidget(browse_button)
        layout.addLayout(exe_row)

        model_row = QHBoxLayout()
        model_row.addWidget(self._label("Model File"))
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setReadOnly(True)
        folder_button = QPushButton("Folder")
        folder_button.clicked.connect(self._open_models_folder)
        model_row.addWidget(self.model_path_edit, 1)
        model_row.addWidget(folder_button)
        layout.addLayout(model_row)

        cleanup_row = QHBoxLayout()
        cleanup_row.addWidget(self._label("Cleanup Style"))
        self.cleanup_backend_combo = QComboBox()
        self.cleanup_backend_combo.addItem("None", "none")
        self.cleanup_backend_combo.addItem("Smart Cleanup", "asr_postprocess")
        self.cleanup_backend_combo.addItem("AI Rewrite Cleanup", "ollama_llm")
        cleanup_row.addWidget(self.cleanup_backend_combo, 1)
        layout.addLayout(cleanup_row)

        ollama_url_row = QHBoxLayout()
        ollama_url_row.addWidget(self._label("AI Server URL"))
        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ollama_url_row.addWidget(self.ollama_url_edit, 1)
        layout.addLayout(ollama_url_row)

        ollama_model_row = QHBoxLayout()
        ollama_model_row.addWidget(self._label("AI Model"))
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setEditable(True)
        self.ollama_model_combo.addItems(["qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:3b"])
        ollama_model_row.addWidget(self.ollama_model_combo, 1)
        layout.addLayout(ollama_model_row)

        prompt_label = QLabel("Smart Cleanup Advanced Instructions")
        prompt_label.setStyleSheet("font-weight: 700; color: #1D1D1F;")
        layout.addWidget(prompt_label)

        self.cleanup_prompt_edit = QPlainTextEdit()
        self.cleanup_prompt_edit.setMinimumHeight(120)
        self.cleanup_prompt_edit.setPlaceholderText("Advanced cleanup instructions...")
        layout.addWidget(self.cleanup_prompt_edit)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_and_accept)
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)
        root.addLayout(button_row)

        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
            }
            QLabel {
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: #1D1D1F;
            }
            QComboBox, QLineEdit, QPlainTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E7;
                border-radius: 8px;
                padding: 6px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: #1D1D1F;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E7;
                border-radius: 8px;
                padding: 7px 16px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: #1D1D1F;
            }
            QPushButton:hover {
                background-color: #F2F2F7;
            }
        """)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFixedWidth(145)
        label.setStyleSheet("color: #6E6E73;")
        return label

    def _load_settings(self) -> None:
        overlay_index = self.overlay_visibility_combo.findData(self.settings.overlay_visibility_mode)
        self.overlay_visibility_combo.setCurrentIndex(overlay_index if overlay_index >= 0 else 1)
        index = self.hotkey_choice_combo.findData(self.settings.hotkey_choice)
        self.hotkey_choice_combo.setCurrentIndex(index if index >= 0 else 0)

        self.whisper_exe_edit.setText(self.settings.whisper_exe_path)
        self.model_path_edit.setText(str(get_whisper_model_path(self.settings.model_size)))

        cleanup_index = self.cleanup_backend_combo.findData(self.settings.cleanup_backend)
        self.cleanup_backend_combo.setCurrentIndex(cleanup_index if cleanup_index >= 0 else 1)

        self.ollama_url_edit.setText(self.settings.ollama_url)
        ollama_model_index = self.ollama_model_combo.findText(self.settings.ollama_model)
        if ollama_model_index >= 0:
            self.ollama_model_combo.setCurrentIndex(ollama_model_index)
        else:
            self.ollama_model_combo.setEditText(self.settings.ollama_model)
        self.cleanup_prompt_edit.setPlainText(self.settings.cleanup_prompt)

    def _choose_whisper_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose Speech Engine", "", "Executable (*.exe);;All files (*)")
        if path:
            self.whisper_exe_edit.setText(path)

    def _open_models_folder(self) -> None:
        WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(WHISPER_MODELS_DIR)))

    def _save_and_accept(self) -> None:
        self.settings.overlay_visibility_mode = self.overlay_visibility_combo.currentData()
        self.settings.hotkey_choice = self.hotkey_choice_combo.currentData()
        self.settings.whisper_exe_path = self.whisper_exe_edit.text().strip()
        self.settings.model_path = str(get_whisper_model_path(self.settings.model_size))
        self.settings.cleanup_backend = self.cleanup_backend_combo.currentData()
        self.settings.ollama_url = self.ollama_url_edit.text().strip() or "http://localhost:11434"
        self.settings.ollama_model = self.ollama_model_combo.currentText().strip() or "qwen2.5:1.5b"
        self.settings.cleanup_prompt = self.cleanup_prompt_edit.toPlainText().strip()
        self.accept()
