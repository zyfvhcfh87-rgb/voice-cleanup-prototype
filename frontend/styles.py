from PySide6.QtCore import Qt, QPoint, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QAbstractButton,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
    QCheckBox,
    QFrame,
)

# Minimal macOS-inspired Light Theme (Google Stitch UI Design)
QSS_STYLING = """
/* Main Window Backplate */
QMainWindow {
    background-color: #F5F5F7;
}

QWidget#CentralWidget {
    background-color: #F5F5F7;
    border: 1px solid #E5E5E7;
    border-radius: 16px;
}

/* White Cards with soft borders */
.GlassCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E5E7;
    border-radius: 12px;
}

/* General Typography */
QLabel {
    color: #1D1D1F;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
}

.CardHeader {
    font-size: 14px;
    font-weight: 700;
    color: #1D1D1F;
}

.CardSubHeader {
    font-size: 11px;
    color: #6E6E73;
}

/* Clean Form inputs */
QComboBox, QLineEdit, QPlainTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #E5E5E7;
    border-radius: 8px;
    padding: 6px 10px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
    color: #1D1D1F;
}

QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover {
    border-color: #C5C5C7;
}

QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus {
    border-color: #007AFF;
    background-color: #FFFFFF;
}

/* Dropdown Arrow customization */
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
    border: 1px solid #E5E5E7;
    border-radius: 8px;
    selection-background-color: #F2F2F7;
    selection-color: #1D1D1F;
    padding: 4px;
}

/* Bottom utility buttons & settings buttons */
QPushButton {
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 8px;
    border: 1px solid #E5E5E7;
    background-color: #FFFFFF;
    color: #1D1D1F;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #F5F5F7;
    border-color: #DADCE0;
}

QPushButton:pressed {
    background-color: #E5E5E7;
}

QPushButton:disabled {
    background-color: #F5F5F7;
    color: #8E8E93;
    border-color: #E5E5E7;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #F5F5F7;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #C5C5C7;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #A1A1A5;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


class GlassCard(QWidget):
    """
    A minimal card container styled with a white background, rounded corners,
    and an extremely soft shadow.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Soft premium drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 10))  # Ultra soft shadow
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)


