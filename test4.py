"""
Stylized Gauges — чистый минималистичный дизайн.
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

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QSlider, QVBoxLayout, QLabel, QGroupBox, QSizePolicy)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                         QLinearGradient, QRadialGradient, QPainterPath,
                         QPolygonF)


# ─────────────────────────────────────────────
#  GOOD / BAD индикатор (минималистичный)
# ─────────────────────────────────────────────
class GoodBadGauge(QWidget):
    valueChanged = pyqtSignal(float)

    # Цвета сегментов — плавный переход
    SEGMENTS = [
        (0,   25, QColor("#2ECC71")),   # зелёный
        (25,  50, QColor("#A8E063")),   # салатовый
        (50,  65, QColor("#F7DC6F")),   # жёлтый
        (65,  80, QColor("#F39C12")),   # оранжевый
        (80,  90, QColor("#E74C3C")),   # красный
        (90, 100, QColor("#C0392B")),   # тёмно-красный
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 15.0
        self.setMinimumSize(360, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        v = max(0.0, min(100.0, v))
        if abs(v - self._value) > 0.1:
            self._value = v
            self.valueChanged.emit(v)
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        margin = 12

        # ── Корпус ──
        body_rect = QRectF(margin, margin, W - 2 * margin, H - 2 * margin)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 40)))
        p.drawRoundedRect(QRectF(margin + 3, margin + 3,
                                 W - 2 * margin, H - 2 * margin), 16, 16)

        body_grad = QLinearGradient(0, 0, 0, H)
        body_grad.setColorAt(0.0, QColor("#3A3A3A"))
        body_grad.setColorAt(1.0, QColor("#1A1A1A"))
        p.setBrush(QBrush(body_grad))
        p.setPen(QPen(QColor("#555"), 1))
        p.drawRoundedRect(body_rect, 16, 16)

        # ── Светлая панель ──
        pm = 14
        panel_top = margin + pm
        panel_bottom = margin + int(H * 0.68)
        panel_rect = QRectF(margin + pm, panel_top,
                            W - 2 * (margin + pm),
                            panel_bottom - panel_top)

        dial_grad = QLinearGradient(0, panel_top, 0, panel_bottom)
        dial_grad.setColorAt(0.0, QColor("#F0F0F0"))
        dial_grad.setColorAt(1.0, QColor("#C8C8C8"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(dial_grad))

        path = QPainterPath()
        r = 10
        path.moveTo(panel_rect.left() + r, panel_rect.top())
        path.arcTo(panel_rect.left(), panel_rect.top(), 2 * r, 2 * r, 90, 90)
        path.lineTo(panel_rect.left(), panel_rect.bottom())
        path.lineTo(panel_rect.right(), panel_rect.bottom())
        path.arcTo(panel_rect.right() - 2 * r, panel_rect.top(), 2 * r, 2 * r, 0, 90)
        path.closeSubpath()
        p.drawPath(path)

        # ── Дуга шкалы ──
        cx = W / 2
        cy = panel_bottom - 6
        arc_r = min((W - 2 * (margin + pm)) / 2 - 20,
                    (panel_bottom - panel_top) - 25)
        arc_r = max(arc_r, 50)

        # цветные сегменты (тонкая дуга)
        for lo, hi, color in self.SEGMENTS:
            a1 = 180 - (lo / 100.0) * 180
            a2 = 180 - (hi / 100.0) * 180
            sweep = a2 - a1
            pen = QPen(color, 10, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - arc_r, cy - arc_r, 2 * arc_r, 2 * arc_r),
                      int(a1 * 16), int(sweep * 16))

        # ── Мелкие деления (без цифр, как в примере) ──
        for v in range(0, 101, 5):
            angle = 180 - (v / 100.0) * 180
            a_rad = math.radians(angle)
            is_major = v % 25 == 0
            r1 = arc_r + 8
            r2 = arc_r + (14 if is_major else 10)
            x1 = cx + r1 * math.cos(a_rad)
            y1 = cy - r1 * math.sin(a_rad)
            x2 = cx + r2 * math.cos(a_rad)
            y2 = cy - r2 * math.sin(a_rad)
            p.setPen(QPen(QColor("#555"), 1.5 if is_major else 0.8))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── Стрелка ──
        angle = 180 - (self._value / 100.0) * 180
        a_rad = math.radians(angle)
        needle_len = arc_r - 12
        tip_x = cx + needle_len * math.cos(a_rad)
        tip_y = cy - needle_len * math.sin(a_rad)

        perp = a_rad + math.pi / 2
        bw = 1.8
        tail_len = 14
        tail_x = cx - tail_len * math.cos(a_rad)
        tail_y = cy + tail_len * math.sin(a_rad)

        needle = QPolygonF([
            QPointF(tip_x, tip_y),
            QPointF(cx + bw * math.cos(perp), cy - bw * math.sin(perp)),
            QPointF(tail_x, tail_y),
            QPointF(cx - bw * math.cos(perp), cy + bw * math.sin(perp)),
        ])
        p.setPen(QPen(QColor("#8B0000"), 0.5))
        p.setBrush(QBrush(QColor("#DC143C")))
        p.drawPolygon(needle)

        # ось
        axis_grad = QRadialGradient(cx, cy, 6)
        axis_grad.setColorAt(0.0, QColor("#EEE"))
        axis_grad.setColorAt(1.0, QColor("#555"))
        p.setPen(QPen(QColor("#333"), 1))
        p.setBrush(QBrush(axis_grad))
        p.drawEllipse(QPointF(cx, cy), 5, 5)

        # ── "%" — маленький, аккуратный ──
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.setPen(QColor("#666"))
        p.drawText(QRectF(0, cy + 2, W, 20), Qt.AlignCenter, "%")

        # ── Батарея — маленькая, в правом нижнем углу ──
        bat_w = 44
        bat_h = 14
        bat_x = W - margin - pm - bat_w - 6
        bat_y = H - margin - pm - bat_h - 6
        cells = 4
        cell_w = (bat_w - 8) / cells
        gap = 1.5

        p.setPen(QPen(QColor("#777"), 1))
        p.setBrush(QBrush(QColor("#222")))
        p.drawRoundedRect(QRectF(bat_x, bat_y, bat_w, bat_h), 2, 2)
        p.setBrush(QBrush(QColor("#777")))
        p.setPen(Qt.NoPen)
        p.drawRect(QRectF(bat_x + bat_w, bat_y + 4, 3, bat_h - 8))

        fill_level = self._value / 100.0
        filled_cells = int(fill_level * cells)
        for i in range(cells):
            cx_cell = bat_x + 4 + i * (cell_w + gap)
            cy_cell = bat_y + 2
            cw = cell_w
            ch = bat_h - 4
            if i < filled_cells:
                if fill_level < 0.3:
                    color = QColor("#E74C3C")
                elif fill_level < 0.6:
                    color = QColor("#F1C40F")
                else:
                    color = QColor("#2ECC71")
                p.setBrush(QBrush(color))
            else:
                p.setBrush(QBrush(QColor("#333")))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(cx_cell, cy_cell, cw, ch), 1, 1)

        p.end()


# ─────────────────────────────────────────────
#  Градиентный gauge
# ─────────────────────────────────────────────
class GradientGauge(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 65.0
        self.setMinimumSize(360, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        v = max(0.0, min(100.0, v))
        if abs(v - self._value) > 0.1:
            self._value = v
            self.valueChanged.emit(v)
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        margin = 12

        # ── Корпус ──
        body_rect = QRectF(margin, margin, W - 2 * margin, H - 2 * margin)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 50)))
        p.drawRoundedRect(QRectF(margin + 3, margin + 3,
                                 W - 2 * margin, H - 2 * margin), 16, 16)

        body_grad = QLinearGradient(0, 0, 0, H)
        body_grad.setColorAt(0.0, QColor("#2C2C2C"))
        body_grad.setColorAt(1.0, QColor("#0D0D0D"))
        p.setBrush(QBrush(body_grad))
        p.setPen(QPen(QColor("#444"), 1))
        p.drawRoundedRect(body_rect, 16, 16)

        # ── Внутренняя панель ──
        inner_m = 18
        inner_rect = QRectF(margin + inner_m, margin + inner_m,
                            W - 2 * (margin + inner_m),
                            H - 2 * (margin + inner_m) - 8)
        inner_grad = QLinearGradient(0, inner_rect.top(), 0, inner_rect.bottom())
        inner_grad.setColorAt(0.0, QColor("#222"))
        inner_grad.setColorAt(1.0, QColor("#111"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(inner_grad))
        p.drawRoundedRect(inner_rect, 10, 10)

        # ── Дуга ─
        cx = W / 2
        cy = H * 0.56
        arc_r = min(W, H) * 0.28

        num_segments = 100
        for i in range(num_segments):
            t1 = i / num_segments
            a1 = 180 - t1 * 180
            a2 = 180 - ((i + 1) / num_segments) * 180
            sweep = a2 - a1

            if t1 < 0.5:
                tt = t1 * 2
                r = int(39 + (241 - 39) * tt)
                g = int(174 + (196 - 174) * tt)
                b = int(96 + (15 - 96) * tt)
            else:
                tt = (t1 - 0.5) * 2
                r = int(241 + (231 - 241) * tt)
                g = int(196 + (76 - 196) * tt)
                b = int(15 + (60 - 15) * tt)

            pen = QPen(QColor(r, g, b), 10, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - arc_r, cy - arc_r, 2 * arc_r, 2 * arc_r),
                      int(a1 * 16), int(sweep * 16))

        # ─ Стрелка ──
        angle = 180 - (self._value / 100.0) * 180
        a_rad = math.radians(angle)
        needle_len = arc_r - 6
        tip_x = cx + needle_len * math.cos(a_rad)
        tip_y = cy - needle_len * math.sin(a_rad)
        perp = a_rad + math.pi / 2
        bw = 2.5
        tail_len = 16
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
        p.setBrush(QBrush(QColor(0, 0, 0, 50)))
        p.drawPolygon(shadow)

        needle_grad = QLinearGradient(tail_x, tail_y, tip_x, tip_y)
        needle_grad.setColorAt(0.0, QColor("#999"))
        needle_grad.setColorAt(0.5, QColor("#EEE"))
        needle_grad.setColorAt(1.0, QColor("#FFF"))

        needle = QPolygonF([
            QPointF(tip_x, tip_y),
            QPointF(cx + bw * math.cos(perp), cy - bw * math.sin(perp)),
            QPointF(tail_x, tail_y),
            QPointF(cx - bw * math.cos(perp), cy + bw * math.sin(perp)),
        ])
        p.setPen(QPen(QColor("#666"), 0.5))
        p.setBrush(QBrush(needle_grad))
        p.drawPolygon(needle)

        axis_grad = QRadialGradient(cx, cy, 8)
        axis_grad.setColorAt(0.0, QColor("#FFF"))
        axis_grad.setColorAt(0.6, QColor("#AAA"))
        axis_grad.setColorAt(1.0, QColor("#444"))
        p.setPen(QPen(QColor("#333"), 1))
        p.setBrush(QBrush(axis_grad))
        p.drawEllipse(QPointF(cx, cy), 7, 7)

        # ── Значение ──
        p.setFont(QFont("Segoe UI", 22, QFont.Bold))
        p.setPen(QColor("#DDD"))
        p.drawText(QRectF(0, cy + 18, W, 30),
                   Qt.AlignCenter, f"{self._value:.0f}%")

        p.end()


# ─────────────────────────────────────────────
#  Главное окно
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stylized Gauges")
        self.setMinimumSize(780, 340)
        self.resize(840, 380)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ── GOOD/BAD ──
        gb_box = QGroupBox("Индикатор GOOD / BAD")
        gb_box.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 13px;
                border: 1px solid #555; border-radius: 8px;
                margin-top: 14px; padding-top: 14px;
                background: #2A2A2A; color: #EEE; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        gb_layout = QVBoxLayout(gb_box)
        self.gb_gauge = GoodBadGauge()
        gb_layout.addWidget(self.gb_gauge)

        sl = QHBoxLayout()
        sl.addWidget(QLabel("Значение:"))
        self.gb_slider = QSlider(Qt.Horizontal)
        self.gb_slider.setRange(0, 100)
        self.gb_slider.setValue(15)
        self.gb_slider.valueChanged.connect(self._on_gb)
        sl.addWidget(self.gb_slider)
        self.gb_label = QLabel("15%")
        self.gb_label.setMinimumWidth(45)
        self.gb_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        sl.addWidget(self.gb_label)
        gb_layout.addLayout(sl)

        # ── Gradient ──
        gr_box = QGroupBox("Градиентный индикатор")
        gr_box.setStyleSheet(gb_box.styleSheet())
        gr_layout = QVBoxLayout(gr_box)
        self.gr_gauge = GradientGauge()
        gr_layout.addWidget(self.gr_gauge)

        sl2 = QHBoxLayout()
        sl2.addWidget(QLabel("Значение:"))
        self.gr_slider = QSlider(Qt.Horizontal)
        self.gr_slider.setRange(0, 100)
        self.gr_slider.setValue(65)
        self.gr_slider.valueChanged.connect(self._on_gr)
        sl2.addWidget(self.gr_slider)
        self.gr_label = QLabel("65%")
        self.gr_label.setMinimumWidth(45)
        self.gr_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        sl2.addWidget(self.gr_label)
        gr_layout.addLayout(sl2)

        layout.addWidget(gb_box, 1)
        layout.addWidget(gr_box, 1)

    def _on_gb(self, v):
        self.gb_gauge.value = float(v)
        self.gb_label.setText(f"{v}%")

    def _on_gr(self, v):
        self.gr_gauge.value = float(v)
        self.gr_label.setText(f"{v}%")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background: #1E1E1E; }
        QSlider::groove:horizontal { height: 5px; background: #444; border-radius: 3px; }
        QSlider::handle:horizontal {
            background: #4A90D9; border: 1px solid #357ABD;
            width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
        QSlider::sub-page:horizontal { background: #4A90D9; border-radius: 3px; }
        QLabel { color: #EEE; font-size: 12px; }
    """)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())