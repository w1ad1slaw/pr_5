import sys
import math
import random
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, QColor, QPen, QBrush,
    QFont, QPainterPath, QConicalGradient
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QVariantAnimation, QTimer, Signal
)


# ============================================================
# КОНФИГУРАЦИИ ЦВЕТОВ (по мотивам образца)
# ============================================================
class LiquidTheme:
    def __init__(self, name, liquid, liquid_dark, liquid_light,
                 bg_top, bg_bottom, arc_color, text_color):
        self.name = name
        self.liquid = QColor(liquid)
        self.liquid_dark = QColor(liquid_dark)
        self.liquid_light = QColor(liquid_light)
        self.bg_top = QColor(bg_top)
        self.bg_bottom = QColor(bg_bottom)
        self.arc_color = QColor(arc_color)
        self.text_color = QColor(text_color)


THEME_BLUE = LiquidTheme(
    "blue",
    liquid="#2c3e50", liquid_dark="#1a2530", liquid_light="#3a5068",
    bg_top="#2c3e50", bg_bottom="#1a2530",
    arc_color="#4fc3f7", text_color="#ffffff"
)

THEME_GREEN = LiquidTheme(
    "green",
    liquid="#1abc7c", liquid_dark="#0d8a56", liquid_light="#3fe0a0",
    bg_top="#2c3e50", bg_bottom="#1a2530",
    arc_color="#1abc7c", text_color="#ffffff"
)

THEME_CYAN = LiquidTheme(
    "cyan",
    liquid="#26d0e0", liquid_dark="#0fa8b8", liquid_light="#6ff0ff",
    bg_top="#2c3e50", bg_bottom="#1a2530",
    arc_color="#26d0e0", text_color="#ffffff"
)

THEME_RED = LiquidTheme(
    "red",
    liquid="#e53935", liquid_dark="#b71c1c", liquid_light="#ff6f60",
    bg_top="#2c3e50", bg_bottom="#1a2530",
    arc_color="#e53935", text_color="#ffffff"
)


