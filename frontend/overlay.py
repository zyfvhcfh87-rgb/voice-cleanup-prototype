from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QGuiApplication, QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget


class MicrophoneOverlay(QWidget):
    """
    A minimal, macOS-inspired floating desktop widget.
    Displays a circular microphone button with beautiful custom state animations
    and a clean pill-shaped label below it.
    """
    COLORS = {
        "idle": QColor("#8E8E93"),          # Disabled/Idle gray
        "recording": QColor("#34C759"),     # Success/Ready green
        "processing": QColor("#007AFF"),    # Accent/Processing blue
        "stopping": QColor("#007AFF"),
        "transcribing": QColor("#007AFF"),
        "cleaning": QColor("#007AFF"),
        "inserting": QColor("#007AFF"),
        "error": QColor("#FF3B30"),         # Error red
        "done": QColor("#34C759"),          # Handled same as idle/success
    }

    def __init__(self) -> None:
        super().__init__()
        
        # Transparent, always-on-top, frameless window
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Expanded to fit circle + label comfortably
        self.setFixedSize(120, 120)

        self.current_state = "idle"
        self.pulse_phase = 0.0
        
        # 60 FPS animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start()

    def set_state(self, state: str) -> None:
        """
        Transition between overlay states such as idle, recording,
        processing, transcribing, cleaning, inserting, error, and done.
        """
        if state == "done":
            state = "idle"
            
        self.current_state = state
        self._move_to_bottom_right()
        
        # Ensure it is shown if overlay is enabled
        self.show()
        self.update()

    def _update_animation(self) -> None:
        if self.current_state in ("processing", "stopping", "transcribing", "cleaning", "inserting"):
            self.pulse_phase += 0.04  # Rotate progress arc
        elif self.current_state == "recording":
            self.pulse_phase += 0.02  # Outer glow pulse
        else:
            self.pulse_phase += 0.01
            
        if self.pulse_phase > 1.0:
            self.pulse_phase = 0.0
            
        if self.isVisible():
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center point and parameters
        center_x = self.width() / 2.0
        center_y = 44.0  # Vertically centered in the top half
        
        # Main circle radius (48px diameter)
        radius = 24.0

        state_color = self.COLORS.get(self.current_state, self.COLORS["idle"])

        # 1. DRAW OUTER GLOWS/PULSES
        if self.current_state == "recording":
            # Pulsing outer green ring
            pulse_r = radius + (self.pulse_phase * 12.0)
            alpha = int(120 * (1.0 - self.pulse_phase))
            glow_color = QColor(state_color.red(), state_color.green(), state_color.blue(), alpha)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(QPointF(center_x, center_y), pulse_r, pulse_r)
            
        elif self.current_state in ("processing", "stopping", "transcribing", "cleaning", "inserting"):
            # Spinning blue progress ring around the circle
            ring_pen = QPen(state_color)
            ring_pen.setWidthF(3.0)
            ring_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            angle = int(self.pulse_phase * 360.0 * 16.0)
            span_angle = int(90.0 * 16.0)
            rect = QRectF(center_x - radius - 4, center_y - radius - 4, (radius + 4) * 2, (radius + 4) * 2)
            painter.drawArc(rect, angle, span_angle)
            
        elif self.current_state == "error":
            # Soft red outer halo
            glow_color = QColor(state_color.red(), state_color.green(), state_color.blue(), 50)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(QPointF(center_x, center_y), radius + 6.0, radius + 6.0)

        # 2. DRAW MAIN BUTTON CIRCLE WITH SOFT SHADOW
        # Soft shadow
        shadow_color = QColor(0, 0, 0, 35)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawEllipse(QPointF(center_x, center_y + 2), radius, radius)

        # Main circle fill
        if self.current_state == "idle":
            # Soft silver-gray background matching macOS
            circle_color = QColor("#E5E5E7")
        else:
            circle_color = state_color

        painter.setBrush(QBrush(circle_color))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # Subtle white/gray border
        border_pen = QPen(QColor(255, 255, 255, 100) if self.current_state != "idle" else QColor("#DADCE0"))
        border_pen.setWidthF(1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # 3. DRAW MIC ICON
        mic_color = QColor("#FFFFFF") if self.current_state != "idle" else QColor("#6E6E73")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(mic_color))

        # A. Capsule (rounded rect)
        cap_w = 6.0
        cap_h = 13.0
        cap_x = center_x - cap_w / 2.0
        cap_y = center_y - cap_h / 2.0 - 2.0
        painter.drawRoundedRect(QRectF(cap_x, cap_y, cap_w, cap_h), 3.0, 3.0)

        # B. Stand Cup (Crescent U-shape)
        cup_pen = QPen(mic_color)
        cup_pen.setWidthF(1.8)
        cup_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(cup_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cup_w = 11.0
        cup_h = 8.0
        cup_x = center_x - cup_w / 2.0
        cup_y = cap_y + cap_h - cup_h + 2.0
        painter.drawArc(QRectF(cup_x, cup_y, cup_w, cup_h), 180 * 16, 180 * 16)

        # C. Stem and Base
        painter.drawLine(QPointF(center_x, cup_y + cup_h), QPointF(center_x, cup_y + cup_h + 4.0))
        painter.drawLine(QPointF(center_x - 4.0, cup_y + cup_h + 4.0), QPointF(center_x + 4.0, cup_y + cup_h + 4.0))

        # D. If error state, draw a diagonal slash across the mic icon
        if self.current_state == "error":
            slash_pen = QPen(QColor("#FFFFFF"))
            slash_pen.setWidthF(2.0)
            slash_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(slash_pen)
            # Diagonal line from top-left of mic area to bottom-right
            painter.drawLine(QPointF(center_x - 6.0, center_y - 8.0), QPointF(center_x + 6.0, center_y + 6.0))

        # 4. DRAW CAPSULE LABEL BELOW CIRCLE
        label_text = "Idle"
        if self.current_state == "recording":
            label_text = "Listening"
        elif self.current_state == "stopping":
            label_text = "Stopping"
        elif self.current_state == "transcribing":
            label_text = "Transcribing"
        elif self.current_state == "processing":
            label_text = "Processing"
        elif self.current_state == "cleaning":
            label_text = "Cleaning"
        elif self.current_state == "inserting":
            label_text = "Inserting"
        elif self.current_state == "error":
            label_text = "Error"

        # Capsule dimensions
        lbl_w = max(72.0, len(label_text) * 7.0 + 18.0)
        lbl_h = 18.0
        lbl_x = center_x - lbl_w / 2.0
        lbl_y = 80.0  # Spaced nicely below the circle

        # Draw dark capsule background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 140)))  # Semi-transparent dark pill
        painter.drawRoundedRect(QRectF(lbl_x, lbl_y, lbl_w, lbl_h), 9.0, 9.0)

        # Draw text inside capsule
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(lbl_x, lbl_y, lbl_w, lbl_h), Qt.AlignmentFlag.AlignCenter, label_text)

    def _move_to_bottom_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        margin = 32
        self.move(area.right() - self.width() - margin, area.bottom() - self.height() - margin)
