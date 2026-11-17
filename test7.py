
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
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer, QEasingCurve, QPropertyAnimation
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                         QLinearGradient, QRadialGradient, QConicalGradient,
                         QPainterPath, QPolygonF)


class FitnessGauge(QWidget):
    """
    Тёмный gauge с цветными зонами (зелёный→жёлтый→красный),
    значением в центре и стрелкой. Стиль fitness/activity tracker.
    """

    valueChanged = pyqtSignal(float)

    # Дуга 240°: от 7 часов до 5 часов
    START_ANGLE = 210
    SWEEP = -240

    MIN_VALUE = 0
    MAX_VALUE = 100

    # Цветные зоны
    ZONES = [
        (0,   40, QColor("#2ECC71")),   # зелёный — отлично
        (40,  70, QColor("#F1C40F")),   # жёлтый — нормально
        (70,  85, QColor("#E67E22")),   # оранжевый — внимание
        (85, 100, QColor("#E74C3C")),   # красный — критично
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._display_value = 0.0  # для анимации
        self.setMinimumSize(420, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Анимация плавного изменения
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)  # ~60 FPS

    def _animate(self):
        """Плавное приближение отображаемого значения к целевому."""
        diff = self._value - self._display_value
        if abs(diff) < 0.05:
            self._display_value = self._value
        else:
            self._display_value += diff * 0.12
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

    def _get_zone_color(self, v):
        for lo, hi, color in self.ZONES:
            if lo <= v < hi:
                return color
        return self.ZONES[-1][2]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        cx = W / 2
        cy = H / 2
        R = min(W, H) * 0.40

        # ══════════════════════════════════════════
        #  1. ФОН — тёмный радиальный градиент
        # ══════════════════════════════════════════
        bg = QRadialGradient(cx, cy, R * 1.4)
        bg.setColorAt(0.0, QColor("#2A2A30"))
        bg.setColorAt(0.7, QColor("#1A1A20"))
        bg.setColorAt(1.0, QColor("#0E0E12"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(0, 0, W, H), 24, 24)

        # ══════════════════════════════════════════
        #  2. ВНЕШНИЕ ДЕЛЕНИЯ (чёрточки по периметру)
        # ══════════════════════════════════════════
        for v in range(self.MIN_VALUE, self.MAX_VALUE + 1):
            angle = self._value_to_angle(v)
            a_rad = math.radians(angle)
            is_major = v % 10 == 0
            is_mid = v % 5 == 0

            if is_major:
                r1 = R + 8
                r2 = R + 22
                pen_w = 2.5
                color = QColor("#888")
            elif is_mid:
                r1 = R + 8
                r2 = R + 16
                pen_w = 1.5
                color = QColor("#555")
            else:
                r1 = R + 8
                r2 = R + 12
                pen_w = 0.8
                color = QColor("#333")

            x1 = cx + r1 * math.cos(a_rad)
            y1 = cy - r1 * math.sin(a_rad)
            x2 = cx + r2 * math.cos(a_rad)
            y2 = cy - r2 * math.sin(a_rad)
            p.setPen(QPen(color, pen_w, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ══════════════════════════════════════════
        #  3. ЦИФРЫ НА ШКАЛЕ
        # ══════════════════════════════════════════
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.setPen(QColor("#AAA"))
        for v in range(self.MIN_VALUE, self.MAX_VALUE + 1, 10):
            angle = self._value_to_angle(v)
            a_rad = math.radians(angle)
            r_label = R + 32
            x = cx + r_label * math.cos(a_rad)
            y = cy - r_label * math.sin(a_rad)
            p.drawText(QRectF(x - 14, y - 9, 28, 18),
                       Qt.AlignCenter, str(v))

        # ═════════════════════════════════════════
        #  4. ТРЕК ДУГИ (серый фон)
        # ══════════════════════════════════════════
        track_r = R - 10
        track_width = 18
        p.setPen(QPen(QColor("#2A2A30"), track_width, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                  self.START_ANGLE * 16, self.SWEEP * 16)

        # ══════════════════════════════════════════
        #  5. ЦВЕТНАЯ ДУГА ПРОГРЕССА со свечением
        # ══════════════════════════════════════════
        if self._display_value > 0.1:
            current_angle = self._value_to_angle(self._display_value)
            progress_sweep = current_angle - self.START_ANGLE

            num_seg = 80
            for i in range(num_seg):
                t1 = i / num_seg
                t2 = (i + 1) / num_seg
                if t1 > self._display_value / self.MAX_VALUE:
                    break
                a1 = self.START_ANGLE + t1 * self.SWEEP
                a2 = self.START_ANGLE + t2 * self.SWEEP
                sweep = a2 - a1

                # цвет по зоне
                val_at_seg = t1 * self.MAX_VALUE
                color = self._get_zone_color(val_at_seg)

                # свечение (шире)
                p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 40),
                              track_width + 10, Qt.SolidLine, Qt.RoundCap))
                p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                          int(a1 * 16), int(sweep * 16))

                # основной сегмент
                seg_grad = QLinearGradient(
                    cx + track_r * math.cos(math.radians(a1)),
                    cy - track_r * math.sin(math.radians(a1)),
                    cx + track_r * math.cos(math.radians(a2)),
                    cy - track_r * math.sin(math.radians(a2))
                )
                seg_grad.setColorAt(0.0, color.lighter(115))
                seg_grad.setColorAt(1.0, color)

                p.setPen(QPen(QBrush(seg_grad), track_width,
                              Qt.SolidLine, Qt.RoundCap))
                p.drawArc(QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r),
                          int(a1 * 16), int(sweep * 16))

        # ══════════════════════════════════════════
        #  6. СТРЕЛКА
        # ═════════════════════════════════════════
        angle = self._value_to_angle(self._display_value)
        a_rad = math.radians(angle)
        needle_len = R - 30
        tip_x = cx + needle_len * math.cos(a_rad)
        tip_y = cy - needle_len * math.sin(a_rad)

        perp = a_rad + math.pi / 2
        bw = 3
        tail_len = 18
        tail_x = cx - tail_len * math.cos(a_rad)
        tail_y = cy + tail_len * math.sin(a_rad)

        # тень стрелки
        shadow = QPolygonF([
            QPointF(tip_x + 2, tip_y + 2),
            QPointF(cx + bw * math.cos(perp) + 2, cy - bw * math.sin(perp) + 2),
            QPointF(tail_x + 2, tail_y + 2),
            QPointF(cx - bw * math.cos(perp) + 2, cy + bw * math.sin(perp) + 2),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 80)))
        p.drawPolygon(shadow)

        # стрелка с градиентом
        needle_color = self._get_zone_color(self._display_value)
        needle_grad = QLinearGradient(tail_x, tail_y, tip_x, tip_y)
        needle_grad.setColorAt(0.0, needle_color.darker(120))
        needle_grad.setColorAt(0.5, needle_color)
        needle_grad.setColorAt(1.0, needle_color.lighter(130))

        needle = QPolygonF([
            QPointF(tip_x, tip_y),
            QPointF(cx + bw * math.cos(perp), cy - bw * math.sin(perp)),
            QPointF(tail_x, tail_y),
            QPointF(cx - bw * math.cos(perp), cy + bw * math.sin(perp)),
        ])
        p.setPen(QPen(needle_color.darker(150), 0.5))
        p.setBrush(QBrush(needle_grad))
        p.drawPolygon(needle)

        # ══════════════════════════════════════════
        #  7. ЦЕНТРАЛЬНЫЙ КРУГ СО ЗНАЧЕНИЕМ
        # ══════════════════════════════════════════
        center_r = R * 0.38

        # тень круга
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 60)))
        p.drawEllipse(QPointF(cx + 2, cy + 3), center_r, center_r)

        # градиент круга
        center_grad = QRadialGradient(cx - center_r * 0.3, cy - center_r * 0.3, center_r)
        center_grad.setColorAt(0.0, QColor("#3A3A42"))
        center_grad.setColorAt(0.5, QColor("#2A2A32"))
        center_grad.setColorAt(1.0, QColor("#1A1A22"))
        p.setBrush(QBrush(center_grad))
        p.setPen(QPen(QColor("#444"), 2))
        p.drawEllipse(QPointF(cx, cy), center_r, center_r)

        # внутреннее свечение
        inner_glow = QRadialGradient(cx, cy, center_r * 0.7)
        inner_glow.setColorAt(0.0, QColor(255, 255, 255, 8))
        inner_glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(inner_glow))
        p.drawEllipse(QPointF(cx, cy), center_r - 2, center_r - 2)

        # ══════════════════════════════════════════
        #  8. ЗНАЧЕНИЕ В ЦЕНТРЕ
        # ═════════════════════════════════════════
        # большое число
        p.setFont(QFont("Segoe UI", 42, QFont.Bold))
        value_color = self._get_zone_color(self._display_value)
        p.setPen(QPen(value_color))
        p.drawText(QRectF(0, cy - 35, W, 50),
                   Qt.AlignCenter, f"{self._display_value:.0f}")

        # подпись
        p.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        p.setPen(QColor("#888"))
        p.drawText(QRectF(0, cy + 15, W, 20),
                   Qt.AlignCenter, "из 100")

        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gauge")
        self.setMinimumSize(500, 560)
        self.resize(520, 580)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.gauge = FitnessGauge()
        layout.addWidget(self.gauge, 1)

        # Слайдер
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Значение:"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(65)
        self.slider.valueChanged.connect(self._on_slider)
        slider_layout.addWidget(self.slider)
        self.val_label = QLabel("65")
        self.val_label.setMinimumWidth(35)
        self.val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_layout.addWidget(self.val_label)
        layout.addLayout(slider_layout)

        # Начальное значение с анимацией
        QTimer.singleShot(300, lambda: self._on_slider(65))

    def _on_slider(self, v):
        self.gauge.value = float(v)
        self.val_label.setText(str(v))


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