class WaveformLogo(QWidget):
    """
    Custom widget that draws a clean gray waveform logo.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Waveform bars
        heights = [8, 14, 18, 12, 6]
        width = 2.5
        spacing = 2.0
        start_x = (self.width() - (len(heights) * width + (len(heights) - 1) * spacing)) / 2.0
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#8E8E93"))) # Neutral gray
        
        for i, h in enumerate(heights):
            x = start_x + i * (width + spacing)
            y = (self.height() - h) / 2.0
            painter.drawRoundedRect(QRectF(x, y, width, h), width/2.0, width/2.0)


class StatusPill(QWidget):
    """
    Pill widget shown in the top-right header, displaying status dot and label.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 26)
        self.status_state = "idle"
        self.status_text = "Ready"

    def set_status(self, state: str):
        self.status_state = state
        if state == "idle":
            self.status_text = "Ready"
        elif state == "recording":
            self.status_text = "Listening"
        elif state == "processing":
            self.status_text = "Processing"
        elif state == "error":
            self.status_text = "Error"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background pill shape
        painter.setPen(QPen(QColor("#E5E5E7"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 12, 12)

        # Status dot color
        if self.status_state == "idle":
            dot_color = QColor("#34C759")      # Green
        elif self.status_state == "recording":
            dot_color = QColor("#34C759")      # Green for active mic
        elif self.status_state == "processing":
            dot_color = QColor("#007AFF")      # Blue
        elif self.status_state == "error":
            dot_color = QColor("#FF3B30")      # Red
        else:
            dot_color = QColor("#8E8E93")

        # Draw status dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(QPointF(14.0, self.height() / 2.0), 3.5, 3.5)

        # Draw status text
        painter.setPen(QColor("#1D1D1F"))
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(22, 0, self.width() - 28, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.status_text
        )


class SegmentedControl(QWidget):
    """
    Custom Segmented Control (macOS styled) with zero gaps and raised white pill indicator.
    """
    valueChanged = Signal(str)

    def __init__(self, items: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.items = items
        self.selected_value = items[0][1]
        self.setFixedHeight(42)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.setObjectName("SegmentedControl")
        self.setStyleSheet("""
            QWidget#SegmentedControl {
                background-color: #E3E3E8;
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)  # Connected segments
        
        self.buttons = []
        for label, val in items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._make_selector(val))
            layout.addWidget(btn, 1)  # Equal stretch factor
            self.buttons.append((btn, val))
            
        self.set_value(self.selected_value)

    def _make_selector(self, val):
        return lambda: self.set_value(val, emit=True)

    def set_value(self, val, emit=False):
        self.selected_value = val
        for btn, btn_val in self.buttons:
            if btn_val == val:
                btn.setChecked(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #1D1D1F;
                        border: 0.5px solid rgba(0, 0, 0, 0.08);
                        border-radius: 6px;
                        font-weight: 600;
                        padding: 4px 10px;
                        min-height: 32px;
                    }
                """)
                # Dynamic soft shadow on selection
                shadow = QGraphicsDropShadowEffect(btn)
                shadow.setBlurRadius(3)
                shadow.setColor(QColor(0, 0, 0, 20))
                shadow.setOffset(0, 1)
                btn.setGraphicsEffect(shadow)
            else:
                btn.setChecked(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #6E6E73;
                        border: none;
                        border-radius: 6px;
                        font-weight: 500;
                        padding: 4px 10px;
                        min-height: 32px;
                    }
                    QPushButton:hover {
                        color: #1D1D1F;
                    }
                """)
                btn.setGraphicsEffect(None)
        if emit:
            self.valueChanged.emit(val)

    def currentData(self):
        return self.selected_value


class SwitchToggle(QCheckBox):
    """
    Custom widget that implements a gorgeous native macOS-style toggle switch.
    """
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QCheckBox {
                spacing: 10px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
                color: #1D1D1F;
            }
            QCheckBox::indicator {
                width: 0px;
                height: 0px;
            }
        """)
        self.setMinimumHeight(24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track parameters
        track_w = 34.0
        track_h = 20.0
        track_x = 2.0
        track_y = (self.height() - track_h) / 2.0
        
        checked = self.isChecked()
        track_color = QColor("#34C759") if checked else QColor("#D1D1D6")
        
        # Draw track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(QRectF(track_x, track_y, track_w, track_h), 10.0, 10.0)

        # Draw thumb
        thumb_d = 16.0
        thumb_y = track_y + 2.0
        if checked:
            thumb_x = track_x + track_w - thumb_d - 2.0
        else:
            thumb_x = track_x + 2.0
            
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Thumb drop shadow
        shadow_color = QColor(0, 0, 0, 35)
        painter.setBrush(QBrush(shadow_color))
        painter.drawEllipse(QRectF(thumb_x, thumb_y + 0.5, thumb_d, thumb_d))
        
        # Real white thumb circle
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QRectF(thumb_x, thumb_y, thumb_d, thumb_d))

        # Text label
        if self.text():
            painter.setPen(QColor("#1D1D1F"))
            font = self.font()
            font.setFamily("Segoe UI")
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(
                QRectF(track_x + track_w + 10.0, 0, self.width() - track_w - 15.0, self.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self.text()
            )


class TrafficLightButton(QAbstractButton):
    """
    Tiny custom-painted macOS traffic-light control.

    It deliberately avoids QPushButton styling so the app-wide button padding
    cannot stretch the circles into vertical bars.
    """
    def __init__(self, base_color: str, hover_color: str, pressed_color: str, symbol: str, parent=None):
        super().__init__(parent)
        self.base_color = QColor(base_color)
        self.hover_color = QColor(hover_color)
        self.pressed_color = QColor(pressed_color)
        self.symbol = symbol
        self.setFixedSize(14, 14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Close" if symbol == "x" else "Minimize")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self.base_color
        if self.isDown():
            color = self.pressed_color
        elif self.underMouse():
            color = self.hover_color

        painter.setPen(QPen(QColor(0, 0, 0, 35), 0.7))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QRectF(1, 1, 12, 12))

        if self.underMouse() or self.isDown():
            symbol_pen = QPen(QColor(80, 40, 35, 160), 1.4)
            symbol_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(symbol_pen)
            if self.symbol == "x":
                painter.drawLine(QPointF(5.0, 5.0), QPointF(9.0, 9.0))
                painter.drawLine(QPointF(9.0, 5.0), QPointF(5.0, 9.0))
            else:
                painter.drawLine(QPointF(4.5, 7.0), QPointF(9.5, 7.0))


class TitleBar(QWidget):
    """
    macOS Utility inspired TitleBar featuring Traffic Light window controls
    on the left, centered Waveform logo + App Name, and status pill on the right.
    Has a clean subtle bottom border.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(54)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 0, 16, 0)
        content_layout.setSpacing(12)
        
        # 1. macOS Traffic Lights (Close, Minimize)
        self.traffic_lights = QWidget()
        lights_layout = QHBoxLayout(self.traffic_lights)
        lights_layout.setContentsMargins(0, 0, 0, 0)
        lights_layout.setSpacing(8)
        
        self.close_btn = TrafficLightButton("#FF5F57", "#E0443E", "#BF3630", "x")
        self.close_btn.clicked.connect(self.parent.close)
        lights_layout.addWidget(self.close_btn)
        
        self.min_btn = TrafficLightButton("#FFBD2E", "#E0A526", "#B8861F", "-")
        self.min_btn.clicked.connect(self.parent.showMinimized)
        lights_layout.addWidget(self.min_btn)
        
        content_layout.addWidget(self.traffic_lights)
        
        # Spacer before logo/title
        content_layout.addSpacing(6)
        
        # 2. Waveform Logo and App Name
        self.logo = WaveformLogo()
        self.title_label = QLabel("Voice Cleanup")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #1D1D1F;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
        """)
        
        content_layout.addWidget(self.logo)
        content_layout.addWidget(self.title_label)
        
        content_layout.addStretch()
        
        # 3. Status Pill on the right
        self.status_pill = StatusPill()
        content_layout.addWidget(self.status_pill)
        
        self.main_layout.addWidget(content_widget, 1)
        
        # 4. Subtle 1px Bottom Border Line
        self.bottom_line = QFrame(self)
        self.bottom_line.setFrameShape(QFrame.Shape.HLine)
        self.bottom_line.setFrameShadow(QFrame.Shadow.Plain)
        self.bottom_line.setLineWidth(1)
        self.bottom_line.setFixedHeight(1)
        self.bottom_line.setStyleSheet("color: #E5E5E7; background-color: #E5E5E7; border: none;")
        self.main_layout.addWidget(self.bottom_line)
        
        self.drag_position = QPoint()

    def set_status(self, state: str):
        self.status_pill.set_status(state)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.parent.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
