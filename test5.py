"""
Modern Speedometer — тонкая дуга, крупные цифры, значение в центре.
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
                             QHBoxLayout, QSlider, QLabel, QSizePolicy)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                         QLinearGradient, QRadialGradient, QPolygonF)


class SpeedometerWidget(QWidget):
    valueChanged = pyqtSignal(float)

    # Дуга 240°: от 7 часов (210°) до 5 часов (-30° = 330°)
    START_ANGLE = 210
    SWEEP = -240

    MIN_VALUE = 0
    MAX_VALUE = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self.setMinimumSize(440, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        v = max(self.MIN_VALUE, min(self.MAX_VALUE, v))
        if abs(v - self._value) > 0.1:
            self._value = v
            self.valueChanged.emit(v)
            self.update()

    def _value_to_angle(self, v):
        t = (v - self.MIN_VALUE) / (self.MAX_VALUE - self.MIN_VALUE)
        return self.START_ANGLE + t * self.SWEEP

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        cx = W / 2
        cy = H * 0.47
        R = min(W, H) * 0.38

        # ── Фон ──
        bg = QRadialGradient(cx, cy, R * 1.5)
        bg.setColorAt(0.0, QColor("#252528"))
        bg.setColorAt(1.0, QColor("#0C0C0E"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(0, 0, W, H), 20, 20)

        # ── Тонкая дуга-трек (серая, фоновая) ──
        track_width = 8
        p.setPen(QPen(QColor("#3A3A3E"), track_width, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - R, cy - R, 2 * R, 2 * R),
                  self.START_ANGLE * 16, self.SWEEP * 16)

        # ─ Цветная дуга (прогресс) — от 0 до текущего значения ──
        if self._value > 0:
            current_angle = self._value_to_angle(self._value)
            progress_sweep = current_angle - self.START_ANGLE  # отрицательный

            # градиент по дуге: зелёный → жёлтый → красный
            # рисуем сегментами
            num_seg = 60
            for i in range(num_seg):
                t1 = i / num_seg
                t2 = (i + 1) / num_seg
                if t1 > self._value / self.MAX_VALUE:
                    break
                a1 = self.START_ANGLE + t1 * self.SWEEP
                a2 = self.START_ANGLE + t2 * self.SWEEP
                sweep = a2 - a1

                # цвет зависит от позиции
                ratio = (t1 + t2) / 2
                if ratio < 0.5:
                    tt = ratio * 2
                    r = int(40 + (240 - 40) * tt)
                    g = int(200 + (200 - 200) * tt)
                    b = int(80 + (60 - 80) * tt)
                else:
                    tt = (ratio - 0.5) * 2
                    r = int(240 + (230 - 240) * tt)
                    g = int(200 + (50 - 200) * tt)
                    b = int(60 + (50 - 60) * tt)

                p.setPen(QPen(QColor(r, g, b), track_width,
                              Qt.SolidLine, Qt.RoundCap))
                p.drawArc(QRectF(cx - R, cy - R, 2 * R, 2 * R),
                          int(a1 * 16), int(sweep * 16))

        # ── Деления (мелкие, на дуге) ──
        for v in range(self.MIN_VALUE, self.MAX_VALUE + 1):
            angle = self._value_to_angle(v)
            a_rad = math.radians(angle)
            is_major = v % 10 == 0
            is_mid = v % 5 == 0

            if is_major:
                r1 = R + track_width / 2 + 2
                r2 = R + track_width / 2 + 14
                pen_w = 2
                color = QColor("#DDD")
            elif is_mid:
                r1 = R + track_width / 2 + 2
                r2 = R + track_width / 2 + 9
                pen_w = 1.2
                color = QColor("#999")
            else:
                r1 = R + track_width / 2 + 2
                r2 = R + track_width / 2 + 5
                pen_w = 0.6
                color = QColor("#555")

            x1 = cx + r1 * math.cos(a_rad)
            y1 = cy - r1 * math.sin(a_rad)
            x2 = cx + r2 * math.cos(a_rad)
            y2 = cy - r2 * math.sin(a_rad)
            p.setPen(QPen(color, pen_w))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── Цифры СНАРУЖИ дуги (крупные, читаемые) ──
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.setPen(QColor("#EEE"))
        for v in range(self.MIN_VALUE, self.MAX_VALUE + 1, 10):
            angle = self._value_to_angle(v)
            a_rad = math.radians(angle)
            r_label = R + track_width / 2 + 30
            x = cx + r_label * math.cos(a_rad)
            y = cy - r_label * math.sin(a_rad)
            p.drawText(QRectF(x - 16, y - 10, 32, 20),
                       Qt.AlignCenter, str(v))

        # ── Стрелка ──
        angle = self._value_to_angle(self._value)
        a_rad = math.radians(angle)
        needle_len = R - 16
        tip_x = cx + needle_len * math.cos(a_rad)
        tip_y = cy - needle_len * math.sin(a_rad)

        perp = a_rad + math.pi / 2
        bw = 2.5
        tail_len = 20
        tail_x = cx - tail_len * math.cos(a_rad)
        tail_y = cy + tail_len * math.sin(a_rad)

        # тень
        shadow = QPolygonF([
            QPointF(tip_x + 1.5, tip_y + 1.5),
            QPointF(cx + bw * math.cos(perp) + 1.5, cy - bw * math.sin(perp) + 1.5),
            QPointF(tail_x + 1.5, tail_y + 1.5),
            QPointF(cx - bw * math.cos(perp) + 1.5, cy + bw * math.sin(perp) + 1.5),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 70)))
        p.drawPolygon(shadow)

        # стрелка
        needle = QPolygonF([
            QPointF(tip_x, tip_y),
            QPointF(cx + bw * math.cos(perp), cy - bw * math.sin(perp)),
            QPointF(tail_x, tail_y),
            QPointF(cx - bw * math.cos(perp), cy + bw * math.sin(perp)),
        ])
        p.setPen(QPen(QColor("#AA1111"), 0.5))
        p.setBrush(QBrush(QColor("#EE2222")))
        p.drawPolygon(needle)

        # ── Центральная ось (небольшой красный круг) ──
        axis_r = 10
        axis_grad = QRadialGradient(cx - 2, cy - 2, axis_r)
        axis_grad.setColorAt(0.0, QColor("#FF6666"))
        axis_grad.setColorAt(1.0, QColor("#990000"))
        p.setPen(QPen(QColor("#660000"), 1))
        p.setBrush(QBrush(axis_grad))
        p.drawEllipse(QPointF(cx, cy), axis_r, axis_r)

        # ── Цифровое значение В ЦЕНТРЕ (крупно) ──
        p.setFont(QFont("Segoe UI", 48, QFont.Bold))
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(0, cy + 30, W, 60),
                   Qt.AlignCenter, f"{self._value:.0f}")

        # подпись "km/h"
        p.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        p.setPen(QColor("#888"))
        p.drawText(QRectF(0, cy + 80, W, 20),
                   Qt.AlignCenter, "km/h")

        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Спидометр")
        self.setMinimumSize(500, 480)
        self.resize(540, 520)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.speedometer = SpeedometerWidget()
        layout.addWidget(self.speedometer, 1)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Скорость:"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self._on_slider)
        slider_layout.addWidget(self.slider)
        self.val_label = QLabel("0")
        self.val_label.setMinimumWidth(30)
        self.val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_layout.addWidget(self.val_label)
        layout.addLayout(slider_layout)

    def _on_slider(self, v):
        self.speedometer.value = float(v)
        self.val_label.setText(str(v))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background: #1A1A1E; }
        QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }
        QSlider::handle:horizontal {
            background: #4A90D9; border: 1px solid #357ABD;
            width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
        QSlider::sub-page:horizontal { background: #4A90D9; border-radius: 3px; }
        QLabel { color: #EEE; font-size: 13px; }
    """)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())