import sys
import math
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, QColor, QPen, QBrush,
    QFont, QPainterPath, QFontDatabase
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QVariantAnimation, QEasingCurve, Property,
    QPropertyAnimation, Signal
)


# ---------- Палитра (единая для всех приборов) ----------
class Palette:
    BG           = QColor("#0d1117")   # фон окна
    CARD         = QColor("#161b22")   # карточка прибора
    CARD_EDGE    = QColor("#21262d")

    TEXT         = QColor("#e6edf3")
    TEXT_MUTED   = QColor("#7d8590")

    TICK_MAJOR   = QColor("#c9d1d9")
    TICK_MINOR   = QColor("#484f58")

    ACCENT       = QColor("#58a6ff")

    # Жидкость (синяя как на образце)
    LIQ_DARK     = QColor("#0d3a7a")
    LIQ_MID      = QColor("#1f6feb")
    LIQ_LIGHT    = QColor("#79c0ff")
    LIQ_GLOW     = QColor("#cae8ff")

    # Стекло
    GLASS_HI     = QColor(255, 255, 255, 45)   # блик
    GLASS_LO     = QColor(255, 255, 255, 8)
    GLASS_EDGE   = QColor(120, 140, 170, 120)
    GLASS_BG     = QColor(20, 28, 40, 200)


