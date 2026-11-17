import tkinter as tk
import math
import random


# ---------- Цветовая палитра (тёмная тема) ----------
class Palette:
    BG_DARK      = '#0f1419'   # фон окна
    BG_CARD      = '#1a2028'   # карточка прибора
    BG_RING      = '#242d38'   # внешнее кольцо
    BG_FACE      = '#151b22'   # лицо шкалы
    TEXT_PRIMARY = '#e8eef5'   # основной текст
    TEXT_MUTED   = '#7a8899'   # второстепенный текст
    TICK_MAJOR   = '#c8d4e0'   # крупные риски
    TICK_MINOR   = '#3a4552'   # мелкие риски
    NEEDLE       = '#ff4757'   # стрелка
    NEEDLE_GLOW  = '#ff6b7a'   # свечение стрелки
    HUB          = '#2c3644'   # шарнир
    HUB_EDGE     = '#4a5568'   # окантовка шарнира
    ACCENT       = '#4fc3f7'   # акцент (кнопки, значения)
    BTN_BG       = '#242d38'
    BTN_BG_HOVER = '#2e3947'
    BTN_BORDER   = '#3a4552'

    # Цветовые зоны (cold → hot)
    ZONE_COLD    = '#4a90e2'   # синий
    ZONE_COMFORT = '#2ecc71'   # зелёный
    ZONE_WARM    = '#f39c12'   # оранжевый
    ZONE_HOT     = '#e74c3c'   # красный


