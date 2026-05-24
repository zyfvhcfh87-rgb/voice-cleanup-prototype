from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect

# Brand Identity QSS Stylesheet
QSS_STYLING = """
/* Custom QSS Theme */
QMainWindow {
    background-color: #F9F6F8;
}

QWidget#CentralWidget {
    background-color: #F9F6F8;
}

/* GlassCard Container */
.GlassCard {
    background-color: rgba(255, 255, 255, 0.68);
    border: 1px solid rgba(255, 255, 255, 0.5);
    border-radius: 16px;
}

/* Input Card Labels */
QLabel {
    color: #222222;
    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    font-size: 13px;
}

.CardHeader {
    font-size: 14px;
    font-weight: 700;
    color: #222222;
}

.CardSubHeader {
    font-size: 11px;
    color: #666666;
}

/* Main Buttons (Pill shape) */
QPushButton {
    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 18px;
    border: none;
    min-height: 36px;
}

QPushButton:disabled {
    background-color: #E2DFE2;
    color: #9A979A;
}

/* Start Recording button (Green gradient) */
QPushButton#StartBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #43D66D, stop:1 #2DBE5C);
    color: white;
}
QPushButton#StartBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #52E27B, stop:1 #3CCF6C);
}
QPushButton#StartBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #33C65D, stop:1 #1DAE4C);
}

/* Stop Recording button (Soft red) */
QPushButton#StopBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF5A5A, stop:1 #E04848);
    color: white;
}
QPushButton#StopBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF6C6C, stop:1 #F05858);
}
QPushButton#StopBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EF4A4A, stop:1 #D03838);
}

/* Save Settings button (Purple/pink gradient) */
QPushButton#SaveBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF8FD8, stop:1 #D98FFF);
    color: white;
}
QPushButton#SaveBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFA3E2, stop:1 #E5A3FF);
}
QPushButton#SaveBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7FC8, stop:1 #C97FFF);
}

/* Copy Cleaned Text button (Cyan accent) */
QPushButton#CopyBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7CEBFF, stop:1 #52D8F0);
    color: #1A2E35;
}
QPushButton#CopyBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #92F0FF, stop:1 #67E1F5);
}
QPushButton#CopyBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6CDDEE, stop:1 #42C2D8);
}

/* Path actions (Browse / Refresh) */
QPushButton#BrowseBtn, QPushButton#RefreshBtn {
    background-color: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(220, 210, 220, 0.6);
    border-radius: 14px;
    padding: 4px 12px;
    min-height: 28px;
    font-size: 11px;
    color: #444444;
}
QPushButton#BrowseBtn:hover, QPushButton#RefreshBtn:hover {
    background-color: #FFFFFF;
    border-color: #D98FFF;
    color: #111111;
}
QPushButton#BrowseBtn:pressed, QPushButton#RefreshBtn:pressed {
    background-color: #F2EFF2;
    border-color: #C97FFF;
}

/* Interactive inputs */
QComboBox, QLineEdit, QPlainTextEdit {
    background-color: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(210, 200, 210, 0.55);
    border-radius: 10px;
    padding: 8px 12px;
    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    font-size: 13px;
    color: #222222;
}

QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover {
    border: 1px solid rgba(217, 143, 255, 0.5);
    background-color: rgba(255, 255, 255, 0.82);
}

QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus {
    border: 1.5px solid #D98FFF;
    background-color: #FFFFFF;
}

/* Text Editors styling */
QPlainTextEdit#RawText {
    background-color: rgba(244, 241, 244, 0.75);
    border: 1px solid rgba(220, 215, 220, 0.6);
}

QPlainTextEdit#CleanText {
    background-color: rgba(255, 255, 255, 0.88);
    border: 1.5px solid rgba(124, 235, 255, 0.65); /* Highlight cyan border */
}

/* Custom Dropdown spacing */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: none;
}

QComboBox::down-arrow {
    image: none;
    border: none;
    width: 0;
    height: 0;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid rgba(217, 143, 255, 0.4);
    border-radius: 8px;
    selection-background-color: #F6EDFC;
    selection-color: #222222;
    padding: 4px;
}

/* QCheckBox customizing */
QCheckBox {
    spacing: 8px;
    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    font-size: 13px;
    color: #333333;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid rgba(210, 200, 210, 0.7);
    background-color: rgba(255, 255, 255, 0.85);
}

QCheckBox::indicator:hover {
    border-color: #D98FFF;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    border-color: #D98FFF;
    background-color: #D98FFF;
}

/* Status Label custom text */
QLabel#StatusLabel {
    color: #666666;
    font-weight: 500;
    font-size: 12px;
}
"""

class GlassCard(QWidget):
    """
    A elegant container widget designed to have translucent glass-like appearance
    and a subtle modern shadow effect.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#GlassCard {
                background-color: rgba(255, 255, 255, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
            }
        """)
        
        # Soft premium drop shadow (extremely low performance cost)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(180, 160, 185, 30))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)


class TitleBar(QWidget):
    """
    A custom Title Bar widget providing frameless window dragging controls
    and styled minimize/close actions.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(44)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(18, 0, 18, 0)
        self.layout.setSpacing(10)
        
        # Rounded Glowing Gradient Bubble Logo
        self.logo_label = QWidget()
        self.logo_label.setFixedSize(14, 14)
        self.logo_label.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF8FD8, stop:0.5 #D98FFF, stop:1 #7CEBFF);
                border-radius: 7px;
            }
        """)
        
        # App Title Text
        self.title_label = QLabel("Voice Cleanup AI")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #222222;
                font-size: 12px;
                font-weight: 700;
                font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
                letter-spacing: 0.5px;
            }
        """)
        
        self.layout.addWidget(self.logo_label)
        self.layout.addWidget(self.title_label)
        self.layout.addStretch()
        
        # Minimize Action Button (soft gray-lavender circle)
        self.min_btn = QPushButton()
        self.min_btn.setFixedSize(13, 13)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setStyleSheet("""
            QPushButton {
                background: #E4DFE3;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #CDC6CC;
            }
        """)
        self.min_btn.clicked.connect(self.parent.showMinimized)
        
        # Close Action Button (soft red circle)
        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(13, 13)
        self.close_btn.setToolTip("Close")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #FF5A5A;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #E84545;
            }
        """)
        self.close_btn.clicked.connect(self.parent.close)
        
        self.layout.addWidget(self.min_btn)
        self.layout.addWidget(self.close_btn)
        
        self.drag_position = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.parent.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
