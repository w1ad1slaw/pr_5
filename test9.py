import sys
import math
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from PySide6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, QConicalGradient,
    QColor, QPen, QBrush, QFont, QPainterPath, QPolygonF, QIcon
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QRect, QSize, Signal, QPoint
)


# ============================================================
# ТЕМЫ ОФОРМЛЕНИЯ
# ============================================================
class Theme:
    """Контейнер цветов для одной темы."""
    def __init__(self, name,
                 outer_ring_start, outer_ring_end,   # градиент окантовки
                 disk_bg_top, disk_bg_bottom,        # фон диска
                 arrow_idle, arrow_hover, arrow_active,
                 center_bg, center_icon, center_border,
                 shadow_alpha=140):
        self.name = name
        self.outer_ring_start = QColor(outer_ring_start)
        self.outer_ring_end   = QColor(outer_ring_end)
        self.disk_bg_top      = QColor(disk_bg_top)
        self.disk_bg_bottom   = QColor(disk_bg_bottom)
        self.arrow_idle       = QColor(arrow_idle)
        self.arrow_hover      = QColor(arrow_hover)
        self.arrow_active     = QColor(arrow_active)
        self.center_bg        = QColor(center_bg)
        self.center_icon      = QColor(center_icon)
        self.center_border    = QColor(center_border)
        self.shadow_alpha     = shadow_alpha


# --- 4 темы (по мотивам образца) ---
THEME_DARK = Theme(
    name="dark",
    outer_ring_start="#3a4452", outer_ring_end="#1a2028",
    disk_bg_top="#1c222b",       disk_bg_bottom="#0f141a",
    arrow_idle="#5a6472", arrow_hover="#8b95a3", arrow_active="#26c6da",
    center_bg="#0a0e13", center_icon="#26c6da", center_border="#26c6da",
)

THEME_LIGHT = Theme(
    name="light",
    outer_ring_start="#ff8a65", outer_ring_end="#4fc3f7",   # радужная окантовка
    disk_bg_top="#f5f5f5",       disk_bg_bottom="#dcdcdc",
    arrow_idle="#a0a0a0", arrow_hover="#707070", arrow_active="#4fc3f7",
    center_bg="#ffffff", center_icon="#909090", center_border="#d0d0d0",
)

THEME_BLUE = Theme(
    name="blue",
    outer_ring_start="#ffd54f", outer_ring_end="#ffb300",   # золото
    disk_bg_top="#1e3a5f",       disk_bg_bottom="#0d1f38",
    arrow_idle="#4a7ba8", arrow_hover="#7aa8d4", arrow_active="#7ec8ff",
    center_bg="#0a1f38", center_icon="#7ec8ff", center_border="#7ec8ff",
)

THEME_PURPLE = Theme(
    name="purple",
    outer_ring_start="#b39ddb", outer_ring_end="#7e57c2",
    disk_bg_top="#3a2a5c",       disk_bg_bottom="#1a1030",
    arrow_idle="#6a5a8a", arrow_hover="#9c8ac0", arrow_active="#c8a8ff",
    center_bg="#1a1030", center_icon="#c8a8ff", center_border="#c8a8ff",
)


