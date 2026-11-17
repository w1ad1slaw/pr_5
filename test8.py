"""
Circular Progress & Internet Speed Test Gauge
Релизное качество: свечение, анимация, градиенты.
"""

import os
import sys
import math

try:
    import PyQt5 as _pq5
    _qt_plugins_path = os.path.join(os.path.dirname(_pq5.__file__), 'Qt5', 'plugins')
    if os.path.isdir(_qt_plugins_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = _qt_plugins_path
except ImportError:
    pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QSlider, QLabel, QSizePolicy, QGroupBox)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                         QLinearGradient, QRadialGradient, QPainterPath, QPolygonF)


# ═════════════════════════════════════════════════
#  1. CIRCULAR PROGRESS INDICATOR (первый виджет)
# ══════════════════════════════════════════════════
class CircularProgressWidget(QWidget):
    """
    Тёмный круговой индикатор прогресса со светящейся точкой.
    Стиль: минимализм, неоновое свечение.
    """

    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._display_value = 0.0
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)

    def _animate(self):
        diff = self._value - self._display_value
        if abs(diff) < 0.1:
            self._display_value = self._value
        else:
            self._display_value += diff * 0.1
        self.update()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        v = max(0.0, min(100.0, v))
        if abs(v - self._value) > 0.01:
            self._value = v
            self.valueChanged.emit(v)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        R = min(W, H) * 0.38

        # ── Фон (тёмный круг) ──
        bg = QRadialGradient(cx, cy, R * 1.1)
        bg.setColorAt(0.0, QColor("#2A2A30"))
        bg.setColorAt(1.0, QColor("#141418"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg))
        p.drawEllipse(QPointF(cx, cy), R + 10, R + 10)

        # ── Трек (серая дуга) ──
        track_r = R
        track_width = 10
        p.setPen(QPen(QColor("#2A2A30"), track_width, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                  90 * 16, -360 * 16)  # полный круг, начиная с 12 часов

        # ── Прогресс (синяя дуга) ──
        if self._display_value > 0.1:
            progress_angle = -360 * (self._display_value / 100.0)

            # свечение
            p.setPen(QPen(QColor(70, 130, 255, 50), track_width + 12,
                          Qt.SolidLine, Qt.RoundCap))
            p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                      90 * 16, int(progress_angle * 16))

            # основная дуга с градиентом
            progress_color = QColor("#4A90FF")
            p.setPen(QPen(progress_color, track_width, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                      90 * 16, int(progress_angle * 16))

            # ── Светящаяся точка в конце дуги ──
            end_angle_rad = math.radians(90 + progress_angle)
            dot_x = cx + track_r * math.cos(end_angle_rad)
            dot_y = cy - track_r * math.sin(end_angle_rad)

            # внешнее свечение
            glow_r = 18
            glow = QRadialGradient(dot_x, dot_y, glow_r)
            glow.setColorAt(0.0, QColor(70, 130, 255, 120))
            glow.setColorAt(0.5, QColor(70, 130, 255, 40))
            glow.setColorAt(1.0, QColor(70, 130, 255, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(dot_x, dot_y), glow_r, glow_r)

            # сама точка
            dot_grad = QRadialGradient(dot_x - 2, dot_y - 2, 6)
            dot_grad.setColorAt(0.0, QColor("#80B0FF"))
            dot_grad.setColorAt(1.0, QColor("#4A90FF"))
            p.setBrush(QBrush(dot_grad))
            p.setPen(QPen(QColor("#2A60CC"), 1))
            p.drawEllipse(QPointF(dot_x, dot_y), 6, 6)

        # ── Процент в центре ──
        p.setFont(QFont("Segoe UI", 28, QFont.Bold))
        p.setPen(QColor("#4A90FF"))
        p.drawText(QRectF(0, cy - 20, W, 40),
                   Qt.AlignCenter, f"{self._display_value:.0f}%")

        p.end()


# ══════════════════════════════════════════════════
#  2. INTERNET SPEED TEST GAUGE (последний виджет)
# ══════════════════════════════════════════════════
class SpeedTestGauge(QWidget):
    """
    Спидометр скорости интернета.
    Деления: 0M, 25M, 50M, 75M, 88M, 100M
    Цвета: голубой → розовый градиент
    """

    valueChanged = pyqtSignal(float)

    START_ANGLE = 210
    SWEEP = -240

    MIN_VALUE = 0
    MAX_VALUE = 100

    # Основные метки (как на изображении)
    MAJOR_MARKS = [0, 25, 50, 75, 88, 100]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._display_value = 0.0
        self.setMinimumSize(380, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)

    def _animate(self):
        diff = self._value - self._display_value
        if abs(diff) < 0.1:
            self._display_value = self._value
        else:
            self._display_value += diff * 0.1
        self.update()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        v = max(self.MIN_VALUE, min(self.MAX_VALUE, v))
        if abs(v - self._value) > 0.01:
            self._value = v
            self.valueChanged.emit(v)

    def _value_to_angle(self, v):
        t = (v - self.MIN_VALUE) / (self.MAX_VALUE - self.MIN_VALUE)
        return self.START_ANGLE + t * self.SWEEP

    def _get_color(self, v):
        """Голубой → розовый градиент."""
        t = v / self.MAX_VALUE
        if t < 0.5:
            tt = t * 2
            r = int(70 + (220 - 70) * tt)
            g = int(180 + (80 - 180) * tt)
            b = int(255 + (180 - 255) * tt)
        else:
            tt = (t - 0.5) * 2
            r = int(220 + (240 - 220) * tt)
            g = int(80 + (60 - 80) * tt)
            b = int(180 + (200 - 180) * tt)
        return QColor(r, g, b)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        cx = W / 2
        cy = H * 0.48
        R = min(W, H) * 0.38

        # ─ Фон ──
        bg = QRadialGradient(cx, cy, R * 1.4)
        bg.setColorAt(0.0, QColor("#2A2A30"))
        bg.setColorAt(1.0, QColor("#0E0E12"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(0, 0, W, H), 20, 20)

        # ── Внешние деления ─
        for v in range(self.MIN_VALUE, self.MAX_VALUE + 1):
            angle = self._value_to_angle(v)
            a_rad = math.radians(angle)
            is_major = v in self.MAJOR_MARKS
            is_mid = v % 10 == 0

            if is_major:
                r1 = R + 6
                r2 = R + 20
                pen_w = 2.5
                color = self._get_color(v)
            elif is_mid:
                r1 = R + 6
                r2 = R + 14
                pen_w = 1.5
                color = QColor("#666")
            else:
                r1 = R + 6
                r2 = R + 10
                pen_w = 0.8
                color = QColor("#3A3A3E")

            x1 = cx + r1 * math.cos(a_rad)
            y1 = cy - r1 * math.sin(a_rad)
            x2 = cx + r2 * math.cos(a_rad)
            y2 = cy - r2 * math.sin(a_rad)
            p.setPen(QPen(color, pen_w, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── Цифры на шкале ──
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        for v in self.MAJOR_MARKS:
            angle = self._value_to_angle(v)
            a_rad = math.radians(angle)
            r_label = R + 32
            x = cx + r_label * math.cos(a_rad)
            y = cy - r_label * math.sin(a_rad)
            color = self._get_color(v)
            p.setPen(QPen(color))
            p.drawText(QRectF(x - 16, y - 10, 32, 20),
                       Qt.AlignCenter, f"{v}M")

        # ── Трек дуги ──
        track_r = R - 12
        track_width = 14
        p.setPen(QPen(QColor("#2A2A30"), track_width, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                  self.START_ANGLE * 16, self.SWEEP * 16)

        # ── Цветная дуга прогресса ──
        if self._display_value > 0.1:
            current_angle = self._value_to_angle(self._display_value)
            progress_sweep = current_angle - self.START_ANGLE

            num_seg = 60
            for i in range(num_seg):
                t1 = i / num_seg
                t2 = (i + 1) / num_seg
                if t1 > self._display_value / self.MAX_VALUE:
                    break
                a1 = self.START_ANGLE + t1 * self.SWEEP
                a2 = self.START_ANGLE + t2 * self.SWEEP
                sweep = a2 - a1

                val_at_seg = t1 * self.MAX_VALUE
                color = self._get_color(val_at_seg)

                # свечение
                p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 40),
                              track_width + 8, Qt.SolidLine, Qt.RoundCap))
                p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                          int(a1 * 16), int(sweep * 16))

                # основной сегмент
                p.setPen(QPen(color, track_width, Qt.SolidLine, Qt.RoundCap))
                p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                          int(a1 * 16), int(sweep * 16))

        # ── Стрелка ──
        angle = self._value_to_angle(self._display_value)
        a_rad = math.radians(angle)
        needle_len = R - 28
        tip_x = cx + needle_len * math.cos(a_rad)
        tip_y = cy - needle_len * math.sin(a_rad)

        perp = a_rad + math.pi / 2
        bw = 2.5
        tail_len = 16
        tail_x = cx - tail_len * math.cos(a_rad)
        tail_y = cy + tail_len * math.sin(a_rad)

        # тень
        shadow = [
            QPointF(tip_x + 2, tip_y + 2),
            QPointF(cx + bw * math.cos(perp) + 2, cy - bw * math.sin(perp) + 2),
            QPointF(tail_x + 2, tail_y + 2),
            QPointF(cx - bw * math.cos(perp) + 2, cy + bw * math.sin(perp) + 2),
        ]
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 70)))
        p.drawPolygon(QPolygonF(shadow))

        # стрелка
        needle_color = self._get_color(self._display_value)
        needle = [
            QPointF(tip_x, tip_y),
            QPointF(cx + bw * math.cos(perp), cy - bw * math.sin(perp)),
            QPointF(tail_x, tail_y),
            QPointF(cx - bw * math.cos(perp), cy + bw * math.sin(perp)),
        ]
        p.setPen(QPen(needle_color.darker(130), 0.5))
        p.setBrush(QBrush(needle_color))
        p.drawPolygon(QPolygonF(needle))

        # ось
        axis_r = 8
        axis_grad = QRadialGradient(cx - 2, cy - 2, axis_r)
        axis_grad.setColorAt(0.0, QColor("#FFF"))
        axis_grad.setColorAt(1.0, QColor("#888"))
        p.setPen(QPen(QColor("#555"), 1))
        p.setBrush(QBrush(axis_grad))
        p.drawEllipse(QPointF(cx, cy), axis_r, axis_r)

        # ── Цифровое значение внизу ──
        p.setFont(QFont("Segoe UI", 32, QFont.Bold))
        value_color = self._get_color(self._display_value)
        p.setPen(QPen(value_color))
        p.drawText(QRectF(0, cy + R * 0.5, W, 40),
                   Qt.AlignCenter, f"{self._display_value:.0f}")

        p.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        p.setPen(QColor("#888"))
        p.drawText(QRectF(0, cy + R * 0.5 + 35, W, 20),
                   Qt.AlignCenter, "Mbps")

        p.end()


