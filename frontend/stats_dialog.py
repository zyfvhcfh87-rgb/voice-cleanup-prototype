from PySide6.QtCore import Qt, QPoint, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
    QProgressBar,
)

from config.dictation_stats import (
    load_today_stats,
    get_most_used_mic,
    get_avg_session_length,
)


class CircularRingWidget(QWidget):
    """
    Custom widget that draws a beautiful macOS-style circular ring
    with a big bold number and description text centered inside.
    """
    def __init__(self, number_str: str, label_str: str, parent=None):
        super().__init__(parent)
        self.number_str = number_str
        self.label_str = label_str
        self.setFixedSize(140, 140)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Center coordinates
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = 52.0  # Radius for the ring center line
        
        # 1. Draw outer circle ring background (gray)
        pen = QPen(QColor("#E5E5E7"))
        pen.setWidth(8)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 2. Draw actual dark ring indicator (slightly darker gray, e.g., #A1A1A5)
        indicator_pen = QPen(QColor("#A1A1A5"))
        indicator_pen.setWidth(8)
        indicator_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(indicator_pen)
        painter.drawEllipse(QPointF(cx, cy), r, r)
        
        # 3. Draw big bold number in the center
        painter.setPen(QColor("#1D1D1F"))
        num_font = QFont("Segoe UI", 26)
        num_font.setBold(True)
        painter.setFont(num_font)
        num_rect = QRectF(cx - r, cy - 22, r * 2, 28)
        painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, self.number_str)
        
        # 4. Draw label below the number
        painter.setPen(QColor("#6E6E73"))
        lbl_font = QFont("Segoe UI", 9)
        lbl_font.setBold(False)
        painter.setFont(lbl_font)
        lbl_rect = QRectF(cx - r, cy + 8, r * 2, 16)
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, self.label_str)