# ============================================================
# ВИДЖЕТ: СЕЛЕКТОР НАПРАВЛЕНИЯ
# ============================================================
class DirectionSelector(QWidget):
    """
    8-стрелочный селектор направления с центральной кнопкой.

    Сигналы:
        directionChanged(int)  — 0..7 (0 = верх, по часовой)
        resetClicked()         — клик по центральной кнопке
    """

    directionChanged = Signal(int)
    resetClicked = Signal()

    def __init__(self, theme=THEME_DARK, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setMouseTracking(True)

        self.theme = theme
        self._hover_dir = -1     # -1 = ничего
        self._active_dir = -1
        self._hover_center = False
        self._active_center = False
        self._selected_dir = 0   # подсвеченное «текущее» направление

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def set_selected_direction(self, d):
        self._selected_dir = d % 8
        self.update()

    # ---------- Геометрия ----------
    def _geom(self):
        w, h = self.width(), self.height()
        size = min(w, h)
        cx, cy = w / 2, h / 2
        r_outer = size / 2 - 6
        r_disk = r_outer - 12
        r_arrow_out = r_disk - 6
        r_arrow_in = r_arrow_out - 22
        r_center = r_arrow_in - 22
        return cx, cy, r_outer, r_disk, r_arrow_out, r_arrow_in, r_center

    def _angle_to_xy(self, angle_deg, radius, cx, cy):
        """Угол: 0° = верх, по часовой стрелке."""
        rad = math.radians(angle_deg - 90)
        return cx + radius * math.cos(rad), cy + radius * math.sin(rad)

    # ---------- Отрисовка ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        cx, cy, r_outer, r_disk, r_arr_o, r_arr_i, r_center = self._geom()
        t = self.theme

        # 1. Внешняя окантовка (градиент)
        self._draw_outer_ring(p, cx, cy, r_outer, t)

        # 2. Диск (фон)
        self._draw_disk(p, cx, cy, r_disk, t)

        # 3. 8 стрелок
        for i in range(8):
            self._draw_arrow(p, cx, cy, i, r_arr_o, r_arr_i, t)

        # 4. Центральная кнопка
        self._draw_center(p, cx, cy, r_center, t)

    def _draw_outer_ring(self, p, cx, cy, r, t):
        # Тень
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, t.shadow_alpha))
        p.drawEllipse(QPointF(cx + 1, cy + 3), r + 1, r + 1)

        # Градиентная окантовка (линейный градиент по диагонали)
        grad = QLinearGradient(QPointF(cx - r, cy - r), QPointF(cx + r, cy + r))
        grad.setColorAt(0.0, t.outer_ring_start)
        grad.setColorAt(1.0, t.outer_ring_end)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_disk(self, p, cx, cy, r, t):
        # Радиальный градиент диска
        grad = QRadialGradient(QPointF(cx - r * 0.3, cy - r * 0.4), r * 1.5)
        grad.setColorAt(0.0, t.disk_bg_top)
        grad.setColorAt(1.0, t.disk_bg_bottom)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Верхний мягкий блик
        p.setBrush(QColor(255, 255, 255, 12))
        p.drawEllipse(QPointF(cx, cy - r * 0.35), r * 0.55, r * 0.35)

    def _draw_arrow(self, p, cx, cy, index, r_out, r_in, t):
        """Треугольная стрелка под углом index*45°."""
        angle = index * 45.0

        # Цвет — зависит от состояния
        if index == self._active_dir:
            color = t.arrow_active
        elif index == self._hover_dir:
            color = t.arrow_hover
        elif index == self._selected_dir:
            color = t.arrow_active.darker(130)
        else:
            color = t.arrow_idle

        # Строим треугольник: острие к внешнему краю, основание — внутри
        tip_x, tip_y = self._angle_to_xy(angle, r_out, cx, cy)
        # Перпендикуляр для основания
        rad = math.radians(angle - 90)
        perp_x = -math.sin(rad)
        perp_y = math.cos(rad)
        half_base = 16

        base_l = QPointF(cx + r_in * math.cos(rad) + half_base * perp_x,
                         cy + r_in * math.sin(rad) + half_base * perp_y)
        base_r = QPointF(cx + r_in * math.cos(rad) - half_base * perp_x,
                         cy + r_in * math.sin(rad) - half_base * perp_y)

        poly = QPolygonF([QPointF(tip_x, tip_y), base_l, base_r])

        # Свечение при hover
        if index == self._hover_dir:
            p.setPen(Qt.NoPen)
            glow = QColor(color)
            glow.setAlpha(70)
            p.setBrush(glow)
            big = QPolygonF([QPointF(tip_x, tip_y),
                             QPointF(base_l.x() - 2, base_l.y() - 2),
                             QPointF(base_r.x() - 2, base_r.y() - 2)])
            p.drawPolygon(big)

        # Основная заливка
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPolygon(poly)

    def _draw_center(self, p, cx, cy, r, t):
        # Тень
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(QPointF(cx, cy + 2), r + 1, r + 1)

        # Основной круг
        if self._active_center:
            bg = t.center_border
        elif self._hover_center:
            bg = t.center_bg.lighter(130)
        else:
            bg = t.center_bg

        grad = QRadialGradient(QPointF(cx - r * 0.3, cy - r * 0.3), r * 1.4)
        grad.setColorAt(0.0, bg.lighter(120))
        grad.setColorAt(1.0, bg.darker(120))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Окантовка
        p.setPen(QPen(t.center_border, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Иконка «обновления» — две дуги со стрелками
        self._draw_refresh_icon(p, cx, cy, r * 0.55, t.center_icon)

    def _draw_refresh_icon(self, p, cx, cy, r, color):
        """Иконка круговой стрелки «обновление»."""
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap))

        # Две дуги (верхняя и нижняя) со смещением
        arc_rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(arc_rect, 60 * 16, 140 * 16)
        p.drawArc(arc_rect, 240 * 16, 140 * 16)

        # Стрелки на концах дуг
        def arrow_head(angle_deg):
            rad = math.radians(angle_deg - 90)
            tip_x = cx + r * math.cos(rad)
            tip_y = cy + r * math.sin(rad)
            # Треугольник
            perp_x = -math.sin(rad)
            perp_y = math.cos(rad)
            back_x = tip_x - 8 * math.cos(rad)
            back_y = tip_y - 8 * math.sin(rad)
            pts = [
                QPointF(tip_x, tip_y),
                QPointF(back_x + 4 * perp_x, back_y + 4 * perp_y),
                QPointF(back_x - 4 * perp_x, back_y - 4 * perp_y),
            ]
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF(pts))
            p.setPen(QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap))

        arrow_head(60)   # конец верхней дуги
        arrow_head(240)  # конец нижней дуги

    # ---------- Обработка мыши ----------
    def _dir_at_pos(self, pos):
        """Определить, по какой стрелке кликнули, или -1."""
        cx, cy, r_outer, r_disk, r_arr_o, r_arr_i, r_center = self._geom()
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.hypot(dx, dy)

        # Если в центральной кнопке — вернуть -2
        if dist <= r_center:
            return -2

        # Внутри кольца стрелок
        if r_arr_i - 6 <= dist <= r_arr_o + 4:
            angle = math.degrees(math.atan2(dy, dx)) + 90   # 0° = верх
            angle = (angle + 360) % 360
            index = round(angle / 45) % 8
            return index

        return -1

    def mouseMoveEvent(self, event):
        d = self._dir_at_pos(event.position().toPoint())
        new_hover_dir = d if d >= 0 else -1
        new_hover_center = (d == -2)

        if new_hover_dir != self._hover_dir or new_hover_center != self._hover_center:
            self._hover_dir = new_hover_dir
            self._hover_center = new_hover_center
            # Меняем курсор
            if new_hover_center or new_hover_dir >= 0:
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, event):
        self._hover_dir = -1
        self._hover_center = False
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        d = self._dir_at_pos(event.position().toPoint())
        if d == -2:
            self._active_center = True
        elif d >= 0:
            self._active_dir = d
        self.update()

    def mouseReleaseEvent(self, event):
        d = self._dir_at_pos(event.position().toPoint())

        if d == -2 and self._active_center:
            self._active_center = False
            self.resetClicked.emit()
        elif d >= 0 and self._active_dir == d:
            self._active_dir = -1
            self._selected_dir = d
            self.directionChanged.emit(d)
        else:
            self._active_dir = -1
            self._active_center = False
        self.update()