class Gauge(tk.Canvas):
    """
    Базовый класс аналоговой шкалы с современным дизайном.
    Включает: цветовые зоны, плавную анимацию с easing,
    интерактивное перетаскивание стрелки, hover-эффекты.
    """

    def __init__(self, parent, min_val, max_val, size=380,
                 start_angle=135, arc_range=270,
                 major_step=10, minor_step=2,
                 unit='', label='',
                 zones=None,
                 palette=Palette,
                 **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=palette.BG_DARK, highlightthickness=0, **kwargs)

        self.palette = palette
        self.size = size
        self.min_val = min_val
        self.max_val = max_val
        self.center = size / 2
        self.radius = size / 2 - 30

        self.start_angle = start_angle
        self.arc_range = arc_range
        self.major_step = major_step
        self.minor_step = minor_step
        self.unit = unit
        self.label = label

        # Цветовые зоны: [(от, до, цвет), ...]
        self.zones = zones or []

        # Анимация с easing
        self.current_value = min_val
        self.target_value = min_val
        self.velocity = 0.0
        self.SPRING = 0.18       # жёсткость пружины
        self.DAMPING = 0.72      # затухание

        # Пульсация шарнира при изменении
        self.pulse = 0.0

        # Интерактивность
        self.dragging = False

        # Отрисовка
        self.draw_card()
        self.draw_face()
        self.draw_zones()
        self.draw_scale()
        self.draw_value_text()
        self.create_needle()

        # Привязка событий мыши
        self.bind('<Button-1>', self.on_press)
        self.bind('<B1-Motion>', self.on_drag)
        self.bind('<ButtonRelease-1>', self.on_release)

        # Цикл анимации
        self.animate()

    # ============ Отрисовка ============

    def draw_card(self):
        """Внешняя карточка с тенью."""
        s = self.size
        # Тень (смещённый тёмный круг)
        self.create_oval(8, 12, s-4, s-4, fill='#0a0e13', outline='')
        # Корпус
        self.create_oval(4, 4, s-8, s-8,
                         fill=self.palette.BG_CARD, outline='#2a3441', width=2)
        # Внутреннее кольцо
        self.create_oval(16, 16, s-20, s-20,
                         fill=self.palette.BG_RING, outline='')

    def draw_face(self):
        """Лицо шкалы."""
        s = self.size
        # Внутренний круг шкалы
        self.create_oval(26, 26, s-30, s-30,
                         fill=self.palette.BG_FACE, outline='#2a3441', width=1)
        # Верхний блик (мягкий)
        self.create_arc(30, 30, s-34, s-34,
                        start=40, extent=100, style=tk.ARC,
                        outline='#1e2733', width=8)

    def draw_zones(self):
        """Цветные зоны на дуге."""
        if not self.zones:
            return
        s = self.size
        r = self.radius - 2
        # Tkinter рисует arc против часовой, а наши углы — по часовой,
        # поэтому extent берём с минусом и стартуем с конца зоны.
        for (z_from, z_to, color) in self.zones:
            f1 = (z_from - self.min_val) / (self.max_val - self.min_val)
            f2 = (z_to - self.min_val) / (self.max_val - self.min_val)
            a1 = self.start_angle + self.arc_range * f1
            a2 = self.start_angle + self.arc_range * f2
            # Tkinter angle: 0° — справа, против часовой.
            # Наш угол — по часовой от положительной оси X.
            tk_start = -a2
            tk_extent = a2 - a1
            self.create_arc(
                self.center - r, self.center - r,
                self.center + r, self.center + r,
                start=tk_start, extent=tk_extent,
                style=tk.ARC, outline=color, width=8
            )

    def draw_scale(self):
        """Риски-точки и цифры."""
        # Мелкие риски (точки)
        minor_count = int((self.max_val - self.min_val) / self.minor_step)
        for i in range(minor_count + 1):
            val = self.min_val + i * self.minor_step
            fraction = (val - self.min_val) / (self.max_val - self.min_val)
            angle_deg = self.start_angle + self.arc_range * fraction
            angle_rad = math.radians(angle_deg)
            # Точки на дуге (внутри зоны)
            r = self.radius - 14
            x = self.center + r * math.cos(angle_rad)
            y = self.center + r * math.sin(angle_rad)
            if val % self.major_step != 0:
                self.create_oval(x-1, y-1, x+1, y+1,
                                 fill=self.palette.TICK_MINOR, outline='')

        # Крупные риски и цифры
        major_count = int((self.max_val - self.min_val) / self.major_step)
        for i in range(major_count + 1):
            val = self.min_val + i * self.major_step
            fraction = (val - self.min_val) / (self.max_val - self.min_val)
            angle_deg = self.start_angle + self.arc_range * fraction
            angle_rad = math.radians(angle_deg)

            # Крупная риска
            x1 = self.center + (self.radius - 6) * math.cos(angle_rad)
            y1 = self.center + (self.radius - 6) * math.sin(angle_rad)
            x2 = self.center + (self.radius - 22) * math.cos(angle_rad)
            y2 = self.center + (self.radius - 22) * math.sin(angle_rad)
            self.create_line(x1, y1, x2, y2,
                             width=2, fill=self.palette.TICK_MAJOR,
                             capstyle=tk.ROUND)

            # Цифра
            tx = self.center + (self.radius - 48) * math.cos(angle_rad)
            ty = self.center + (self.radius - 48) * math.sin(angle_rad)
            self.create_text(tx, ty, text=str(int(val)),
                             font=("Segoe UI", 14, "bold"),
                             fill=self.palette.TEXT_PRIMARY)

        # Подпись единицы измерения
        if self.unit:
            self.create_text(self.center - 70, self.center + 90,
                             text=self.unit,
                             font=("Segoe UI", 22, "bold"),
                             fill=self.palette.TEXT_MUTED)

        # Название прибора сверху
        if self.label:
            self.create_text(self.center, 60,
                             text=self.label.upper(),
                             font=("Segoe UI", 11),
                             fill=self.palette.TEXT_MUTED)

    def draw_value_text(self):
        """Крупное числовое значение внизу — видимость состояния."""
        self.value_text = self.create_text(
            self.center, self.center + 75,
            text=f"{self.min_val:.0f}",
            font=("Segoe UI", 26, "bold"),
            fill=self.palette.ACCENT
        )

    def create_needle(self):
        """Стрелка с тенью, шарнир с окантовкой."""
        # Тень стрелки (смещена вправо-вниз)
        self.needle_shadow = self.create_line(
            self.center + 2, self.center + 2,
            self.center + 2, self.center + 2,
            width=5, fill='#000000', capstyle=tk.ROUND
        )
        # Стрелка
        self.needle = self.create_line(
            self.center, self.center,
            self.center, self.center - self.radius + 30,
            width=4, fill=self.palette.NEEDLE,
            arrow=tk.LAST, arrowshape=(18, 22, 7),
            capstyle=tk.ROUND
        )
        # Шарнир (внешнее кольцо)
        r = 15
        self.hub_outer = self.create_oval(
            self.center - r, self.center - r,
            self.center + r, self.center + r,
            fill=self.palette.HUB_EDGE, outline=''
        )
        # Шарнир (внутренний круг)
        r2 = 11
        self.hub_inner = self.create_oval(
            self.center - r2, self.center - r2,
            self.center + r2, self.center + r2,
            fill=self.palette.HUB, outline=''
        )

    # ============ Логика ============

    def set_value(self, value):
        """Установить целевое значение (стрелка плавно дойдёт)."""
        new_val = max(self.min_val, min(value, self.max_val))
        if abs(new_val - self.target_value) > 0.01:
            self.pulse = 1.0    # запуск пульсации
        self.target_value = new_val

    def value_to_angle(self, value):
        fraction = (value - self.min_val) / (self.max_val - self.min_val)
        return self.start_angle + self.arc_range * fraction

    def angle_to_value(self, x, y):
        """Обратное преобразование для интерактивного перетаскивания."""
        dx = x - self.center
        dy = y - self.center
        angle = math.degrees(math.atan2(dy, dx))    # -180…180, по часовой
        # Приводим к нашему диапазону (start_angle … start_angle + arc_range)
        while angle < self.start_angle - 180:
            angle += 360
        while angle > self.start_angle + 180:
            angle -= 360
        fraction = (angle - self.start_angle) / self.arc_range
        fraction = max(0.0, min(1.0, fraction))
        return self.min_val + fraction * (self.max_val - self.min_val)

    def animate(self):
        """Пружинная анимация с затуханием (easing)."""
        diff = self.target_value - self.current_value
        # Пружина
        self.velocity += diff * self.SPRING
        self.velocity *= self.DAMPING
        self.current_value += self.velocity

        # Останавливаемся, когда почти достигли цели
        if abs(diff) < 0.02 and abs(self.velocity) < 0.02:
            self.current_value = self.target_value
            self.velocity = 0.0

        # Пересчёт положения стрелки
        angle_rad = math.radians(self.value_to_angle(self.current_value))
        x = self.center + (self.radius - 32) * math.cos(angle_rad)
        y = self.center + (self.radius - 32) * math.sin(angle_rad)

        self.coords(self.needle,
                    self.center, self.center, x, y)
        self.coords(self.needle_shadow,
                    self.center + 2, self.center + 2, x + 2, y + 2)

        # Обновление текста значения
        self.itemconfig(self.value_text,
                        text=f"{self.current_value:.1f}")

        # Пульсация шарнира
        if self.pulse > 0.01:
            r = 15 + self.pulse * 4
            self.coords(self.hub_outer,
                        self.center - r, self.center - r,
                        self.center + r, self.center + r)
            self.pulse *= 0.85
        elif self.pulse != 0:
            self.pulse = 0.0
            self.coords(self.hub_outer,
                        self.center - 15, self.center - 15,
                        self.center + 15, self.center + 15)

        self.after(16, self.animate)   # ~60 FPS

    # ============ Интерактивность ============

    def on_press(self, event):
        # Проверяем, что клик рядом со стрелкой (в пределах большого круга)
        dx = event.x - self.center
        dy = event.y - self.center
        if math.hypot(dx, dy) <= self.radius:
            self.dragging = True
            self.target_value = self.angle_to_value(event.x, event.y)
            self.current_value = self.target_value
            self.velocity = 0.0
            self.pulse = 1.0

    def on_drag(self, event):
        if not self.dragging:
            return
        self.target_value = self.angle_to_value(event.x, event.y)
        self.current_value = self.target_value
        self.velocity = 0.0
        self.pulse = 0.8

    def on_release(self, event):
        self.dragging = False