# ============================================================
# ВИДЖЕТ: ИНДИКАТОР УРОВНЯ ЖИДКОСТИ
# ============================================================
class LiquidLevelGauge(QWidget):
    """
    Круглый индикатор уровня жидкости.

    Режимы:
        "arc"  — кольцевая дуга вокруг круга (вариант 1)
        "fill" — прямая горизонтальная заливка (вариант 2)
        "wave" — волнистая заливка (вариант 3)

    Сигналы:
        valueChanged(float)
    """

    valueChanged = Signal(float)

    def __init__(self, min_val=0, max_val=100, value=0,
                 style="wave", theme=THEME_BLUE,
                 show_text=True, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self.setMouseTracking(True)

        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self._current = float(value)
        self._target = float(value)
        self._velocity = 0.0
        self._spring = 0.20
        self._damping = 0.70

        self.style = style
        self.theme = theme
        self.show_text = show_text

        # Фаза волны (для анимации)
        self._wave_phase = 0.0
        self._hover = False

        # Пружина
        self._timer = QVariantAnimation(self)
        self._timer.setStartValue(0.0)
        self._timer.setEndValue(1.0)
        self._timer.setDuration(16)
        self._timer.setLoopCount(-1)
        self._timer.valueChanged.connect(self._tick)
        self._timer.start()

    # ---------- API ----------
    def set_value(self, v):
        v = max(self.min_val, min(self.max_val, float(v)))
        self._target = v
        self.valueChanged.emit(v)

    def value(self):
        return self._current

    def set_style(self, style):
        self.style = style
        self.update()

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    # ---------- Анимация ----------
    def _tick(self, _):
        # Пружина к цели
        diff = self._target - self._current
        self._velocity += diff * self._spring
        self._velocity *= self._damping
        self._current += self._velocity
        if abs(diff) < 0.005 and abs(self._velocity) < 0.005:
            self._current = self._target
            self._velocity = 0.0

        # Фаза волны — непрерывно движется
        self._wave_phase += 0.08
        if self._wave_phase > math.tau:
            self._wave_phase -= math.tau

        self.update()

    # ---------- Геометрия ----------
    def _geom(self):
        w, h = self.width(), self.height()
        size = min(w, h)
        cx, cy = w / 2, h / 2
        radius = size / 2 - 14
        return cx, cy, radius

    # ---------- Отрисовка ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        cx, cy, radius = self._geom()
        t = self.theme

        # 1. Фон круга
        self._draw_background(p, cx, cy, radius, t)

        # 2. Содержимое — в зависимости от стиля
        if self.style == "arc":
            self._draw_arc(p, cx, cy, radius, t)
        else:
            # Заливка и волна обрезаются по кругу
            p.save()
            clip = QPainterPath()
            clip.addEllipse(QPointF(cx, cy), radius, radius)
            p.setClipPath(clip)

            if self.style == "wave":
                self._draw_wave_fill(p, cx, cy, radius, t)
            else:  # "fill"
                self._draw_flat_fill(p, cx, cy, radius, t)

            p.restore()

        # 3. Ободок круга
        p.setPen(QPen(QColor(0, 0, 0, 80), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), radius, radius)

        # 4. Hover-подсветка
        if self._hover:
            p.setPen(QPen(t.arc_color, 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), radius + 3, radius + 3)

        # 5. Текст
        if self.show_text:
            self._draw_text(p, cx, cy, radius)

    # --- Фон ---
    def _draw_background(self, p, cx, cy, radius, t):
        grad = QRadialGradient(QPointF(cx - radius * 0.3, cy - radius * 0.4), radius * 1.4)
        grad.setColorAt(0.0, t.bg_top)
        grad.setColorAt(1.0, t.bg_bottom)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), radius, radius)

        # Мягкий верхний блик
        p.setBrush(QColor(255, 255, 255, 10))
        p.drawEllipse(QPointF(cx, cy - radius * 0.35), radius * 0.6, radius * 0.35)

    # --- Стиль 1: кольцевая дуга ---
    def _draw_arc(self, p, cx, cy, radius, t):
        # Серый фон кольца
        ring_pen = QPen(QColor(255, 255, 255, 30), 6, Qt.SolidLine, Qt.RoundCap)
        arc_rect = QRectF(cx - radius + 6, cy - radius + 6,
                          (radius - 6) * 2, (radius - 6) * 2)
        p.setPen(ring_pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(arc_rect, 0, 360 * 16)

        # Цветная дуга — снизу, по часовой
        frac = (self._current - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        frac = max(0.0, min(1.0, frac))
        span = int(360 * frac * 16)

        # Градиент по дуге (ConicalGradient)
        grad = QConicalGradient(QPointF(cx, cy), 90)
        grad.setColorAt(0.0, t.arc_color.lighter(130))
        grad.setColorAt(1.0, t.arc_color.darker(120))

        arc_pen = QPen(QBrush(grad), 6, Qt.SolidLine, Qt.RoundCap)
        p.setPen(arc_pen)
        p.drawArc(arc_rect, 90 * 16, -span)   # от 90° (снизу) против часовой

    # --- Стиль 2: прямая горизонтальная заливка ---
    def _draw_flat_fill(self, p, cx, cy, radius, t):
        frac = (self._current - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        frac = max(0.0, min(1.0, frac))

        # Y уровня жидкости (от верха круга вниз)
        top_y = cy - radius
        bottom_y = cy + radius
        level_y = bottom_y - (bottom_y - top_y) * frac

        # Прямоугольник заливки (внутри клипа круга)
        rect = QRectF(cx - radius, level_y, radius * 2, bottom_y - level_y)

        # Вертикальный градиент жидкости
        grad = QLinearGradient(QPointF(cx, level_y), QPointF(cx, bottom_y))
        grad.setColorAt(0.0, t.liquid_light)
        grad.setColorAt(0.5, t.liquid)
        grad.setColorAt(1.0, t.liquid_dark)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRect(rect)

        # Тонкая светлая линия на поверхности (эффект мениска)
        p.setPen(QPen(t.liquid_light, 2))
        p.drawLine(QPointF(cx - radius, level_y), QPointF(cx + radius, level_y))

    # --- Стиль 3: волнистая заливка ---
    def _draw_wave_fill(self, p, cx, cy, radius, t):
        frac = (self._current - self.min_val) / (self.max_val - self.min_val) if self.max_val > self.min_val else 0
        frac = max(0.0, min(1.0, frac))

        top_y = cy - radius
        bottom_y = cy + radius
        level_y = bottom_y - (bottom_y - top_y) * frac

        # Строим путь: верх — синусоида, низ — прямой
        path = QPainterPath()
        path.moveTo(cx - radius, level_y)

        # Параметры волны
        wave_h = 6                # высота волны
        wave_count = 1.5          # сколько полных волн по диаметру
        steps = 48

        for i in range(steps + 1):
            x = cx - radius + (radius * 2) * (i / steps)
            # Две наложенные синусоиды для естественности
            u = (x - cx) / radius
            y_off = wave_h * math.sin(u * math.pi * wave_count + self._wave_phase)
            y_off += wave_h * 0.4 * math.sin(u * math.pi * wave_count * 2 + self._wave_phase * 1.7)
            path.lineTo(x, level_y + y_off)

        # Замыкаем вниз
        path.lineTo(cx + radius, bottom_y)
        path.lineTo(cx - radius, bottom_y)
        path.closeSubpath()

        # Градиент жидкости
        grad = QLinearGradient(QPointF(cx, level_y), QPointF(cx, bottom_y))
        grad.setColorAt(0.0, t.liquid_light)
        grad.setColorAt(0.5, t.liquid)
        grad.setColorAt(1.0, t.liquid_dark)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # Светлая кромка волны
        p.setPen(QPen(t.liquid_light, 1.5))
        p.setBrush(Qt.NoBrush)
        wave_path = QPainterPath()
        for i in range(steps + 1):
            x = cx - radius + (radius * 2) * (i / steps)
            u = (x - cx) / radius
            y_off = wave_h * math.sin(u * math.pi * wave_count + self._wave_phase)
            y_off += wave_h * 0.4 * math.sin(u * math.pi * wave_count * 2 + self._wave_phase * 1.7)
            if i == 0:
                wave_path.moveTo(x, level_y + y_off)
            else:
                wave_path.lineTo(x, level_y + y_off)
        p.drawPath(wave_path)

    # --- Текст в центре ---
    def _draw_text(self, p, cx, cy, radius):
        val = self._current
        # Если диапазон 0..100 — выводим с процентом
        if abs(self.min_val) < 1e-6 and abs(self.max_val - 100) < 1e-6:
            text = f"{val:.0f}%"
        else:
            text = f"{val:.1f}"

        # Тень текста
        p.setPen(QPen(QColor(0, 0, 0, 120)))
        font = QFont("Segoe UI", int(radius * 0.32), QFont.Bold)
        p.setFont(font)
        p.drawText(QRectF(cx - radius, cy - radius * 0.5 + 2, radius * 2, radius),
                   Qt.AlignCenter, text)

        # Основной текст
        p.setPen(QPen(self.theme.text_color))
        p.drawText(QRectF(cx - radius, cy - radius * 0.5, radius * 2, radius),
                   Qt.AlignCenter, text)

    # ---------- Интерактивность ----------
    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        cx, cy, radius = self._geom()
        dx = event.position().x() - cx
        dy = event.position().y() - cy
        if math.hypot(dx, dy) <= radius:
            # Преобразуем Y в значение
            top_y = cy - radius
            bottom_y = cy + radius
            frac = (bottom_y - event.position().y()) / (bottom_y - top_y)
            frac = max(0.0, min(1.0, frac))
            val = self.min_val + frac * (self.max_val - self.min_val)
            self.set_value(val)


# ============================================================
# ДЕМО-ОКНО
# ============================================================
class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Шкала 6 — Анимация уровня жидкостей")
        self.setStyleSheet("background-color: #0d1117;")

        # --- Резиновое окно ---
        self.setMinimumSize(640, 480)
        self.resize(1100, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # Заголовок
        title = QLabel("Анимация уровня жидкостей")
        title.setStyleSheet(
            "color: #e6edf3; font-family: 'Segoe UI'; "
            "font-size: 16px; font-weight: 700;"
        )
        root.addWidget(title)

        sub = QLabel("Три стиля (arc / fill / wave) и четыре цвета. "
                     "Клик по кругу устанавливает уровень. Волна анимирована.")
        sub.setStyleSheet("color: #7d8590; font-family: 'Segoe UI'; font-size: 11px;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        # Первый ряд — три стиля
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        self.g_arc   = self._make_gauge("arc",  THEME_BLUE,  "Кольцевая дуга")
        self.g_fill  = self._make_gauge("fill", THEME_GREEN, "Прямая заливка")
        self.g_wave  = self._make_gauge("wave", THEME_CYAN,  "Волнистая заливка")
        row1.addLayout(self.g_arc[0], 1)
        row1.addLayout(self.g_fill[0], 1)
        row1.addLayout(self.g_wave[0], 1)
        root.addLayout(row1, 1)

        # Второй ряд — два цвета
        row2 = QHBoxLayout()
        row2.setSpacing(20)
        self.g_red    = self._make_gauge("fill", THEME_RED,   "Красный (fill)")
        self.g_green2 = self._make_gauge("wave", THEME_GREEN, "Зелёный (wave)")
        row2.addLayout(self.g_red[0], 1)
        row2.addLayout(self.g_green2[0], 1)
        row2.addStretch(1)
        root.addLayout(row2, 1)

        # Все приборы
        self.all_gauges = [self.g_arc[1], self.g_fill[1], self.g_wave[1],
                           self.g_red[1], self.g_green2[1]]
        for g in self.all_gauges:
            g.set_value(65)

        # --- Кнопки ---
        btns = QHBoxLayout()
        btns.setSpacing(8)

        self.btn_widgets = []
        for lbl, v in [("0%", 0), ("25%", 25), ("50%", 50),
                       ("65%", 65), ("80%", 80), ("100%", 100)]:
            b = QPushButton(lbl)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(40)
            b.setMinimumWidth(70)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #1c222b; color: #e6edf3;
                    border: 1px solid #2a313b; border-radius: 10px;
                    padding: 8px 16px;
                    font-family: 'Segoe UI'; font-size: 13px; font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #232b36;
                    border-color: #58a6ff;
                    color: #58a6ff;
                }
                QPushButton:pressed {
                    background-color: #0d1117;
                    border-color: #1f6feb;
                }
            """)
            b.clicked.connect(lambda _, val=v: self._on_preset(val))
            btns.addWidget(b)
            self.btn_widgets.append(b)

        # Кнопка «Случайно»
        b_rand = QPushButton("Случайно")
        b_rand.setCursor(Qt.PointingHandCursor)
        b_rand.setFixedHeight(40)
        b_rand.setMinimumWidth(110)
        b_rand.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb; color: #ffffff;
                border: none; border-radius: 10px;
                padding: 8px 16px;
                font-family: 'Segoe UI'; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background-color: #388bfd; }
            QPushButton:pressed { background-color: #1158c7; }
        """)
        b_rand.clicked.connect(self._on_random)
        btns.addWidget(b_rand)

        # Кнопка «Авто» (пауза/возобновление)
        self.btn_auto = QPushButton("Авто: вкл")
        self.btn_auto.setCheckable(True)
        self.btn_auto.setChecked(True)
        self.btn_auto.setCursor(Qt.PointingHandCursor)
        self.btn_auto.setFixedHeight(40)
        self.btn_auto.setMinimumWidth(110)
        self.btn_auto.setStyleSheet("""
            QPushButton {
                background-color: #1c222b; color: #e6edf3;
                border: 1px solid #2a313b; border-radius: 10px;
                padding: 8px 16px;
                font-family: 'Segoe UI'; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #232b36; border-color: #58a6ff; }
            QPushButton:checked {
                background-color: #238636; color: #ffffff;
                border: 1px solid #2ea043;
            }
        """)
        self.btn_auto.clicked.connect(self._toggle_auto)
        btns.addWidget(self.btn_auto)

        btns.addStretch(1)
        root.addLayout(btns)

        # Статусная строка
        self.status = QLabel("Уровень: 65%")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(
            "color: #58a6ff; font-family: 'Consolas'; "
            "font-size: 13px; font-weight: 600; "
            "background-color: #161b22; padding: 10px; "
            "border-radius: 8px; border: 1px solid #2a313b;"
        )
        root.addWidget(self.status)

        # --- Автотаймер (отдельно управляемый) ---
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_tick)
        self.auto_timer.start(2500)

    # ---------- Слоты ----------
    def _make_gauge(self, style, theme, label_text):
        col = QVBoxLayout()
        col.setSpacing(6)
        g = LiquidLevelGauge(style=style, theme=theme, value=65)
        col.addWidget(g, 1)
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "color: #7d8590; font-family: 'Segoe UI'; "
            "font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        col.addWidget(lbl)
        return col, g

    def _set_all(self, val):
        for g in self.all_gauges:
            g.set_value(val)
        self.status.setText(f"Уровень: {val:.0f}%")

    def _on_preset(self, val):
        # Немедленно выставляем значение
        self._set_all(val)
        # Пользователь взял управление — приостанавливаем авто
        if self.btn_auto.isChecked():
            self.btn_auto.setChecked(False)
            self.btn_auto.setText("Авто: выкл")
            self.auto_timer.stop()

    def _on_random(self):
        self._set_all(random.uniform(0, 100))

    def _toggle_auto(self):
        if self.btn_auto.isChecked():
            self.btn_auto.setText("Авто: вкл")
            self.auto_timer.start(2500)
        else:
            self.btn_auto.setText("Авто: выкл")
            self.auto_timer.stop()

    def _auto_tick(self):
        self._set_all(random.uniform(10, 90))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = DemoWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()