# ══════════════════════════════════════════════════
#  Главное окно
# ══════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circular Progress & Speed Test")
        self.setMinimumSize(800, 420)
        self.resize(840, 460)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ── Circular Progress ──
        cp_box = QGroupBox("Circular Progress")
        cp_box.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 13px;
                border: 1px solid #333; border-radius: 8px;
                margin-top: 14px; padding-top: 16px;
                background: #1A1A1E; color: #EEE; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        cp_layout = QVBoxLayout(cp_box)
        self.cp_gauge = CircularProgressWidget()
        cp_layout.addWidget(self.cp_gauge, 1)

        cp_slider = QHBoxLayout()
        cp_slider.addWidget(QLabel("Прогресс:"))
        self.cp_slider = QSlider(Qt.Horizontal)
        self.cp_slider.setRange(0, 100)
        self.cp_slider.setValue(75)
        self.cp_slider.valueChanged.connect(self._on_cp)
        cp_slider.addWidget(self.cp_slider)
        self.cp_label = QLabel("75%")
        self.cp_label.setMinimumWidth(45)
        self.cp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cp_slider.addWidget(self.cp_label)
        cp_layout.addLayout(cp_slider)

        # ── Speed Test ──
        st_box = QGroupBox("Speed Test")
        st_box.setStyleSheet(cp_box.styleSheet())
        st_layout = QVBoxLayout(st_box)
        self.st_gauge = SpeedTestGauge()
        st_layout.addWidget(self.st_gauge, 1)

        st_slider = QHBoxLayout()
        st_slider.addWidget(QLabel("Скорость:"))
        self.st_slider = QSlider(Qt.Horizontal)
        self.st_slider.setRange(0, 100)
        self.st_slider.setValue(65)
        self.st_slider.valueChanged.connect(self._on_st)
        st_slider.addWidget(self.st_slider)
        self.st_label = QLabel("65")
        self.st_label.setMinimumWidth(35)
        self.st_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        st_slider.addWidget(self.st_label)
        st_layout.addLayout(st_slider)

        layout.addWidget(cp_box, 1)
        layout.addWidget(st_box, 1)

        # Начальные значения с анимацией
        QTimer.singleShot(300, lambda: self._on_cp(75))
        QTimer.singleShot(500, lambda: self._on_st(65))

    def _on_cp(self, v):
        self.cp_gauge.value = float(v)
        self.cp_label.setText(f"{v}%")

    def _on_st(self, v):
        self.st_gauge.value = float(v)
        self.st_label.setText(str(v))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background: #141418; }
        QSlider::groove:horizontal { height: 6px; background: #2A2A30; border-radius: 3px; }
        QSlider::handle:horizontal {
            background: #4A90D9; border: 1px solid #357ABD;
            width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }
        QSlider::sub-page:horizontal { background: #4A90D9; border-radius: 3px; }
        QLabel { color: #DDD; font-size: 13px; }
    """)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())