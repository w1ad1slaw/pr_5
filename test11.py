import sys
import math
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, QColor, QPen, QBrush,
    QFont, QPainterPath, QPolygonF
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QVariantAnimation, Signal
)


# ---------- Палитра (единая для всех приборов) ----------
class Palette:
    BG         = QColor("#0d1117")
    TEXT       = QColor("#e6edf3")
    TEXT_MUTED = QColor("#7d8590")
    ACCENT     = QColor("#58a6ff")

    # Корпус
    BEZEL_RED_LO = QColor("#8b1f22")
    BEZEL_RED_HI = QColor("#e5484d")

    # Циферблат
    FACE_TOP   = QColor("#2b3540")
    FACE_BOT   = QColor("#151b22")
    FACE_RING  = QColor(255, 255, 255, 18)

    # Стрелка
    NEEDLE_N   = QColor("#e5484d")
    NEEDLE_N_2 = QColor("#8b1f22")
    NEEDLE_S   = QColor("#4a90e2")
    NEEDLE_S_2 = QColor("#1e5bb8")

    # Шарнир
    HUB_EDGE   = QColor("#7d8590")
    HUB_FILL   = QColor("#e6edf3")
    HUB_DOT    = QColor("#2b3540")


class Compass(QWidget):
    """
    Круглый компас с плавной анимацией вращения стрелки.
    Азимут: 0° = север, по часовой стрелке (N → E → S → W).
    """

    azimuthChanged = Signal(float)

    def __init__(self, azimuth=0.0, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setMouseTracking(True)

        # Пружина
        self._current = float(azimuth) % 360
        self._target = self._current
        self._velocity = 0.0
        self._spring = 0.18
        self._damping = 0.70
        self._dragging = False

        self._timer = QVariantAnimation(self)
        self._timer.setStartValue(0.0)
        self._timer.setEndValue(1.0)
        self._timer.setDuration(16)
        self._timer.setLoopCount(-1)
        self._timer.valueChanged.connect(self._tick)
        self._timer.start()

    # ---------- API ----------
    def set_azimuth(self, a):
        """Установить азимут (0…360). Плавно повернёт стрелку."""
        a = a % 360
        # Выбираем кратчайший путь поворота
        diff = ((a - self._current + 540) % 360) - 180
        self._target = self._current + diff
        self.azimuthChanged.emit(a)

    def azimuth(self):
        return self._current % 360

    # ---------- Анимация ----------
    def _tick(self, _):
        if not self._dragging:
            diff = self._target - self._current
            self._velocity += diff * self._spring
            self._velocity *= self._damping
            self._current += self._velocity
            if abs(diff) < 0.01 and abs(self._velocity) < 0.01:
                self._current = self._target
                self._velocity = 0.0
        self.update()

    # ---------- Геометрия ----------
    def _geom(self):
        w, h = self.width(), self.height()
        size = min(w, h)
        cx, cy = w / 2, h / 2
        r_outer = size / 2 - 6      # внешняя красная окантовка
        r_face  = r_outer - 14      # тёмный циферблат
        r_inner = r_face - 22       # внутренний круг под стеклом
        return cx, cy, r_outer, r_face, r_inner

    # ---------- Отрисовка ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        cx, cy, r_outer, r_face, r_inner = self._geom()

        # 1. Тень под корпусом
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(QPointF(cx + 2, cy + 4), r_outer + 1, r_outer + 1)

        # 2. Красная окантовка (с градиентом)
        bezel_grad = QRadialGradient(QPointF(cx - r_outer * 0.3, cy - r_outer * 0.4), r_outer * 1.5)
        bezel_grad.setColorAt(0.0, Palette.BEZEL_RED_HI)
        bezel_grad.setColorAt(1.0, Palette.BEZEL_RED_LO)
        p.setBrush(QBrush(bezel_grad))
        p.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # 3. Тёмный циферблат
        face_grad = QRadialGradient(QPointF(cx - r_face * 0.35, cy - r_face * 0.4), r_face * 1.5)
        face_grad.setColorAt(0.0, Palette.FACE_TOP)
        face_grad.setColorAt(1.0, Palette.FACE_BOT)
        p.setBrush(QBrush(face_grad))
        p.drawEllipse(QPointF(cx, cy), r_face, r_face)

        # 4. Светлое внутреннее кольцо (стеклянный эффект)
        p.setPen(Qt.NoPen)
        inner_grad = QRadialGradient(QPointF(cx, cy - r_inner * 0.3), r_inner * 1.2)
        inner_grad.setColorAt(0.0, QColor(255, 255, 255, 26))
        inner_grad.setColorAt(0.7, QColor(255, 255, 255, 6))
        inner_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(inner_grad))
        p.drawEllipse(QPointF(cx, cy), r_inner, r_inner)

        # Тонкое кольцо-контур внутренней области
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r_inner, r_inner)

        # 5. Метки сторон света
        self._draw_cardinal_marks(p, cx, cy, r_face)
        # 6. Буквы N/E/S/W
        self._draw_cardinal_letters(p, cx, cy, r_face)
        # 7. Стрелка
        self._draw_needle(p, cx, cy, r_face, r_inner)
        # 8. Hover-обводка
        if self._dragging or self._is_hovered():
            p.setPen(QPen(QColor(88, 166, 255, 180), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r_outer + 4, r_outer + 4)

    # --- Метки С/Ю/З/В и промежуточные риски ---
    def _draw_cardinal_marks(self, p, cx, cy, r_face):
        p.setPen(QPen(QColor(255, 255, 255, 220), 3, Qt.SolidLine, Qt.RoundCap))
        for angle_deg in [0, 90, 180, 270]:
            self._draw_mark(p, cx, cy, r_face, angle_deg, length=14, width=3)

        p.setPen(QPen(QColor(255, 255, 255, 170), 2, Qt.SolidLine, Qt.RoundCap))
        for angle_deg in [45, 135, 225, 315]:
            self._draw_mark(p, cx, cy, r_face, angle_deg, length=9, width=2)

    def _draw_mark(self, p, cx, cy, r_face, angle_deg, length, width):
        rad = math.radians(angle_deg - 90)   # 0° = верх
        r1 = r_face - 6
        r2 = r1 - length
        x1 = cx + r1 * math.cos(rad)
        y1 = cy + r1 * math.sin(rad)
        x2 = cx + r2 * math.cos(rad)
        y2 = cy + r2 * math.sin(rad)
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    # --- Буквы N/E/S/W ---
    def _draw_cardinal_letters(self, p, cx, cy, r_face):
        p.setPen(QPen(Palette.TEXT))
        p.setFont(QFont("Segoe UI", 13, QFont.Bold))

        letters = [
            ("N", 0),
            ("E", 90),
            ("S", 180),
            ("W", 270),
        ]
        r_text = r_face - 32
        for letter, angle_deg in letters:
            rad = math.radians(angle_deg - 90)
            x = cx + r_text * math.cos(rad)
            y = cy + r_text * math.sin(rad)
            rect = QRectF(x - 14, y - 12, 28, 24)
            p.drawText(rect, Qt.AlignCenter, letter)

    # --- Стрелка ---
    def _draw_needle(self, p, cx, cy, r_face, r_inner):
        # Угол поворота: азимут 0° = север = стрелка вверх
        angle_rad = math.radians(self._current)

        # Размеры стрелки
        len_n = r_inner - 4      # длина северной половины
        len_s = r_inner - 4      # длина южной
        half_w = 12              # полуширина у основания

        # --- Северная половина (красная) ---
        tip_n = QPointF(cx + len_n * math.sin(angle_rad),
                        cy - len_n * math.cos(angle_rad))
        base_l_n = QPointF(cx - half_w * math.cos(angle_rad),
                           cy - half_w * math.sin(angle_rad))
        base_r_n = QPointF(cx + half_w * math.cos(angle_rad),
                           cy + half_w * math.sin(angle_rad))
        poly_n = QPolygonF([tip_n, base_l_n, base_r_n])

        grad_n = QLinearGradient(base_l_n, tip_n)
        grad_n.setColorAt(0.0, Palette.NEEDLE_N_2)
        grad_n.setColorAt(1.0, Palette.NEEDLE_N)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad_n))
        p.drawPolygon(poly_n)

        # --- Южная половина (синяя) ---
        tip_s = QPointF(cx - len_s * math.sin(angle_rad),
                        cy + len_s * math.cos(angle_rad))
        base_l_s = QPointF(cx - half_w * math.cos(angle_rad),
                           cy - half_w * math.sin(angle_rad))
        base_r_s = QPointF(cx + half_w * math.cos(angle_rad),
                           cy + half_w * math.sin(angle_rad))
        poly_s = QPolygonF([tip_s, base_l_s, base_r_s])

        grad_s = QLinearGradient(base_l_s, tip_s)
        grad_s.setColorAt(0.0, Palette.NEEDLE_S_2)
        grad_s.setColorAt(1.0, Palette.NEEDLE_S)
        p.setBrush(QBrush(grad_s))
        p.drawPolygon(poly_s)

        # --- Шарнир ---
        # Тень шарнира
        p.setBrush(QColor(0, 0, 0, 100))
        p.drawEllipse(QPointF(cx + 1, cy + 2), 12, 12)

        # Внешний контур
        hub_grad = QRadialGradient(QPointF(cx - 3, cy - 3), 14)
        hub_grad.setColorAt(0.0, QColor("#ffffff"))
        hub_grad.setColorAt(1.0, QColor("#c9d1d9"))
        p.setBrush(QBrush(hub_grad))
        p.setPen(QPen(Palette.HUB_EDGE, 1))
        p.drawEllipse(QPointF(cx, cy), 11, 11)

        # Внутренняя точка
        p.setPen(Qt.NoPen)
        p.setBrush(Palette.HUB_DOT)
        p.drawEllipse(QPointF(cx, cy), 2.5, 2.5)

    # --- Hover ---
    def _is_hovered(self):
        return self.underMouse()

    # ---------- Мышь ----------
    def _pos_to_azimuth(self, pos):
        cx, cy, *_ = self._geom()
        dx = pos.x() - cx
        dy = pos.y() - cy
        # Угол: 0° = север, по часовой
        a = math.degrees(math.atan2(dx, -dy))
        return a % 360

    def mousePressEvent(self, event):
        cx, cy, r_outer, *_ = self._geom()
        if math.hypot(event.position().x() - cx,
                      event.position().y() - cy) <= r_outer:
            self._dragging = True
            self._current = self._pos_to_azimuth(event.position())
            self._target = self._current
            self._velocity = 0.0
            self.azimuthChanged.emit(self._current % 360)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._current = self._pos_to_azimuth(event.position())
            self._target = self._current
            self._velocity = 0.0
            self.azimuthChanged.emit(self._current % 360)
        self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False