class MicIconWidget(QWidget):
    """
    Custom widget to draw a clean macOS-style gray mic icon in a circle.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center and background circle
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = 16.0
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#F5F5F7")))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Draw simple mic icon
        painter.setBrush(QBrush(QColor("#007AFF")))
        
        cap_w = 4.0
        cap_h = 9.0
        cap_x = cx - cap_w / 2.0
        cap_y = cy - cap_h / 2.0 - 1.5
        painter.drawRoundedRect(QRectF(cap_x, cap_y, cap_w, cap_h), 2.0, 2.0)

        # Stand Cup
        cup_pen = QPen(QColor("#007AFF"))
        cup_pen.setWidthF(1.5)
        cup_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(cup_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cup_w = 8.0
        cup_h = 5.0
        cup_x = cx - cup_w / 2.0
        cup_y = cap_y + cap_h - cup_h + 1.5
        painter.drawArc(QRectF(cup_x, cup_y, cup_w, cup_h), 180 * 16, 180 * 16)

        # Stem & Base
        painter.drawLine(QPointF(cx, cup_y + cup_h), QPointF(cx, cup_y + cup_h + 3.0))
        painter.drawLine(QPointF(cx - 3.0, cup_y + cup_h + 3.0), QPointF(cx + 3.0, cup_y + cup_h + 3.0))


class StopwatchIconWidget(QWidget):
    """
    Custom widget to draw a stopwatch icon in a circle.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = 16.0
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#F5F5F7")))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Draw simple stopwatch
        pen = QPen(QColor("#007AFF"))
        pen.setWidthF(1.8)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Stopwatch body
        sw_r = 7.0
        painter.drawEllipse(QPointF(cx, cy + 1.0), sw_r, sw_r)

        # Top button
        painter.setBrush(QBrush(QColor("#007AFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(cx - 1.5, cy - sw_r - 2.5, 3.0, 2.0))
        
        # Side button
        painter.drawEllipse(QPointF(cx + 4.5, cy - 4.5), 1.0, 1.0)

        # Clock hand
        hand_pen = QPen(QColor("#007AFF"))
        hand_pen.setWidthF(1.5)
        painter.setPen(hand_pen)
        painter.drawLine(QPointF(cx, cy + 1.0), QPointF(cx + 3.5, cy - 2.5))


class StatisticsDashboardDialog(QDialog):
    """
    Statistics Dashboard Pop-up Modal window designed to match reference image 2.
    It displays rich local statistics like sessions today, words written, estimated
    time saved, most used microphone (with progress bar), and average session length.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistics Dashboard")
        self.setFixedSize(650, 430)

        # Frameless with transparent background
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.CustomizeWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.drag_position = QPoint()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # Outer layout to support shadow border padding
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)

        # Central white card widget
        self.card = QWidget()
        self.card.setObjectName("StatsCard")
        self.card.setStyleSheet("""
            QWidget#StatsCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E7;
                border-radius: 20px;
            }
        """)

        # Soft blue-tinted glow shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(100, 150, 240, 45))  # Soft blue glow
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        outer_layout.addWidget(self.card)

        # Inner card layout
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # Top Row: Close Button right-aligned
        top_row = QHBoxLayout()
        top_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(60, 26)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F7;
                border: 1px solid #DADCE0;
                border-radius: 6px;
                color: #1D1D1F;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E5E5EA;
            }
            QPushButton:pressed {
                background-color: #D1D1D6;
            }
        """)
        close_btn.clicked.connect(self.accept)
        top_row.addWidget(close_btn)
        layout.addLayout(top_row)

        # Title: Center Centered
        self.title_label = QLabel("Statistics Dashboard")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 26px;
                font-weight: 700;
                color: #1D1D1F;
                margin-top: -10px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(self.title_label)

        # Stats Rings & Time Saved Layout (Horizontal)
        middle_row = QHBoxLayout()
        middle_row.setSpacing(24)
        middle_row.setContentsMargins(10, 0, 10, 0)

        # 1. Sessions Ring
        self.sessions_ring = CircularRingWidget("0", "Sessions Today")
        middle_row.addWidget(self.sessions_ring)

        # 2. Total Words Ring
        self.words_ring = CircularRingWidget("0", "Total Words")
        middle_row.addWidget(self.words_ring)

        # 3. Time Saved layout
        time_saved_layout = QVBoxLayout()
        time_saved_layout.setSpacing(2)
        time_saved_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        lbl_ts_header = QLabel("Time Saved")
        lbl_ts_header.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 600;
                color: #6E6E73;
            }
        """)
        
        self.time_saved_value = QLabel("0 mins")
        self.time_saved_value.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 32px;
                font-weight: 700;
                color: #007AFF;
            }
        """)
        
        lbl_ts_today = QLabel("today")
        lbl_ts_today.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 11px;
                color: #6E6E73;
            }
        """)

        time_saved_layout.addWidget(lbl_ts_header)
        time_saved_layout.addWidget(self.time_saved_value)
        time_saved_layout.addWidget(lbl_ts_today)

        middle_row.addLayout(time_saved_layout)
        middle_row.addStretch()

        layout.addLayout(middle_row)
        layout.addSpacing(6)

        # Bottom Row: Two detailed cards stacked horizontally
        bottom_cards_row = QHBoxLayout()
        bottom_cards_row.setSpacing(16)

        # Card 1: Most Used Mic
        mic_card = QWidget()
        mic_card.setObjectName("MicCard")
        mic_card.setStyleSheet("""
            QWidget#MicCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E7;
                border-radius: 12px;
            }
        """)
        mic_layout = QVBoxLayout(mic_card)
        mic_layout.setContentsMargins(12, 10, 12, 10)
        mic_layout.setSpacing(4)

        lbl_mic_title = QLabel("Most Used Mic")
        lbl_mic_title.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: bold; color: #1D1D1F;")
        mic_layout.addWidget(lbl_mic_title)

        mic_row = QHBoxLayout()
        mic_row.setSpacing(8)
        self.mic_icon = MicIconWidget()
        mic_info = QVBoxLayout()
        mic_info.setSpacing(1)
        self.mic_name_label = QLabel("None")
        self.mic_name_label.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 12px; font-weight: bold; color: #1D1D1F;")
        self.mic_percent_label = QLabel("0% of sessions")
        self.mic_percent_label.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 10px; color: #6E6E73;")
        mic_info.addWidget(self.mic_name_label)
        mic_info.addWidget(self.mic_percent_label)
        mic_row.addWidget(self.mic_icon)
        mic_row.addLayout(mic_info)
        mic_row.addStretch()
        mic_layout.addLayout(mic_row)

        self.mic_progress = QProgressBar()
        self.mic_progress.setFixedHeight(5)
        self.mic_progress.setTextVisible(False)
        self.mic_progress.setStyleSheet("""
            QProgressBar {
                background-color: #E5E5E7;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #8E8E93;
                border-radius: 2px;
            }
        """)
        mic_layout.addWidget(self.mic_progress)
        bottom_cards_row.addWidget(mic_card, 1)

        # Card 2: Avg. Session Length
        len_card = QWidget()
        len_card.setObjectName("LenCard")
        len_card.setStyleSheet("""
            QWidget#LenCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E5E7;
                border-radius: 12px;
            }
        """)
        len_layout = QVBoxLayout(len_card)
        len_layout.setContentsMargins(12, 10, 12, 10)
        len_layout.setSpacing(4)

        lbl_len_title = QLabel("Avg. Session Length")
        lbl_len_title.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: bold; color: #1D1D1F;")
        len_layout.addWidget(lbl_len_title)

        len_row = QHBoxLayout()
        len_row.setSpacing(8)
        self.len_icon = StopwatchIconWidget()
        self.len_value_label = QLabel("0 seconds")
        self.len_value_label.setWordWrap(True)
        self.len_value_label.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 13px; font-weight: bold; color: #1D1D1F;")
        len_row.addWidget(self.len_icon)
        len_row.addWidget(self.len_value_label, 1)
        len_layout.addLayout(len_row)
        len_layout.addStretch()
        bottom_cards_row.addWidget(len_card, 1)

        layout.addLayout(bottom_cards_row)

    def _load_data(self):
        stats = load_today_stats()
        
        # Load sessions ring
        self.sessions_ring.number_str = str(stats.sessions)
        
        # Load words ring
        self.words_ring.number_str = f"{stats.words:,}"
        
        # Load time saved value
        self.time_saved_value.setText(f"{stats.minutes_saved} mins")
        
        # Load most used mic
        mic_name, mic_percent = get_most_used_mic(stats)
        self.mic_name_label.setText(mic_name)
        self.mic_percent_label.setText(f"{round(mic_percent)}% of sessions")
        self.mic_progress.setValue(int(round(mic_percent)))
        
        # Load avg session length
        avg_seconds = get_avg_session_length(stats)
        self.len_value_label.setText(self._format_duration(avg_seconds))

    def _format_duration(self, seconds: float) -> str:
        if seconds <= 0:
            return "0 seconds"
        mins = int(seconds // 60)
        secs = int(round(seconds % 60))
        parts = []
        if mins > 0:
            parts.append(f"{mins} minute{'s' if mins > 1 else ''}")
        if secs > 0 or not parts:
            parts.append(f"{secs} second{'s' if secs > 1 else ''}")
        return " ".join(parts)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