# ============================================================
# ДЕМО-ОКНО: 4 ТЕМЫ
# ============================================================
class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Шкала 5 — Индикаторы направления")
        self.setStyleSheet("background-color: #0d1117;")
        self.setMinimumSize(600,500)
        self.resize(1500,900)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # Заголовок
        title = QLabel("Индикаторы направления")
        title.setStyleSheet(
            "color: #e6edf3; font-family: 'Segoe UI'; "
            "font-size: 16px; font-weight: 700;"
        )
        root.addWidget(title)

        subtitle = QLabel("4 цветовые темы одного виджета. Клик по стрелке — выбор направления. "
                          "Клик по центру — сброс.")
        subtitle.setStyleSheet(
            "color: #7d8590; font-family: 'Segoe UI'; font-size: 11px;"
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        # Ряд из 4 виджетов
        row = QHBoxLayout()
        row.setSpacing(16)

        self.selectors = []
        for theme in [THEME_DARK, THEME_LIGHT, THEME_BLUE, THEME_PURPLE]:
            col = QVBoxLayout()
            col.setSpacing(8)

            sel = DirectionSelector(theme)
            sel.directionChanged.connect(
                lambda d, s=sel, name=theme.name: self._on_dir(d, name)
            )
            sel.resetClicked.connect(
                lambda name=theme.name: self._on_reset(name)
            )
            self.selectors.append(sel)
            col.addWidget(sel, 1)

            # Подпись темы
            lbl = QLabel(theme.name.upper())
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #7d8590; font-family: 'Segoe UI'; "
                "font-size: 10px; font-weight: 700; letter-spacing: 1px;"
            )
            col.addWidget(lbl)

            row.addLayout(col, 1)

        root.addLayout(row, 1)

        # Статусная строка
        self.status = QLabel("—")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(
            "color: #58a6ff; font-family: 'Consolas'; "
            "font-size: 13px; font-weight: 600; "
            "background-color: #161b22; padding: 10px; "
            "border-radius: 8px; border: 1px solid #2a313b;"
        )
        root.addWidget(self.status)

    def _on_dir(self, d, theme_name):
        names = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
        self.status.setText(
            f"[{theme_name}] directionChanged → {d} ({names[d]})"
        )

    def _on_reset(self, theme_name):
        self.status.setText(f"[{theme_name}] resetClicked")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = DemoWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()