# ---------- Кастомный виджет прибора ----------
class LiquidThermometer(QWidget):
    """
    Современный жидкостный термометр.
    Рисуется целиком через QPainter с настоящими градиентами.
    """

    valueChanged = Signal(float)

    def __init__(self, min_val=0.0, max_val=20.0,
                 major_step=5, minor_step=1,
                 unit="°C", label="ТЕМПЕРАТУРА",
                 parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 540)

        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.major_step = major_step
        self.minor_step = minor_step
        self.unit = unit
        self.label = label

        # ---- Состояние значения + пружинная анимация ----
        self._current = min_val
        self._target = min_val
        self._velocity = 0.0
        self._spring = 0.20
        self._damping = 0.70

        # Анимация через QVariantAnimation
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(self.min_val)
        self._anim.setEndValue(self.min_val)
        self._anim.setDuration(0)
        # Используем QTimer-подобный подход через отдельную анимацию
        # для пружины — через QPropertyAnimation по свойству current
        self._timer_anim = QVariantAnimation(self)
        self._timer_anim.setStartValue(0.0)
        self._timer_anim.setEndValue(1.0)
        self._timer_anim.setDuration(16)  # ~60 FPS
        self._timer_anim.setLoopCount(-1)
        self._timer_anim.valueChanged.connect(self._tick)
        self._timer_anim.start()

        # Геометрия (пересчитывается в paintEvent)
        self._tube_x = 0
        self._tube_w = 0
        self._tube_top = 0
        self._tube_bot = 0
        self._bulb_r = 0
        self._bulb_cy = 0
        self._scale_x = 0

    # ---------- Публичный API ----------
    def set_value(self, v):
        v = max(self.min_val, min(self.max_val, float(v)))
        self._target = v
        self.valueChanged.emit(v)

    def value(self):
        return self._current

    # ---------- Пружинная анимация ----------
    def _tick(self, _):
        diff = self._target - self._current
        self._velocity += diff * self._spring
        self._velocity *= self._damping
        self._current += self._velocity

        if abs(diff) < 0.005 and abs(self._velocity) < 0.005:
            self._current = self._target
            self._velocity = 0.0

        self.update()

    # ---------- Расчёт геометрии ----------
    def _recalc_geometry(self):
        w, h = self.width(), self.height()
        # Центр прибора немного смещаем влево, чтобы справа влезла шкала
        self._tube_x = w * 0.42
        self._tube_w = 26
        self._tube_top = h * 0.12
        self._bulb_r = self._tube_w * 1.7
        self._bulb_cy = h * 0.80
        self._tube_bot = self._bulb_cy - self._bulb_r * 0.4
        self._scale_x = self._tube_x + self._tube_w / 2 + 24

    def resizeEvent(self, event):
        self._recalc_geometry()
        super().resizeEvent(event)

    # ---------- Отрисовка ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        self._recalc_geometry()
        self._draw_card(p)
        self._draw_glass_tube(p)
        self._draw_bulb_glass(p)
        self._draw_liquid(p)
        self._draw_scale(p)
        self._draw_value_text(p)

    # --- Карточка с тенью ---
    def _draw_card(self, p):
        rect = QRectF(10, 10, self.width() - 20, self.height() - 20)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)

        # Тень
        p.save()
        shadow = QPainterPath(path)
        p.translate(0, 4)
        p.fillPath(shadow, QColor(0, 0, 0, 90))
        p.restore()

        # Заливка карточки — вертикальный градиент
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, QColor("#1c222b"))
        grad.setColorAt(1.0, QColor("#12171f"))
        p.fillPath(path, QBrush(grad))

        # Тонкая рамка
        p.setPen(QPen(Palette.CARD_EDGE, 1))
        p.drawPath(path)

    # --- Стеклянный капилляр ---
    def _draw_glass_tube(self, p):
        x = self._tube_x
        w = self._tube_w
        top = self._tube_top
        bot = self._tube_bot
        r = w / 2

        tube_rect = QRectF(x - r, top, w, bot - top)

        # Внешний корпус стекла
        path_outer = QPainterPath()
        path_outer.addRoundedRect(tube_rect, r, r)

        grad = QLinearGradient(tube_rect.topLeft(), tube_rect.topRight())
        grad.setColorAt(0.0, QColor(255, 255, 255, 35))
        grad.setColorAt(0.5, QColor(255, 255, 255, 10))
        grad.setColorAt(1.0, QColor(255, 255, 255, 30))
        p.fillPath(path_outer, QBrush(grad))

        # Внутренняя полость (тёмная)
        inner = tube_rect.adjusted(3, 3, -3, -3)
        path_inner = QPainterPath()
        path_inner.addRoundedRect(inner, r - 3, r - 3)
        p.fillPath(path_inner, QBrush(Palette.GLASS_BG))

        # Блик-полоса слева
        shine_rect = QRectF(x - r + 5, top + 8, 4, bot - top - 16)
        shine = QLinearGradient(shine_rect.topLeft(), shine_rect.bottomLeft())
        shine.setColorAt(0.0, QColor(255, 255, 255, 0))
        shine.setColorAt(0.5, QColor(255, 255, 255, 70))
        shine.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(shine_rect, QBrush(shine))

        # Контур
        p.setPen(QPen(Palette.GLASS_EDGE, 1.2))
        p.drawPath(path_outer)

        # Закругление сверху — усиленный блик
        cap_grad = QRadialGradient(QPointF(x, top + r), r * 1.2)
        cap_grad.setColorAt(0.0, QColor(255, 255, 255, 80))
        cap_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(cap_grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(x, top + r), r, r)

    # --- Колба ---
    def _draw_bulb_glass(self, p):
        cx = self._tube_x
        cy = self._bulb_cy
        r = self._bulb_r

        # Тень под колбой
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(QPointF(cx + 2, cy + 6), r + 2, r + 2)

        # Стеклянная оболочка (внешняя)
        outer = QRadialGradient(QPointF(cx - r * 0.3, cy - r * 0.4), r * 1.4)
        outer.setColorAt(0.0, QColor(255, 255, 255, 60))
        outer.setColorAt(0.7, QColor(255, 255, 255, 12))
        outer.setColorAt(1.0, QColor(255, 255, 255, 35))
        p.setBrush(QBrush(outer))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Внутренняя полость
        inner_r = r - 3
        inner = QRadialGradient(QPointF(cx - inner_r * 0.3, cy - inner_r * 0.4), inner_r * 1.5)
        inner.setColorAt(0.0, QColor(40, 55, 80, 230))
        inner.setColorAt(1.0, QColor(15, 22, 35, 240))
        p.setBrush(QBrush(inner))
        p.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

        # Контур
        p.setPen(QPen(Palette.GLASS_EDGE, 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

    # --- Жидкость (столбик + заливка колбы) ---
    def _draw_liquid(self, p):
        x = self._tube_x
        r = self._tube_w / 2 - 3
        top = self._tube_top + 6
        bot = self._tube_bot
        cy = self._bulb_cy
        br = self._bulb_r - 3

        # Y для текущего значения
        val = self._current
        frac = (val - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        y_liq = bot - frac * (bot - top)

        p.setPen(Qt.NoPen)

        # --- Заливка колбы ---
        bulb_grad = QRadialGradient(QPointF(x - br * 0.35, cy - br * 0.45), br * 1.6)
        bulb_grad.setColorAt(0.0, Palette.LIQ_LIGHT)
        bulb_grad.setColorAt(0.6, Palette.LIQ_MID)
        bulb_grad.setColorAt(1.0, Palette.LIQ_DARK)
        p.setBrush(QBrush(bulb_grad))
        p.drawEllipse(QPointF(x, cy), br, br)

        # Блик на колбе
        p.setBrush(QColor(255, 255, 255, 110))
        p.drawEllipse(QPointF(x - br * 0.35, cy - br * 0.45), br * 0.28, br * 0.22)

        # Маленькая искорка
        p.setBrush(QColor(255, 255, 255, 180))
        p.drawEllipse(QPointF(x - br * 0.42, cy - br * 0.52), br * 0.10, br * 0.08)

        # --- Столбик жидкости ---
        if y_liq < bot:
            rect = QRectF(x - r, y_liq, r * 2, bot - y_liq)

            # Градиент по вертикали: сверху светлый, снизу тёмный
            g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            g.setColorAt(0.0, Palette.LIQ_LIGHT)
            g.setColorAt(0.15, Palette.LIQ_MID)
            g.setColorAt(1.0, Palette.LIQ_DARK)

            path = QPainterPath()
            # Скругление только сверху
            path.addRoundedRect(rect, r, r)
            # Нижнюю половину закругляем в обратную сторону, чтобы переход к колбе был плавным
            p.fillPath(path, QBrush(g))

            # Блик по левому краю столбика
            shine = QLinearGradient(QPointF(x - r, 0), QPointF(x + r, 0))
            shine.setColorAt(0.0, QColor(255, 255, 255, 0))
            shine.setColorAt(0.25, QColor(255, 255, 255, 90))
            shine.setColorAt(0.45, QColor(255, 255, 255, 0))
            shine.setColorAt(1.0, QColor(0, 0, 0, 40))
            p.fillRect(QRectF(x - r, y_liq, r * 2, bot - y_liq), QBrush(shine))

            # Мениск сверху (светлая точка)
            p.setBrush(QColor(255, 255, 255, 160))
            p.drawEllipse(QPointF(x, y_liq + 3), r * 0.55, 2.2)

    # --- Шкала ---
    def _draw_scale(self, p):
        x = self._scale_x
        top = self._tube_top + 6
        bot = self._tube_bot

        # Мелкие риски
        n_minor = int(round((self.max_val - self.min_val) / self.minor_step))
        p.setPen(QPen(Palette.TICK_MINOR, 1))
        for i in range(n_minor + 1):
            val = self.min_val + i * self.minor_step
            if abs(val % self.major_step) < 1e-6:
                continue
            y = self._value_to_y(val, top, bot)
            p.drawLine(QPointF(x, y), QPointF(x + 8, y))

        # Крупные риски + цифры
        n_major = int(round((self.max_val - self.min_val) / self.major_step))
        font_num = QFont("Segoe UI", 13, QFont.DemiBold)
        p.setFont(font_num)
        for i in range(n_major + 1):
            val = self.min_val + i * self.major_step
            y = self._value_to_y(val, top, bot)

            p.setPen(QPen(Palette.TICK_MAJOR, 2))
            p.drawLine(QPointF(x, y), QPointF(x + 16, y))

            p.setPen(QPen(Palette.TEXT))
            p.drawText(QRectF(x + 24, y - 12, 60, 24),
                       Qt.AlignVCenter | Qt.AlignLeft,
                       f"{int(val)}")

        # °C рядом с верхом шкалы
        p.setPen(QPen(Palette.TEXT_MUTED))
        p.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        p.drawText(QRectF(x + 24, top - 34, 60, 20),
                   Qt.AlignVCenter | Qt.AlignLeft, self.unit)

    # --- Крупное значение и подпись ---
    def _draw_value_text(self, p):
        w = self.width()
        # Подпись сверху
        p.setPen(QPen(Palette.TEXT_MUTED))
        p.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        p.drawText(QRectF(0, 24, w, 22),
                   Qt.AlignHCenter | Qt.AlignVCenter,
                   self.label)

        # Значение снизу
        p.setPen(QPen(Palette.ACCENT))
        p.setFont(QFont("Segoe UI", 24, QFont.Bold))
        p.drawText(QRectF(0, self.height() - 60, w, 40),
                   Qt.AlignHCenter | Qt.AlignVCenter,
                   f"{self._current:.1f} {self.unit}")

    def _value_to_y(self, value, top, bot):
        frac = (value - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        return bot - frac * (bot - top)


# ---------- Кнопка-пресет с hover и press ----------
class PresetButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setMinimumWidth(96)
        self.setStyleSheet("""
            QPushButton {
                background-color: #1c222b;
                color: #e6edf3;
                border: 1px solid #2a313b;
                border-radius: 10px;
                padding: 8px 16px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #232b36;
                border-color: #3a4452;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
        """)


# ---------- Демо-окно ----------
class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Шкала 2")
        self.setStyleSheet("background-color: #0d1117;")
        self.setFixedSize(560, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Прибор
        self.thermo = LiquidThermometer(min_val=0, max_val=20,
                                        major_step=5, minor_step=1,
                                        unit="°C", label="ТЕМПЕРАТУРА")
        root.addWidget(self.thermo, 1)

        # Панель кнопок
        btns = QHBoxLayout()
        btns.setContentsMargins(20, 10, 20, 24)
        btns.setSpacing(10)
        for label, val in [("0 °C", 0), ("5 °C", 5), ("10 °C", 10),
                           ("15 °C", 15), ("20 °C", 20)]:
            b = PresetButton(label)
            b.clicked.connect(lambda _, v=val: self.thermo.set_value(v))
            btns.addWidget(b)

        # Кнопка «Случайно»
        b_rand = PresetButton("Случайно")
        b_rand.clicked.connect(self._random)
        btns.addWidget(b_rand)

        container = QWidget()
        container.setLayout(btns)
        root.addWidget(container)

    def _random(self):
        import random
        self.thermo.set_value(random.uniform(0, 20))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = DemoWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()