# ---------- Демо ----------
def azimuth_to_text(a):
    """Преобразовать азимут в направление + цифру."""
    a = a % 360
    names = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    idx = int((a + 22.5) % 360 // 45) % 8
    return f"{a:05.1f}°  {names[idx]}"


class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Шкала 7 — Компас")
        self.setStyleSheet("background-color: #0d1117;")
        self.setMinimumSize(560, 560)
        self.resize(680, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(20)

        # Заголовок
        title = QLabel("КОМПАС")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #7d8590; font-family: 'Segoe UI'; "
            "font-size: 12px; font-weight: 700; letter-spacing: 3px;"
        )
        root.addWidget(title)

        # Компас
        self.compass = Compass(azimuth=0)
        self.compass.azimuthChanged.connect(self._on_azimuth)
        root.addWidget(self.compass, 1)

        # Крупное значение азимута
        self.value_label = QLabel(azimuth_to_text(0))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(
            "color: #58a6ff; font-family: 'Segoe UI'; "
            "font-size: 24px; font-weight: 700;"
        )
        root.addWidget(self.value_label)

        # Кнопки-пресеты сторон света
        btns = QHBoxLayout()
        btns.setSpacing(8)
        for lbl, val in [("С", 0), ("В", 90), ("Ю", 180), ("З", 270), ("СВ", 45), ("СЗ", 315)]:
            b = QPushButton(lbl)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(42)
            b.setMinimumWidth(56)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #1c222b; color: #e6edf3;
                    border: 1px solid #2a313b; border-radius: 10px;
                    padding: 8px 12px;
                    font-family: 'Segoe UI'; font-size: 13px; font-weight: 700;
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
            b.clicked.connect(lambda _, v=val: self.compass.set_azimuth(v))
            btns.addWidget(b)
        btns.addStretch(1)
        root.addLayout(btns)

    def _on_azimuth(self, a):
        self.value_label.setText(azimuth_to_text(a))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = DemoWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()