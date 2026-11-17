"""
Professional LED VU-Meter — релизный вариант со свечением, пиками и анимацией.
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
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                         QLinearGradient, QRadialGradient, QPainterPath)


class VUMeterWidget(QWidget):
    """Профессиональный LED VU-метр со свечением и пиковыми индикаторами."""

    DB_MARKS = [-20, -15, -10, -6, -3, 0, 1, 3, 6]
    DB_MIN = -20
    DB_MAX = 6

    # Цвета сегментов с зонами
    ZONE_COLORS = [
        (0.00, 0.55, QColor("#00E5FF")),   # голубой (cyan)
        (0.55, 0.75, QColor("#7C4DFF")),   # фиолетовый
        (0.75, 0.90, QColor("#E040FB")),   # пурпурный
        (0.90, 1.00, QColor("#FF1744")),   # красный (клип)
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._left_level = 0.0
        self._right_level = 0.0
        self._left_peak = 0.0
        self._right_peak = 0.0
        self._left_display = 0.0  # для анимации decay
        self._right_display = 0.0

        self.setMinimumSize(520, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Таймер анимации decay
        self._decay_timer = QTimer(self)
        self._decay_timer.timeout.connect(self._decay)
        self._decay_timer.start(30)  # ~33 FPS

    def _decay(self):
        """Плавное затухание отображаемого уровня."""
        decay_rate = 0.03
        changed = False

        if self._left_display > self._left_level + 0.001:
            self._left_display = max(self._left_level, self._left_display - decay_rate)
            changed = True
        if self._right_display > self._right_level + 0.001:
            self._right_display = max(self._right_level, self._right_display - decay_rate)
            changed = True

        # Пики затухают медленнее
        peak_decay = 0.01
        if self._left_peak > self._left_level + 0.001:
            self._left_peak = max(self._left_level, self._left_peak - peak_decay)
            changed = True
        if self._right_peak > self._right_level + 0.001:
            self._right_peak = max(self._right_level, self._right_peak - peak_decay)
            changed = True

        if changed:
            self.update()

    @property
    def left_level(self):
        return self._left_level

    @left_level.setter
    def left_level(self, v):
        v = max(0.0, min(1.0, v))
        if v > self._left_peak:
            self._left_peak = v
        self._left_level = v
        if v > self._left_display:
            self._left_display = v

    @property
    def right_level(self):
        return self._right_level

    @right_level.setter
    def right_level(self, v):
        v = max(0.0, min(1.0, v))
        if v > self._right_peak:
            self._right_peak = v
        self._right_level = v
        if v > self._right_display:
            self._right_display = v

    def _db_to_pos(self, db):
        return (db - self.DB_MIN) / (self.DB_MAX - self.DB_MIN)

    def _get_color(self, pos):
        for lo, hi, color in self.ZONE_COLORS:
            if lo <= pos < hi:
                return color
        return self.ZONE_COLORS[-1][2]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()

        # ── Корпус с внутренним свечением ──
        margin = 10
        body = QRectF(margin, margin, W - 2 * margin, H - 2 * margin)

        # тень
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 60)))
        p.drawRoundedRect(QRectF(margin + 4, margin + 4,
                                 W - 2 * margin, H - 2 * margin), 12, 12)

        # основной градиент
        body_grad = QLinearGradient(0, 0, 0, H)
        body_grad.setColorAt(0.0, QColor("#1E1E24"))
        body_grad.setColorAt(0.5, QColor("#141418"))
        body_grad.setColorAt(1.0, QColor("#0A0A0C"))
        p.setBrush(QBrush(body_grad))
        p.setPen(QPen(QColor("#2A2A30"), 1.5))
        p.drawRoundedRect(body, 12, 12)

        # внутреннее свечение рамки
        inner_glow = QRectF(margin + 2, margin + 2,
                            W - 2 * margin - 4, H - 2 * margin - 4)
        glow_grad = QLinearGradient(0, inner_glow.top(), 0, inner_glow.bottom())
        glow_grad.setColorAt(0.0, QColor(100, 200, 255, 15))
        glow_grad.setColorAt(0.5, QColor(100, 200, 255, 0))
        glow_grad.setColorAt(1.0, QColor(100, 200, 255, 10))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow_grad))
        p.drawRoundedRect(inner_glow, 10, 10)

        # ── Параметры сегментов ──
        seg_left = 40
        seg_right = W - margin - 20
        seg_top = margin + 20
        seg_height = 12
        seg_gap = 2
        num_seg = 48

        seg_width = (seg_right - seg_left - (num_seg - 1) * seg_gap) / num_seg

        # ── Фоновые дорожки (неактивные сегменты) ──
        for ch, y_offset in enumerate([0, seg_height + 8]):
            y = seg_top + y_offset
            for i in range(num_seg):
                x = seg_left + i * (seg_width + seg_gap)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor("#1A1A1E")))
                p.drawRoundedRect(QRectF(x, y, seg_width, seg_height), 2, 2)

        # ── Активные сегменты со свечением ──
        for ch, (level, display) in enumerate([
            (self._left_level, self._left_display),
            (self._right_level, self._right_display)
        ]):
            y = seg_top + ch * (seg_height + 8)
            filled = int(display * num_seg)

            for i in range(filled):
                pos = i / num_seg
                x = seg_left + i * (seg_width + seg_gap)
                color = self._get_color(pos)

                # свечение вокруг сегмента
                glow_r = seg_width * 0.8
                glow = QRadialGradient(x + seg_width / 2, y + seg_height / 2, glow_r)
                glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 80))
                glow.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(glow))
                p.drawEllipse(QPointF(x + seg_width / 2, y + seg_height / 2),
                              glow_r, glow_r)

                # сам сегмент с градиентом
                seg_grad = QLinearGradient(0, y, 0, y + seg_height)
                seg_grad.setColorAt(0.0, color.lighter(130))
                seg_grad.setColorAt(0.5, color)
                seg_grad.setColorAt(1.0, color.darker(110))
                p.setBrush(QBrush(seg_grad))
                p.setPen(QPen(color.lighter(150), 0.5))
                p.drawRoundedRect(QRectF(x, y, seg_width, seg_height), 2, 2)

        # ── Пиковые маркеры (маленькие треугольники сверху) ──
        for ch, peak in enumerate([self._left_peak, self._right_peak]):
            y = seg_top + ch * (seg_height + 8) - 6
            peak_x = seg_left + peak * (seg_right - seg_left)
            color = self._get_color(peak)

            # треугольник
            triangle = QPainterPath()
            triangle.moveTo(peak_x, y)
            triangle.lineTo(peak_x - 4, y + 5)
            triangle.lineTo(peak_x + 4, y + 5)
            triangle.closeSubpath()

            p.setPen(QPen(color.lighter(120), 1))
            p.setBrush(QBrush(color))
            p.drawPath(triangle)

        # ── Метки L / R ──
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.setPen(QColor("#00E5FF"))
        p.drawText(QRectF(margin + 8, seg_top, 28, seg_height),
                   Qt.AlignCenter, "L")
        p.setPen(QColor("#E040FB"))
        p.drawText(QRectF(margin + 8, seg_top + seg_height + 8, 28, seg_height),
                   Qt.AlignCenter, "R")

        # ── Шкала dB (вплотную под сегментами) ──
        scale_y = seg_top + 2 * (seg_height + 8) + 12

        # горизонтальная линия
        p.setPen(QPen(QColor("#333"), 1))
        p.drawLine(QPointF(seg_left, scale_y - 8),
                   QPointF(seg_right, scale_y - 8))

        # метки dB
        p.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        for db in self.DB_MARKS:
            pos = self._db_to_pos(db)
            x = seg_left + pos * (seg_right - seg_left)

            # вертикальная линия
            p.setPen(QPen(QColor("#444"), 1))
            p.drawLine(QPointF(x, scale_y - 10), QPointF(x, scale_y - 4))

            # текст
            text = f"{db:+d}" if db != 0 else "0"
            p.setPen(QColor("#AAA"))
            p.drawText(QRectF(x - 10, scale_y - 2, 20, 12),
                       Qt.AlignCenter, text)

        # подпись "dB"
        p.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        p.setPen(QColor("#666"))
        p.drawText(QRectF(seg_right + 4, scale_y - 2, 16, 12),
                   Qt.AlignLeft, "dB")

        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LED VU-Meter")
        self.setMinimumSize(580, 320)
        self.resize(620, 340)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # VU-метр
        self.vu_meter = VUMeterWidget()
        layout.addWidget(self.vu_meter, 1)

        # Слайдеры
        sliders = QVBoxLayout()
        sliders.setSpacing(12)

        for label, setter, slider_attr, label_attr in [
            ("L:", self._set_left, 'left_slider', 'left_label'),
            ("R:", self._set_right, 'right_slider', 'right_label')
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(70 if label == "L:" else 60)
            setattr(self, slider_attr, slider)

            val_label = QLabel("70%" if label == "L:" else "60%")
            val_label.setMinimumWidth(45)
            val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            setattr(self, label_attr, val_label)

            slider.valueChanged.connect(
                lambda v, s=setter, l=val_label: (s(v), l.setText(f"{v}%"))
            )

            row.addWidget(slider)
            row.addWidget(val_label)
            sliders.addLayout(row)

        layout.addLayout(sliders)

        # Начальные значения
        self.vu_meter.left_level = 0.70
        self.vu_meter.right_level = 0.60

    def _set_left(self, v):
        self.vu_meter.left_level = v / 100.0

    def _set_right(self, v):
        self.vu_meter.right_level = v / 100.0


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