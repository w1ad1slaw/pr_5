"""
Manometer & Analog Clock Widget
Десктопное приложение с виджетами манометра и аналоговых часов.
"""

import os
import sys

# ── ВАЖНО: указать путь к плагинам Qt ДО импорта PyQt5 ──────────────────────
# Автоматически находим путь к PyQt5 в текущем окружении
try:
    import PyQt5 as _pq5
    _qt_plugins_path = os.path.join(
        os.path.dirname(_pq5.__file__), 'Qt5', 'plugins'
    )
    if os.path.isdir(_qt_plugins_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = _qt_plugins_path
except ImportError:
    pass
# ─────────────────────────────────────────────────────────────────────────────

import math
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QSlider, QGroupBox, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                         QRadialGradient, QPainterPath, QPolygonF)


# ─────────────────────────────────────────────
#  Виджет манометра
# ─────────────────────────────────────────────
class ManometerWidget(QWidget):
    valueChanged = pyqtSignal(float)

    # Цветовые зоны (bar)
    ZONES = [
        (0,  45, QColor("#2ECC40")),   # зелёный — норма
        (45, 75, QColor("#FFDC00")),   # жёлтый — внимание
        (75, 90, QColor("#FF851B")),   # оранжевый — предупреждение
        (90,120, QColor("#FF4136")),   # красный — опасность
    ]

    # Углы в СИСТЕМЕ QT: 0° = 3 часа, 90° = 12 часов,
    # положительное направление — ПРОТИВ часовой стрелки.
    START_ANGLE = 210      # 7:30 — начало шкалы (0 bar)
    SWEEP_ANGLE = -240     # идём ПО часовой на 240° до 4:30 (120 bar)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 29.0
        self._min = 0.0
        self._max = 120.0
        self.setMinimumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float):
        v = max(self._min, min(self._max, v))
        if abs(v - self._value) > 1e-3:
            self._value = v
            self.valueChanged.emit(v)
            self.update()

    def _value_to_qt_angle(self, v: float) -> float:
        t = (v - self._min) / (self._max - self._min)
        return self.START_ANGLE + t * self.SWEEP_ANGLE

    @staticmethod
    def _qt_to_xy(cx, cy, r, qt_angle_deg):
        a = math.radians(qt_angle_deg)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        R = min(W, H) / 2 - 20

        # ── Корпус ──
        body_r = R + 16
        body_grad = QRadialGradient(cx, cy, body_r)
        body_grad.setColorAt(0.0, QColor("#666"))
        body_grad.setColorAt(0.7, QColor("#2A2A2A"))
        body_grad.setColorAt(1.0, QColor("#111"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(body_grad))
        p.drawEllipse(QPointF(cx, cy), body_r, body_r)

        rim_grad = QRadialGradient(cx - body_r * 0.3, cy - body_r * 0.3, body_r)
        rim_grad.setColorAt(0.0, QColor("#EEE"))
        rim_grad.setColorAt(0.5, QColor("#999"))
        rim_grad.setColorAt(1.0, QColor("#333"))
        p.setPen(QPen(QBrush(rim_grad), 4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), body_r - 2, body_r - 2)

        # ── Циферблат ──
        dial_grad = QRadialGradient(cx, cy, R)
        dial_grad.setColorAt(0.0, QColor("#FAFAFA"))
        dial_grad.setColorAt(1.0, QColor("#D0D0D0"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(dial_grad))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # ── Цветные зоны ──
        for lo, hi, color in self.ZONES:
            a1 = self._value_to_qt_angle(lo)
            a2 = self._value_to_qt_angle(hi)
            sweep = a2 - a1
            path = QPainterPath()
            path.moveTo(cx, cy)
            path.arcTo(QRectF(cx - R, cy - R, 2 * R, 2 * R), a1, sweep)
            path.closeSubpath()
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(color))
            p.drawPath(path)

        # ── Деления ──
        major_ticks = list(range(0, 121, 15))
        minor_ticks = list(range(0, 121, 5))

        for v in minor_ticks:
            angle = self._value_to_qt_angle(v)
            is_major = v in major_ticks
            inner = R - (20 if is_major else 11)
            outer = R - 4
            x1, y1 = self._qt_to_xy(cx, cy, inner, angle)
            x2, y2 = self._qt_to_xy(cx, cy, outer, angle)
            p.setPen(QPen(QColor("#111"), 2.5 if is_major else 1))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── Цифры ──
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.setPen(QColor("#111"))
        for v in major_ticks:
            angle = self._value_to_qt_angle(v)
            x, y = self._qt_to_xy(cx, cy, R - 34, angle)
            p.drawText(QRectF(x - 16, y - 12, 32, 24),
                       Qt.AlignCenter, str(v))

        # ── Стрелка ──
        angle = self._value_to_qt_angle(self._value)
        needle_len = R - 40
        tip_x, tip_y = self._qt_to_xy(cx, cy, needle_len, angle)

        a_rad = math.radians(angle)
        perp = a_rad + math.pi / 2
        bw = 5
        b1x = cx + bw * math.cos(perp)
        b1y = cy - bw * math.sin(perp)
        b2x = cx - bw * math.cos(perp)
        b2y = cy + bw * math.sin(perp)

        needle = QPolygonF([QPointF(tip_x, tip_y),
                            QPointF(b1x, b1y),
                            QPointF(b2x, b2y)])
        p.setPen(QPen(QColor("#111"), 1))
        p.setBrush(QBrush(QColor("#1A1A1A")))
        p.drawPolygon(needle)

        # ось
        axis_grad = QRadialGradient(cx, cy, 10)
        axis_grad.setColorAt(0.0, QColor("#EEE"))
        axis_grad.setColorAt(1.0, QColor("#333"))
        p.setPen(QPen(QColor("#111"), 1.5))
        p.setBrush(QBrush(axis_grad))
        p.drawEllipse(QPointF(cx, cy), 10, 10)

        # ── Подпись ──
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.setPen(QColor("#111"))
        p.drawText(QRectF(0, cy + R * 0.55, W, 30),
                   Qt.AlignCenter, f"{self._value:.1f} [bar]")
        p.end()


# ─────────────────────────────────────────────
#  Аналоговые часы
# ─────────────────────────────────────────────
class AnalogClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        R = min(W, H) / 2 - 18

        now = datetime.now()
        h, m, s = now.hour % 12, now.minute, now.second
        ms = now.microsecond / 1_000_000

        # корпус
        body_r = R + 14
        body_grad = QRadialGradient(cx, cy, body_r)
        body_grad.setColorAt(0.0, QColor("#E84040"))
        body_grad.setColorAt(0.6, QColor("#B22222"))
        body_grad.setColorAt(1.0, QColor("#600"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(body_grad))
        p.drawEllipse(QPointF(cx, cy), body_r, body_r)

        rim_grad = QRadialGradient(cx - body_r * 0.3, cy - body_r * 0.3, body_r)
        rim_grad.setColorAt(0.0, QColor("#FFF"))
        rim_grad.setColorAt(0.5, QColor("#CCC"))
        rim_grad.setColorAt(1.0, QColor("#666"))
        p.setPen(QPen(QBrush(rim_grad), 4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), body_r - 2, body_r - 2)

        dial_grad = QRadialGradient(cx, cy, R)
        dial_grad.setColorAt(0.0, QColor("#FFF"))
        dial_grad.setColorAt(1.0, QColor("#F0F0F0"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(dial_grad))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # деления
        for i in range(60):
            qt_angle = 90 - i * 6
            is_hour = i % 5 == 0
            inner = R - (20 if is_hour else 10)
            outer = R - 4
            a = math.radians(qt_angle)
            x1, y1 = cx + inner * math.cos(a), cy - inner * math.sin(a)
            x2, y2 = cx + outer * math.cos(a), cy - outer * math.sin(a)
            p.setPen(QPen(QColor("#111"), 3 if is_hour else 1))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # цифры
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.setPen(QColor("#111"))
        for n in range(1, 13):
            qt_angle = 90 - n * 30
            a = math.radians(qt_angle)
            x = cx + (R - 34) * math.cos(a)
            y = cy - (R - 34) * math.sin(a)
            p.drawText(QRectF(x - 14, y - 12, 28, 24), Qt.AlignCenter, str(n))

        def draw_hand(qt_angle_deg, length, width, color, tail=0.15):
            a = math.radians(qt_angle_deg)
            tip_x, tip_y = cx + length * math.cos(a), cy - length * math.sin(a)
            tail_x = cx - tail * length * math.cos(a)
            tail_y = cy + tail * length * math.sin(a)
            perp = a + math.pi / 2
            hw = width / 2
            poly = QPolygonF([
                QPointF(tip_x, tip_y),
                QPointF(cx + hw * math.cos(perp), cy - hw * math.sin(perp)),
                QPointF(tail_x, tail_y),
                QPointF(cx - hw * math.cos(perp), cy + hw * math.sin(perp)),
            ])
            p.setPen(QPen(color.darker(130), 1))
            p.setBrush(QBrush(color))
            p.drawPolygon(poly)

        h_angle = 90 - (h * 30 + m * 0.5)
        draw_hand(h_angle, R * 0.50, 10, QColor("#1A1A1A"))

        m_angle = 90 - (m * 6 + s * 0.1)
        draw_hand(m_angle, R * 0.72, 6, QColor("#222"))

        s_angle = 90 - (s * 6 + ms * 6)
        draw_hand(s_angle, R * 0.80, 2, QColor("#E02020"), tail=0.22)

        axis_grad = QRadialGradient(cx, cy, 10)
        axis_grad.setColorAt(0.0, QColor("#FFF"))
        axis_grad.setColorAt(1.0, QColor("#333"))
        p.setPen(QPen(QColor("#111"), 1.5))
        p.setBrush(QBrush(axis_grad))
        p.drawEllipse(QPointF(cx, cy), 9, 9)

        p.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        p.setPen(QColor("#555"))
        p.drawText(QRectF(0, cy + R * 0.55, W, 24),
                   Qt.AlignCenter, now.strftime("%H:%M:%S"))
        p.end()


# ─────────────────────────────────────────────
#  Главное окно
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Манометр и Аналоговые часы")
        self.setMinimumSize(720, 420)
        self.resize(820, 460)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        man_box = QGroupBox("Манометр — шкала давления")
        man_box.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 13px;
                border: 1px solid #CCC; border-radius: 8px;
                margin-top: 14px; padding-top: 16px; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        man_layout = QVBoxLayout(man_box)
        self.manometer = ManometerWidget()
        man_layout.addWidget(self.manometer)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Давление:"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1200)
        self.slider.setValue(290)
        self.slider.valueChanged.connect(self._on_slider)
        slider_layout.addWidget(self.slider)
        self.val_label = QLabel("29.0 bar")
        self.val_label.setMinimumWidth(70)
        self.val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_layout.addWidget(self.val_label)
        man_layout.addLayout(slider_layout)

        clock_box = QGroupBox("Аналоговые часы")
        clock_box.setStyleSheet(man_box.styleSheet())
        clock_layout = QVBoxLayout(clock_box)
        self.clock = AnalogClockWidget()
        clock_layout.addWidget(self.clock)

        layout.addWidget(man_box, 1)
        layout.addWidget(clock_box, 1)
        self.manometer.value = 29.0

    def _on_slider(self, v: int):
        val = v / 10.0
        self.manometer.value = val
        self.val_label.setText(f"{val:.1f} bar")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background: #F5F5F5; }
        QLabel { font-size: 12px; }
        QSlider::groove:horizontal { height: 6px; background: #DDD; border-radius: 3px; }
        QSlider::handle:horizontal {
            background: #4A90D9; border: 1px solid #357ABD;
            width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
    """)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())