# ---------- Классы конкретных шкал ----------

class Thermometer(Gauge):
    """Шкала 1"""
    def __init__(self, parent, size=380, **kwargs):
        zones = [
            (0,  15, Palette.ZONE_COLD),      # холодно
            (15, 28, Palette.ZONE_COMFORT),   # комфортно
            (28, 38, Palette.ZONE_WARM),      # тепло
            (38, 50, Palette.ZONE_HOT),       # жарко
        ]
        super().__init__(
            parent,
            min_val=0, max_val=50,
            size=size,
            start_angle=135, arc_range=270,
            major_step=10, minor_step=2,
            unit='°C',
            label='Температура',
            zones=zones,
            **kwargs
        )


# ---------- Кнопка с hover-эффектом ----------

class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, width=110, height=42,
                 palette=Palette):
        super().__init__(parent, width=width, height=height,
                         bg=palette.BG_DARK, highlightthickness=0)
        self.palette = palette
        self.command = command
        self.w = width
        self.h = height
        self.text = text

        self.bg_rect = self.create_rectangle(
            2, 2, width-2, height-2,
            fill=palette.BTN_BG, outline=palette.BTN_BORDER, width=1
        )
        self.label = self.create_text(
            width/2, height/2, text=text,
            font=("Segoe UI", 11, "bold"),
            fill=palette.TEXT_PRIMARY
        )

        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Button-1>', self.on_click)

    def on_enter(self, event):
        self.itemconfig(self.bg_rect, fill=self.palette.BTN_BG_HOVER)

    def on_leave(self, event):
        self.itemconfig(self.bg_rect, fill=self.palette.BTN_BG)

    def on_click(self, event):
        self.command()


# ---------- Демонстрационное окно ----------

class DemoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Шкала 1")
        self.configure(bg=Palette.BG_DARK)
        self.resizable(False, False)

        # Карточка с прибором
        container = tk.Frame(self, bg=Palette.BG_DARK)
        container.pack(padx=30, pady=(30, 15))

        self.thermo = Thermometer(container, size=380)
        self.thermo.pack()

        # Панель кнопок
        btn_frame = tk.Frame(self, bg=Palette.BG_DARK)
        btn_frame.pack(pady=(0, 25))

        ModernButton(btn_frame, "0 °C",   lambda: self.thermo.set_value(0)).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_frame, "15 °C",  lambda: self.thermo.set_value(15)).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_frame, "25 °C",  lambda: self.thermo.set_value(25)).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_frame, "40 °C",  lambda: self.thermo.set_value(40)).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_frame, "Случайно", self.random_value).pack(side=tk.LEFT, padx=5)

    def random_value(self):
        self.thermo.set_value(random.uniform(0, 50))


if __name__ == "__main__":
    DemoApp().mainloop()