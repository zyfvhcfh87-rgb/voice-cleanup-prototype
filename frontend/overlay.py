from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Slot, QPoint, QRectF
from PySide6.QtGui import QGuiApplication, QPainter, QColor, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget


class MicrophoneOverlay(QWidget):
    """
    A premium floating desktop widget shaped as a glassmorphic circle.
    Fades in/out smoothly and features beautiful custom-drawn glowing pulse animations
    representing different stages of AI recording, processing, and status.
    """
    COLORS = {
        "idle": QColor(180, 160, 180, 180),
        "recording": QColor(67, 214, 109),    # Green #43D66D
        "processing": QColor(255, 200, 87),   # Yellow #FFC857
        "done": QColor(124, 235, 255),        # Cyan #7CEBFF
        "error": QColor(255, 90, 90),         # Red #FF5A5A
    }

    def __init__(self) -> None:
        super().__init__()
        
        # Transparent, always-on-top window setup
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(90, 90)  # Spaced nicely for pulse expansion

        self.current_state = "idle"
        self.pulse_phase = 0.0
        self.fade_animation = None

        # 60 FPS animation timer for smooth glow pulsing
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(16)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_timer.start()

    def set_state(self, state: str) -> None:
        """
        Transition between UI states smoothly with fade animations.
        """
        if state == self.current_state:
            return

        old_state = self.current_state
        self.current_state = state
        self._move_to_bottom_right()

        # Stop existing fade animation if running
        if self.fade_animation and self.fade_animation.state() == QPropertyAnimation.State.Running:
            self.fade_animation.stop()

        # Smooth Fade-In when leaving idle
        if old_state == "idle" and state != "idle":
            self.setWindowOpacity(0.0)
            self.show()
            self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_animation.setDuration(200)
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()

        # Smooth Fade-Out when returning to idle
        elif state == "idle":
            self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_animation.setDuration(350)
            self.fade_animation.setStartValue(self.windowOpacity())
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.finished.connect(self._hide_widget)
            self.fade_animation.start()
        
        else:
            self.show()
            self.setWindowOpacity(1.0)

    @Slot()
    def _hide_widget(self) -> None:
        if self.current_state == "idle":
            self.hide()

    @Slot()
    def _update_pulse(self) -> None:
        # Update animation phase (higher speed when processing, slower when recording)
        speed = 0.035 if self.current_state == "processing" else 0.02
        self.pulse_phase += speed
        if self.pulse_phase > 1.0:
            self.pulse_phase = 0.0
        
        # Trigger repaint
        if self.isVisible():
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center point and parameters
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        
        # Main glass sphere size
        glass_radius = 28.0  # 56px diameter

        state_color = self.COLORS.get(self.current_state, self.COLORS["idle"])

        # 1. DRAW OUTER GLOWING PULSE RING (only when active)
        if self.current_state in ("recording", "processing", "error", "done"):
            # Radius increases from glass_radius to width/2
            pulse_radius = glass_radius + self.pulse_phase * (self.width() / 2.0 - glass_radius)
            # Opacity fades as pulse grows
            alpha = int(180 * (1.0 - self.pulse_phase))
            
            pulse_color = QColor(state_color.red(), state_color.green(), state_color.blue(), alpha)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(pulse_color))
            painter.drawEllipse(QPoint(center_x, center_y), pulse_radius, pulse_radius)

            # Draw a secondary inner faint pulse for high-fidelity aesthetics
            if self.pulse_phase > 0.4:
                second_phase = self.pulse_phase - 0.4
                second_radius = glass_radius + second_phase * (self.width() / 2.0 - glass_radius)
                second_alpha = int(140 * (1.0 - second_phase))
                second_color = QColor(state_color.red(), state_color.green(), state_color.blue(), second_alpha)
                painter.drawEllipse(QPoint(center_x, center_y), second_radius, second_radius)

        # 2. DRAW SHADOW UNDER GLASSMORPHIC BEAD
        shadow_color = QColor(0, 0, 0, 30)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawEllipse(QPoint(center_x, center_y + 3), glass_radius, glass_radius)

        # 3. DRAW GLASSMORPHIC MAIN CIRCLE
        # Subtle white glass linear gradient
        glass_gradient = QColor(255, 255, 255, 210)  # Front face
        glass_back = QColor(245, 242, 245, 140)    # Soft purple background
        
        # Glass fill
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glass_gradient))
        painter.drawEllipse(QPoint(center_x, center_y), glass_radius, glass_radius)
        
        # Micro-border: crisp translucent white edge reflection
        border_pen = QPen(QColor(255, 255, 255, 160))
        border_pen.setWidthF(1.2)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPoint(center_x, center_y), glass_radius, glass_radius)

        # 4. DRAW SLEEK MIC VECTOR ICON IN CENTER
        mic_color = state_color
        # For idle, draw the branding gradient mic for an ultra-premium wow factor!
        if self.current_state == "idle":
            mic_color = QColor(217, 143, 255) # Light purple accent

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(mic_color))

        # A. Capsule (rounded rect)
        capsule_width = 8.0
        capsule_height = 16.0
        capsule_x = center_x - capsule_width / 2.0
        capsule_y = center_y - capsule_height / 2.0 - 2.0
        painter.drawRoundedRect(QRectF(capsule_x, capsule_y, capsule_width, capsule_height), 4.0, 4.0)

        # B. Stand Cup (Crescent U-shape)
        cup_pen = QPen(mic_color)
        cup_pen.setWidthF(2.0)
        cup_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(cup_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cup_width = 14.0
        cup_height = 10.0
        cup_x = center_x - cup_width / 2.0
        cup_y = capsule_y + capsule_height - cup_height + 3.0
        painter.drawArc(QRectF(cup_x, cup_y, cup_width, cup_height), 180 * 16, 180 * 16)

        # C. Stem and Base
        painter.drawLine(QPoint(center_x, cup_y + cup_height), QPoint(center_x, cup_y + cup_height + 5.0))
        painter.drawLine(QPoint(center_x - 5.0, cup_y + cup_height + 5.0), QPoint(center_x + 5.0, cup_y + cup_height + 5.0))

    def _move_to_bottom_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        margin = 28
        self.move(area.right() - self.width() - margin, area.bottom() - self.height() - margin)
