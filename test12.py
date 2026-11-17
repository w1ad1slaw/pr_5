import os
import sys
import math
import numpy as np
import sounddevice as sd

# === ИСПРАВЛЕНИЕ ОШИБКИ QT PLATFORM PLUGIN ===
try:
    import PyQt5
    pyqt_path = os.path.dirname(PyQt5.__file__)
    plugin_path = os.path.join(pyqt_path, 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_PLUGIN_PATH'] = plugin_path
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(plugin_path, 'platforms')
except ImportError:
    pass
# ============================================

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QFrame, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QLinearGradient,
                         QRadialGradient, QPainterPath, QPalette, QFontMetrics, QPolygonF)

# ============================================================
# АУДИО ДВИЖОК
# ============================================================
class AudioEngine:
    def __init__(self):
        self.stream = None
        self.is_playing = False
        self.phase = 0.0
        
        self.freq_left = 1000.0
        self.freq_right = 1000.0
        self.amp_left = 0.2
        self.amp_right = 0.2
        self.signal_type = "sine"
        self.channel_mode = "both"
        
        self.last_buffer = np.zeros((4096, 2))
        self.current_level_left = 0.0
        self.current_level_right = 0.0

    def audio_callback(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        
        t = (np.arange(frames) + self.phase) / 44100
        self.phase = (self.phase + frames) % 44100
        
        def generate_signal(freq, stype):
            if stype == "sine":
                return np.sin(2 * np.pi * freq * t)
            elif stype == "square":
                return np.sign(np.sin(2 * np.pi * freq * t))
            elif stype == "triangle":
                return (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t))
            elif stype == "sawtooth":
                return 2.0 * (freq * t - np.floor(freq * t + 0.5))
            elif stype == "noise":
                return np.random.uniform(-1, 1, frames)
            return np.zeros(frames)

        raw_left = generate_signal(self.freq_left, self.signal_type)
        raw_right = generate_signal(self.freq_right, self.signal_type)
        
        sig_left = raw_left * self.amp_left
        sig_right = raw_right * self.amp_right
        
        outdata.fill(0)
        
        if self.channel_mode in ["both", "left"]:
            outdata[:, 0] = sig_left
            self.current_level_left = min(100.0, np.sqrt(np.mean(sig_left**2)) * 300)
        else:
            self.current_level_left = 0.0

        if self.channel_mode in ["both", "right"]:
            outdata[:, 1] = sig_right
            self.current_level_right = min(100.0, np.sqrt(np.mean(sig_right**2)) * 300)
        else:
            self.current_level_right = 0.0
            
        self.last_buffer = np.roll(self.last_buffer, -frames, axis=0)
        self.last_buffer[-frames:] = outdata

    def start(self):
        if not self.is_playing:
            try:
                self.stream = sd.OutputStream(
                    samplerate=44100, channels=2,
                    callback=self.audio_callback, blocksize=1024
                )
                self.stream.start()
                self.is_playing = True
            except Exception as e:
                print(f"Ошибка аудио: {e}")
                self.is_playing = False

    def stop(self):
        if self.is_playing and self.stream:
            self.stream.stop()
            self.stream.close()
            self.is_playing = False
            self.current_level_left = 0.0
            self.current_level_right = 0.0
            self.last_buffer.fill(0)

# ============================================================
# ВИДЖЕТЫ
# ============================================================

class DigitDisplay(QWidget):
    def __init__(self, parent=None, max_value=99999, suffix="", mode="freq"):
        super().__init__(parent)
        self._target_value = 0
        self._anim_digits = [0.0] * 5 
        self._max_value = max_value
        self._suffix = suffix
        self._mode = mode
        self._glow = 0
        self._dimmed = False
        
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)
        
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._update_glow)
        self._glow_timer.start(50)
        self.setFixedHeight(70)
    
    def _update_glow(self):
        self._glow = (self._glow + 0.1) % (2 * math.pi)
        self.update()
    
    def set_value(self, value):
        self._target_value = max(0, min(value, self._max_value))
    
    def set_dimmed(self, dimmed):
        self._dimmed = dimmed
        self.update()
    
    def _animate(self):
        if self._mode == "freq":
            target_str = f"{self._target_value:05d}"
        else:
            target_str = f"{self._target_value:03d}"
            
        num_digits = len(target_str)
        start_idx = 5 - num_digits
        
        needs_update = False
        for i in range(start_idx):
            if self._anim_digits[i] != 0.0:
                self._anim_digits[i] = 0.0
                needs_update = True
                
        for i, char in enumerate(target_str):
            target_digit = int(char)
            idx = start_idx + i
            diff = target_digit - self._anim_digits[idx]
            if abs(diff) > 0.01:
                self._anim_digits[idx] += diff * 0.2
                needs_update = True
            else:
                self._anim_digits[idx] = target_digit
        if needs_update:
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        
        gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        if self._dimmed:
            gradient.setColorAt(0, QColor("#080810"))
            gradient.setColorAt(0.5, QColor("#101018"))
            gradient.setColorAt(1, QColor("#080810"))
        else:
            gradient.setColorAt(0, QColor("#0d0d1a"))
            gradient.setColorAt(0.5, QColor("#1a1a2e"))
            gradient.setColorAt(1, QColor("#0d0d1a"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#333355") if not self._dimmed else QColor("#222233"), 1))
        painter.drawRoundedRect(rect, 8, 8)
        
        if not self._dimmed:
            glow_alpha = int(20 + 15 * math.sin(self._glow))
            painter.setPen(QPen(QColor(0, 255, 65, glow_alpha), 2))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
        
        font_large = QFont("Courier New", 26, QFont.Bold)
        font_large.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        font_small = QFont("Courier New", 16, QFont.Bold)
        font_small.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        
        fm_large = QFontMetrics(font_large)
        char_w_large = fm_large.horizontalAdvance("0")
        
        fm_small = QFontMetrics(font_small)
        char_w_small = fm_small.horizontalAdvance("0")
        
        if self._mode == "freq":
            num_large, num_small = 2, 3
        else:
            num_large, num_small = 3, 0
            
        total_width = num_large * char_w_large + num_small * char_w_small
        start_x = rect.center().x() - total_width / 2
        
        if self._dimmed:
            painter.setPen(QColor(0, 80, 20, 180))
        else:
            painter.setPen(QColor(0, 255, 65, 255))
            
        start_idx = 5 - (num_large + num_small)
        bottom_y = rect.center().y() + fm_large.ascent() / 2
        
        for i in range(num_large + num_small):
            idx = start_idx + i
            val = self._anim_digits[idx]
            v1 = int(val) % 10
            v2 = int(val + 1) % 10
            frac = val - int(val)
            
            alpha1 = int(255 * (1.0 - frac))
            alpha2 = int(255 * frac)
            
            if i < num_large:
                painter.setFont(font_large)
                x = start_x + i * char_w_large
                draw_rect = QRectF(x, bottom_y - fm_large.ascent(), char_w_large, fm_large.height())
            else:
                painter.setFont(font_small)
                x = start_x + num_large * char_w_large + (i - num_large) * char_w_small
                draw_rect = QRectF(x, bottom_y - fm_small.ascent(), char_w_small, fm_small.height())
                
            painter.setPen(QColor(0, 255, 65, alpha1) if not self._dimmed else QColor(0, 80, 20, alpha1))
            painter.drawText(draw_rect, Qt.AlignCenter, str(v1))
            painter.setPen(QColor(0, 255, 65, alpha2) if not self._dimmed else QColor(0, 80, 20, alpha2))
            painter.drawText(draw_rect, Qt.AlignCenter, str(v2))
        
        if self._suffix:
            suffix_font = QFont("Arial", 11, QFont.Bold)
            painter.setFont(suffix_font)
            suffix_rect = QRectF(rect)
            suffix_rect.setRight(rect.right() - 3)
            suffix_rect.setLeft(rect.right() - 35)
            if self._dimmed:
                painter.setPen(QColor(0, 60, 15, 150))
            else:
                painter.setPen(QColor(0, 200, 50, 200))
            painter.drawText(suffix_rect, Qt.AlignRight | Qt.AlignVCenter, self._suffix)
        painter.end()

class Knob(QWidget):
    valueChanged = pyqtSignal(int)
    
    def __init__(self, parent=None, min_val=0, max_val=100, default=50,
                 label="", unit=""):
        super().__init__(parent)
        self._min_val = min_val
        self._max_val = max_val
        self._value = default
        self._display_value = float(default)
        self._target_value = float(default)
        self._angle = -135
        self._target_angle = -135
        self._label = label
        self._unit = unit
        
        self._is_dragging = False
        self._drag_start_y = 0
        self._drag_start_value = 0
        self._hover = False
        self._sensitivity = 1.0
        
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)
        
        self.setFixedSize(100, 140)
        self.setCursor(Qt.PointingHandCursor)
        self._update_angle()
        self.setToolTip(f"{label}: тяните вверх/вниз\nShift — точно, Ctrl — очень точно")
    
    def _update_angle(self):
        range_val = self._max_val - self._min_val
        if range_val == 0:
            self._target_angle = -135
        else:
            normalized = (self._target_value - self._min_val) / range_val
            self._target_angle = -135 + normalized * 270
    
    def set_value(self, value):
        value = max(self._min_val, min(self._max_val, value))
        if abs(value - self._target_value) < 0.01:
            return
        self._target_value = value
        self._value = int(round(value))
        self._update_angle()
        self.valueChanged.emit(self._value)
    
    def get_value(self):
        return int(round(self._target_value))
    
    def _animate(self):
        angle_diff = self._target_angle - self._angle
        if abs(angle_diff) > 0.1:
            self._angle += angle_diff * 0.2
        else:
            self._angle = self._target_angle
        
        val_diff = self._target_value - self._display_value
        if abs(val_diff) > 0.01:
            self._display_value += val_diff * 0.2
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_y = event.globalPos().y()
            self._drag_start_value = self._target_value
            self.setCursor(Qt.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        if self._is_dragging:
            current_y = event.globalPos().y()
            delta_y = self._drag_start_y - current_y
            
            if event.modifiers() & Qt.ControlModifier:
                sens = self._sensitivity * 0.1
            elif event.modifiers() & Qt.ShiftModifier:
                sens = self._sensitivity * 0.3
            else:
                sens = self._sensitivity
            
            range_val = self._max_val - self._min_val
            delta_value = (delta_y / 200.0) * range_val * sens
            
            new_value = self._drag_start_value + delta_value
            new_value = round(new_value)
            self.set_value(new_value)
    
    def mouseReleaseEvent(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self.setCursor(Qt.PointingHandCursor)
    
    def enterEvent(self, event):
        self._hover = True
        self.update()
    
    def leaveEvent(self, event):
        self._hover = False
        self._is_dragging = False
        self.setCursor(Qt.PointingHandCursor)
        self.update()
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.set_value(self._target_value + 1)
        else:
            self.set_value(self._target_value - 1)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        cx = self.width() / 2
        cy = 50
        radius = 35
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx + 2, cy + 3), radius + 2, radius + 2)
        
        body_gradient = QRadialGradient(cx, cy, radius)
        body_gradient.setColorAt(0, QColor("#4a4a6a"))
        body_gradient.setColorAt(0.3, QColor("#3a3a5a"))
        body_gradient.setColorAt(0.7, QColor("#2a2a4a"))
        body_gradient.setColorAt(1, QColor("#1a1a3a"))
        
        painter.setBrush(QBrush(body_gradient))
        if self._hover:
            painter.setPen(QPen(QColor(0, 212, 255, 150), 2))
        else:
            painter.setPen(QPen(QColor("#555577"), 1))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)
        
        inner_radius = radius - 6
        inner_gradient = QRadialGradient(cx - 5, cy - 5, inner_radius)
        inner_gradient.setColorAt(0, QColor("#3d3d5d"))
        inner_gradient.setColorAt(1, QColor("#252545"))
        painter.setBrush(QBrush(inner_gradient))
        painter.setPen(QPen(QColor("#444466"), 1))
        painter.drawEllipse(QPointF(cx, cy), inner_radius, inner_radius)
        
        for i in range(24):
            angle_deg = (i / 24) * 360
            angle_rad = math.radians(angle_deg)
            x1 = cx + (radius - 3) * math.cos(angle_rad)
            y1 = cy + (radius - 3) * math.sin(angle_rad)
            x2 = cx + (radius - 7) * math.cos(angle_rad)
            y2 = cy + (radius - 7) * math.sin(angle_rad)
            painter.setPen(QPen(QColor("#555577"), 1))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        indicator_angle = math.radians(self._angle - 90)
        indicator_length = radius - 10
        ix = cx + indicator_length * math.cos(indicator_angle)
        iy = cy + indicator_length * math.sin(indicator_angle)
        
        painter.setPen(QPen(QColor(0, 255, 65, 255), 2))
        painter.drawLine(QPointF(cx, cy), QPointF(ix, iy))
        
        center_gradient = QRadialGradient(cx, cy, 6)
        center_gradient.setColorAt(0, QColor("#666688"))
        center_gradient.setColorAt(1, QColor("#333355"))
        painter.setBrush(QBrush(center_gradient))
        painter.setPen(QPen(QColor("#555577"), 1))
        painter.drawEllipse(QPointF(cx, cy), 5, 5)
        
        painter.setFont(QFont("Arial", 7))
        painter.setPen(QColor("#888888"))
        
        min_angle = math.radians(-135 - 90)
        min_x = cx + (radius + 14) * math.cos(min_angle)
        min_y = cy + (radius + 14) * math.sin(min_angle)
        painter.drawText(QRectF(min_x - 12, min_y - 6, 24, 12),
                        Qt.AlignCenter, str(self._min_val))
        
        max_angle = math.radians(135 - 90)
        max_x = cx + (radius + 14) * math.cos(max_angle)
        max_y = cy + (radius + 14) * math.sin(max_angle)
        painter.drawText(QRectF(max_x - 12, max_y - 6, 24, 12),
                        Qt.AlignCenter, str(self._max_val))
        
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.setPen(QColor(0, 255, 65, 200))
        label_rect = QRectF(0, 95, self.width(), 18)
        painter.drawText(label_rect, Qt.AlignCenter, self._label)
        
        val_text = f"{int(self._target_value)}{self._unit}"
        painter.setFont(QFont("Courier New", 9, QFont.Bold))
        painter.setPen(QColor(0, 200, 50, 180))
        val_rect = QRectF(0, 112, self.width(), 16)
        painter.drawText(val_rect, Qt.AlignCenter, val_text)
        painter.end()

class Button(QPushButton):
    def __init__(self, text, parent=None, color="#00cc33", size_hint=None):
        super().__init__(text, parent)
        self._hover = False
        self._pressed = False
        self._color = QColor(color)
        self._scale = 1.0
        self._target_scale = 1.0
        if size_hint:
            self.setMinimumSize(*size_hint)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
    
    def enterEvent(self, event):
        self._hover = True
        self._target_scale = 1.05
    
    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self._target_scale = 1.0
    
    def mousePressEvent(self, event):
        self._pressed = True
        self._target_scale = 0.95
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._pressed = False
        self._target_scale = 1.05 if self._hover else 1.0
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        cx = rect.center().x()
        cy = rect.center().y()
        painter.translate(cx, cy)
        painter.scale(self._scale, self._scale)
        painter.translate(-cx, -cy)
        r = rect.adjusted(4, 4, -4, -4)
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 80)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(r.adjusted(2, 3, 2, 3), 8, 8)
        
        gradient = QLinearGradient(r.left(), r.top(), r.left(), r.bottom())
        base_color = self._color
        if self._pressed:
            gradient.setColorAt(0, base_color.darker(130))
            gradient.setColorAt(1, base_color.darker(150))
        elif self._hover:
            gradient.setColorAt(0, base_color.lighter(120))
            gradient.setColorAt(1, base_color)
        else:
            gradient.setColorAt(0, base_color)
            gradient.setColorAt(1, base_color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(base_color.lighter(150), 1))
        painter.drawRoundedRect(r, 8, 8)
        
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.setPen(QColor(255, 255, 255, 255))
        painter.drawText(r, Qt.AlignCenter, self.text())
        painter.end()

class RadioOption(QWidget):
    clicked = pyqtSignal()
    def __init__(self, text, parent=None, checked=False):
        super().__init__(parent)
        self._text = text
        self._checked = checked
        self._hover = False
        self._anim_value = 1.0 if checked else 0.0
        self._target_anim = self._anim_value
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
    
    def _animate(self):
        diff = self._target_anim - self._anim_value
        if abs(diff) > 0.01:
            self._anim_value += diff * 0.2
            self.update()
    
    def set_checked(self, checked):
        self._checked = checked
        self._target_anim = 1.0 if checked else 0.0
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
    
    def enterEvent(self, event):
        self._hover = True
        self.update()
    
    def leaveEvent(self, event):
        self._hover = False
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        circle_r = 9
        circle_x = 14
        circle_y = rect.center().y()
        
        if self._hover:
            painter.setPen(QPen(QColor(0, 212, 255, 150), 2))
        else:
            painter.setPen(QPen(QColor("#555577"), 1.5))
        
        if self._anim_value > 0.5:
            painter.setBrush(QBrush(QColor(0, 255, 65, 200)))
        else:
            painter.setBrush(QBrush(QColor("#2a2a4a")))
        painter.drawEllipse(QPointF(circle_x, circle_y), circle_r, circle_r)
        
        if self._anim_value > 0.3:
            inner_r = circle_r * 0.5 * self._anim_value
            painter.setBrush(QBrush(QColor(0, 255, 65, 255)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(circle_x, circle_y), inner_r, inner_r)
        
        painter.setFont(QFont("Arial", 11))
        painter.setPen(QColor(0, 255, 65, 220) if self._checked else QColor("#aaaaaa"))
        text_rect = QRectF(circle_x + circle_r + 8, rect.top(),
                          rect.width() - circle_x - circle_r - 8, rect.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._text)
        painter.end()

class RadioGroup(QWidget):
    selectionChanged = pyqtSignal(int)
    def __init__(self, options, default_index=0, parent=None):
        super().__init__(parent)
        self._options = options
        self._selected_index = default_index
        self._buttons = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        for i, (text, value) in enumerate(options):
            btn = RadioOption(text, checked=(i == default_index))
            btn.clicked.connect(lambda idx=i: self._select(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)
    
    def _select(self, index):
        if index == self._selected_index:
            return
        self._selected_index = index
        for i, btn in enumerate(self._buttons):
            btn.set_checked(i == index)
        self.selectionChanged.emit(index)
    
    @property
    def selected_index(self):
        return self._selected_index

class Oscilloscope(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer = np.zeros((4096, 2))
        self._running = False
        self._active_channel = "both"
        self._signal_type = "sine"
        self._freq = 1000
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)
        self.setMinimumHeight(150)
    
    def set_buffer(self, buffer):
        self._buffer = buffer
    
    def set_running(self, running):
        self._running = running
    
    def set_active_channel(self, channel):
        self._active_channel = channel
        
    def set_signal_info(self, signal_type, freq):
        self._signal_type = signal_type
        self._freq = freq
    
    def _get_polygon(self, channel_data, rect, center_y):
        num_points = len(channel_data)
        if num_points == 0:
            return QPolygonF()
            
        # 1. ФИКСИРОВАННЫЙ МАСШТАБ (окно времени)
        # Всегда показываем примерно 30 периодов сигнала для наглядности
        # Но ограничиваем окно размером буфера
        if self._freq > 0:
            samples_per_period = 44100.0 / self._freq
            window_size = int(samples_per_period * 30) # 30 периодов
        else:
            window_size = 2048
            
        window_size = min(window_size, num_points)
        window_size = max(window_size, 100) # минимум 100 сэмплов
        
        # 2. ТРИГГЕР (поиск перехода через ноль)
        # Чтобы волна не "бежала" по экрану
        start_idx = 0
        search_limit = num_points - window_size
        if search_limit > 0 and self._signal_type != "noise" and self._freq > 0:
            for i in range(1, search_limit):
                if channel_data[i-1] <= 0 and channel_data[i] > 0:
                    start_idx = i
                    break
                    
        display_data = channel_data[start_idx : start_idx + window_size]
        if len(display_data) == 0:
            return QPolygonF()
            
        actual_points = len(display_data)
        pixels = rect.width()
        samples_per_pixel = actual_points / pixels
        
        points = []
        if samples_per_pixel > 1.5:
            # Пиковое детектирование (Min/Max)
            for x_pix in range(int(pixels)):
                start_s = int(x_pix * samples_per_pixel)
                end_s = int((x_pix + 1) * samples_per_pixel)
                if start_s >= actual_points: break
                
                chunk = display_data[start_s:end_s]
                if len(chunk) == 0: continue
                
                v_min = np.min(chunk)
                v_max = np.max(chunk)
                
                x = rect.left() + x_pix
                y_min = center_y - v_max * (rect.height() / 2 - 10)
                y_max = center_y - v_min * (rect.height() / 2 - 10)
                
                points.append(QPointF(x, y_min))
                points.append(QPointF(x, y_max))
        else:
            # Обычная отрисовка (для низких частот)
            for i in range(actual_points):
                val = display_data[i]
                x = rect.left() + (i / actual_points) * pixels
                y = center_y - val * (rect.height() / 2 - 10)
                points.append(QPointF(x, y))
                
        return QPolygonF(points)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        
        bg_gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        bg_gradient.setColorAt(0, QColor("#0a0a15"))
        bg_gradient.setColorAt(1, QColor("#050510"))
        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)
        
        painter.setPen(QPen(QColor("#1a1a33"), 1))
        grid_spacing_x = rect.width() / 10
        grid_spacing_y = rect.height() / 6
        for i in range(11):
            x = rect.left() + i * grid_spacing_x
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for i in range(7):
            y = rect.top() + i * grid_spacing_y
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        
        painter.setPen(QPen(QColor("#333355"), 1))
        center_y = rect.center().y()
        painter.drawLine(QPointF(rect.left(), center_y), QPointF(rect.right(), center_y))
        
        if not self._running:
            painter.end()
            return
        
        if self._active_channel in ["both", "left"]:
            painter.setPen(QPen(QColor(0, 255, 65, 200), 2))
            poly_left = self._get_polygon(self._buffer[:, 0], rect, center_y)
            if not poly_left.isEmpty():
                painter.drawPolyline(poly_left)
        
        if self._active_channel in ["both", "right"]:
            painter.setPen(QPen(QColor(0, 212, 255, 200), 2))
            poly_right = self._get_polygon(self._buffer[:, 1], rect, center_y)
            if not poly_right.isEmpty():
                painter.drawPolyline(poly_right)
        
        # Вывод информации о масштабе времени (30 периодов)
        if self._freq > 0 and self._signal_type != "noise":
            samples_per_period = 44100.0 / self._freq
            time_us = (samples_per_period * 30 / 44100.0) * 1000000
            if time_us < 1000:
                time_text = f"{time_us:.0f} мкс"
            else:
                time_text = f"{time_us/1000:.1f} мс"
            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor("#888888"))
            painter.drawText(rect.right() - 60, rect.bottom() - 10, time_text)
        elif self._signal_type == "noise":
            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor("#888888"))
            painter.drawText(rect.right() - 60, rect.bottom() - 10, "Шум")

        painter.setFont(QFont("Arial", 9, QFont.Bold))
        if self._active_channel in ["both", "left"]:
            painter.setPen(QColor(0, 255, 65, 200))
            painter.drawText(rect.left() + 8, rect.top() + 16, "L")
        if self._active_channel in ["both", "right"]:
            painter.setPen(QColor(0, 212, 255, 200))
            painter.drawText(rect.left() + 8, rect.top() + 30, "R")
        painter.end()

class VUMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0
        self._target_level = 0
        self._peak = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)
        self.setFixedSize(22, 110)
    
    def _animate(self):
        diff = self._target_level - self._level
        if abs(diff) > 0.5:
            self._level += diff * 0.1
        else:
            self._level = self._target_level
        if self._level > self._peak:
            self._peak = self._level
        else:
            self._peak = max(0, self._peak - 0.5)
        self.update()
    
    def set_level(self, level):
        self._target_level = max(0, min(100, level))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        bar_width = rect.width() - 4
        bar_height = rect.height() - 4
        
        painter.setBrush(QBrush(QColor("#0a0a15")))
        painter.setPen(QPen(QColor("#333355"), 1))
        painter.drawRoundedRect(rect, 4, 4)
        
        num_segments = 20
        segment_height = bar_height / num_segments
        filled_segments = int((self._level / 100) * num_segments)
        
        for i in range(num_segments):
            y = rect.bottom() - 2 - (i + 1) * segment_height
            seg_rect = QRectF(2, y, bar_width, segment_height - 1)
            if i < filled_segments:
                ratio = i / num_segments
                if ratio < 0.6:
                    color = QColor(0, 255, 65, 200)
                elif ratio < 0.85:
                    color = QColor(255, 200, 0, 200)
                else:
                    color = QColor(255, 0, 64, 200)
                painter.setBrush(QBrush(color))
            else:
                painter.setBrush(QBrush(QColor("#1a1a2e")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(seg_rect, 2, 2)
        
        if self._peak > 0:
            peak_y = rect.bottom() - 2 - (self._peak / 100) * bar_height
            painter.setPen(QPen(QColor(255, 255, 0, 200), 2))
            painter.drawLine(QPointF(2, peak_y), QPointF(rect.right() - 2, peak_y))
        painter.end()

class LEDWithLabel(QWidget):
    def __init__(self, parent=None, color="#00ff41", label=""):
        super().__init__(parent)
        self._on = False
        self._color = QColor(color)
        self._label = label
        self._pulse = 0
        self._brightness = 0
        self._target_brightness = 0
        
        self.setFixedSize(90, 22)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(30)
    
    def _update(self):
        self._pulse = (self._pulse + 0.15) % (2 * math.pi)
        diff = self._target_brightness - self._brightness
        if abs(diff) > 0.01:
            self._brightness += diff * 0.15
        self.update()
    
    def set_on(self, on):
        self._on = on
        self._target_brightness = 1.0 if on else 0.0
    
    def paintEvent(self, event):
        if self.width() < 5 or self.height() < 5:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        cx = 11
        cy = self.height() / 2
        r = 6
        
        if self._brightness > 0.1:
            glow_r = r + 3 + 2 * math.sin(self._pulse)
            glow_color = QColor(self._color.red(), self._color.green(),
                              self._color.blue(), int(60 * self._brightness))
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)
        
        gradient = QRadialGradient(cx - 2, cy - 2, r)
        if self._brightness > 0.5:
            gradient.setColorAt(0, self._color.lighter(150))
            gradient.setColorAt(0.5, self._color)
            gradient.setColorAt(1, self._color.darker(150))
        else:
            gradient.setColorAt(0, QColor("#444444"))
            gradient.setColorAt(1, QColor("#222222"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawEllipse(QPointF(cx, cy), r, r)
        
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QColor("#888888"))
        painter.drawText(QRectF(24, 0, self.width() - 24, self.height()),
                        Qt.AlignVCenter | Qt.AlignLeft, self._label)
        painter.end()

# ============================================================
# ГЛАВНОЕ ОКНО
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Генератор сигналов звуковой частоты — ГСЧ4-01")
        self.setMinimumSize(950, 850)
        self.resize(1000, 880)
        
        self.engine = AudioEngine()
        self._running = False
        self._active_channel = "both"
        self._edit_channel = "both"
        self._signal_type = "sine"
        
        self._init_ui()
        self._start_visualization_timer()
    
    def _init_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #12121f;")
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a3e, stop:0.5 #2a2a5e, stop:1 #1a1a3e);
                border: 1px solid #3a3a6a; border-radius: 8px;
            }
        """)
        title_layout = QHBoxLayout(title_frame)
        title_label = QLabel(" Генератор сигналов звуковой частоты")
        title_label.setStyleSheet("color: #00d4ff; font-size: 18px; font-weight: bold; padding: 8px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        model_label = QLabel("ГСЧ4-01")
        model_label.setStyleSheet("""
            color: #ffd700; font-size: 14px; font-weight: bold;
            background: #0a0a1a; border: 1px solid #333355;
            border-radius: 4px; padding: 5px 12px;
        """)
        title_layout.addWidget(model_label)
        main_layout.addWidget(title_frame)
        
        display_frame = QFrame()
        display_frame.setStyleSheet("background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 6px;")
        display_layout = QHBoxLayout(display_frame)
        display_layout.setContentsMargins(15, 15, 15, 15)
        display_layout.setSpacing(20)
        
        left_group = QGroupBox("Левый канал")
        left_group.setStyleSheet(self._get_groupbox_style("#00ff41"))
        left_layout = QHBoxLayout(left_group)
        self.left_freq_display = DigitDisplay(suffix="Гц", mode="freq")
        self.left_freq_display.set_value(1000)
        left_layout.addWidget(self.left_freq_display)
        self.left_amp_display = DigitDisplay(suffix="мВ", max_value=999, mode="amp")
        self.left_amp_display.set_value(100)
        left_layout.addWidget(self.left_amp_display)
        display_layout.addWidget(left_group)
        
        right_group = QGroupBox("Правый канал")
        right_group.setStyleSheet(self._get_groupbox_style("#00d4ff"))
        right_layout = QHBoxLayout(right_group)
        self.right_freq_display = DigitDisplay(suffix="Гц", mode="freq")
        self.right_freq_display.set_value(1000)
        right_layout.addWidget(self.right_freq_display)
        self.right_amp_display = DigitDisplay(suffix="мВ", max_value=999, mode="amp")
        self.right_amp_display.set_value(100)
        right_layout.addWidget(self.right_amp_display)
        display_layout.addWidget(right_group)
        main_layout.addWidget(display_frame)
        
        control_frame = QFrame()
        control_frame.setStyleSheet("background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 6px;")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(15)
        
        channel_group = QGroupBox("Канал")
        channel_group.setStyleSheet(self._get_groupbox_style("#00d4ff"))
        channel_layout = QVBoxLayout(channel_group)
        self.channel_group = RadioGroup(
            [("Левый/Правый", "both"), ("Левый канал", "left"), ("Правый канал", "right")],
            default_index=0
        )
        self.channel_group.selectionChanged.connect(self._on_channel_changed)
        channel_layout.addWidget(self.channel_group)
        control_layout.addWidget(channel_group)
        
        signal_group = QGroupBox("Вид сигнала")
        signal_group.setStyleSheet(self._get_groupbox_style("#00d4ff"))
        signal_layout = QVBoxLayout(signal_group)
        self.signal_group = RadioGroup(
            [("Синусоида", "sine"), ("Прямоугольный", "square"), 
             ("Треугольный", "triangle"), ("Пилообразный", "sawtooth"), ("Белый шум", "noise")],
            default_index=0
        )
        self.signal_group.selectionChanged.connect(self._on_signal_changed)
        signal_layout.addWidget(self.signal_group)
        control_layout.addWidget(signal_group)
        
        right_panel = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_start = Button("Старт", color="#00cc33", size_hint=(100, 45))
        self.btn_start.clicked.connect(self._on_start)
        btn_layout.addWidget(self.btn_start)
        self.btn_stop = Button("Стоп", color="#cc0033", size_hint=(100, 45))
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_stop)
        self.btn_exit = Button("Выход", color="#ff6600", size_hint=(80, 45))
        self.btn_exit.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_exit)
        right_panel.addLayout(btn_layout)
        control_layout.addLayout(right_panel)
        main_layout.addWidget(control_frame)
        
        osc_label = QLabel("Осциллограф")
        osc_label.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold;")
        main_layout.addWidget(osc_label)
        self.oscilloscope = Oscilloscope()
        main_layout.addWidget(self.oscilloscope)
        
        knobs_frame = QFrame()
        knobs_frame.setStyleSheet("background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 6px;")
        knobs_layout = QHBoxLayout(knobs_frame)
        knobs_layout.setContentsMargins(15, 15, 15, 15)
        knobs_layout.setSpacing(15)
        
        self.knob_1k = Knob(label="1x1кГц", min_val=0, max_val=20, default=1, unit="кГц")
        self.knob_1k.valueChanged.connect(self._update_frequency)
        knobs_layout.addWidget(self.knob_1k)
        
        self.knob_100 = Knob(label="1x100Гц", min_val=0, max_val=9, default=0, unit="Гц")
        self.knob_100.valueChanged.connect(self._update_frequency)
        knobs_layout.addWidget(self.knob_100)
        
        self.knob_1 = Knob(label="1x1Гц", min_val=0, max_val=99, default=0, unit="Гц")
        self.knob_1.valueChanged.connect(self._update_frequency)
        knobs_layout.addWidget(self.knob_1)
        
        self.knob_amp = Knob(label="Амплитуда (мВ)", min_val=0, max_val=100, default=20, unit="мВ")
        self.knob_amp.valueChanged.connect(self._update_amplitude)
        knobs_layout.addWidget(self.knob_amp)
        
        vu_layout = QVBoxLayout()
        vu_label = QLabel("Уровень")
        vu_label.setStyleSheet("color: #888888; font-size: 10px;")
        vu_label.setAlignment(Qt.AlignCenter)
        vu_layout.addWidget(vu_label)
        vu_row = QHBoxLayout()
        self.vu_left = VUMeter()
        self.vu_right = VUMeter()
        vu_row.addWidget(self.vu_left)
        vu_row.addWidget(self.vu_right)
        vu_layout.addLayout(vu_row)
        knobs_layout.addLayout(vu_layout)
        
        led_layout = QVBoxLayout()
        led_layout.setSpacing(8)
        self.led_power = LEDWithLabel(color="#00ff41", label="PWR")
        self.led_power.set_on(True)
        led_layout.addWidget(self.led_power)
        self.led_signal = LEDWithLabel(color="#00d4ff", label="SIG")
        led_layout.addWidget(self.led_signal)
        self.led_clip = LEDWithLabel(color="#ff0040", label="CLIP")
        led_layout.addWidget(self.led_clip)
        knobs_layout.addLayout(led_layout)
        
        main_layout.addWidget(knobs_frame)
        
        self.status_label = QLabel("Готов к работе | Space: старт/стоп")
        self.status_label.setStyleSheet("""
            color: #888888; font-size: 11px; padding: 4px 10px;
            background: #0a0a15; border-radius: 4px;
        """)
        main_layout.addWidget(self.status_label)
        
        self._update_frequency()
        self._update_amplitude()
        self._update_channel_visuals()
    
    def _get_groupbox_style(self, color):
        return f"""
            QGroupBox {{
                border: 1px solid #2a2a4a; border-radius: 6px;
                margin-top: 12px; padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: 0 12px; color: {color}; font-size: 12px; font-weight: bold;
            }}
        """
    
    def _update_channel_visuals(self):
        if self._edit_channel == "left":
            self.left_freq_display.set_dimmed(False)
            self.left_amp_display.set_dimmed(False)
            self.right_freq_display.set_dimmed(True)
            self.right_amp_display.set_dimmed(True)
        elif self._edit_channel == "right":
            self.left_freq_display.set_dimmed(True)
            self.left_amp_display.set_dimmed(True)
            self.right_freq_display.set_dimmed(False)
            self.right_amp_display.set_dimmed(False)
        else:
            self.left_freq_display.set_dimmed(False)
            self.left_amp_display.set_dimmed(False)
            self.right_freq_display.set_dimmed(False)
            self.right_amp_display.set_dimmed(False)
    
    def _get_knob_frequency(self):
        freq = (self.knob_1k.get_value() * 1000 + 
                self.knob_100.get_value() * 100 + 
                self.knob_1.get_value())
        return min(freq, 20000)
    
    def _update_frequency(self):
        freq = self._get_knob_frequency()
        
        if self._edit_channel in ["both", "left"]:
            self.engine.freq_left = float(freq)
            self.left_freq_display.set_value(freq)
        
        if self._edit_channel in ["both", "right"]:
            self.engine.freq_right = float(freq)
            self.right_freq_display.set_value(freq)
    
    def _update_amplitude(self):
        amp_mv = self.knob_amp.get_value()
        amp_linear = amp_mv / 100.0
        
        if self._edit_channel in ["both", "left"]:
            self.engine.amp_left = amp_linear
            self.left_amp_display.set_value(amp_mv)
        
        if self._edit_channel in ["both", "right"]:
            self.engine.amp_right = amp_linear
            self.right_amp_display.set_value(amp_mv)
    
    def _on_channel_changed(self, index):
        channel = ["both", "left", "right"][index]
        self._active_channel = channel
        self.engine.channel_mode = channel
        
        if channel == "both":
            if self._edit_channel == "left":
                self.engine.freq_right = self.engine.freq_left
                self.engine.amp_right = self.engine.amp_left
                self.right_freq_display.set_value(int(self.engine.freq_left))
                self.right_amp_display.set_value(int(self.engine.amp_left * 100))
            elif self._edit_channel == "right":
                self.engine.freq_left = self.engine.freq_right
                self.engine.amp_left = self.engine.amp_right
                self.left_freq_display.set_value(int(self.engine.freq_right))
                self.left_amp_display.set_value(int(self.engine.amp_right * 100))
            self._edit_channel = "both"
        elif channel == "left":
            self._edit_channel = "left"
        elif channel == "right":
            self._edit_channel = "right"
        
        self.oscilloscope.set_active_channel(channel)
        self._update_channel_visuals()
    
    def _on_signal_changed(self, index):
        signal_type = ["sine", "square", "triangle", "sawtooth", "noise"][index]
        self._signal_type = signal_type
        self.engine.signal_type = signal_type
    
    def _on_start(self):
        self.engine.start()
        if self.engine.is_playing:
            self._running = True
            self.oscilloscope.set_running(True)
            self.led_signal.set_on(True)
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_label.setText("▶ Генерация активна | Space: стоп")
            self.status_label.setStyleSheet("color: #00ff41; font-size: 11px; padding: 4px 10px; background: #0a1a0a; border-radius: 4px;")
        else:
            self.status_label.setText("Ошибка аудиоустройства!")
    
    def _on_stop(self):
        self.engine.stop()
        self._running = False
        self.oscilloscope.set_running(False)
        self.led_signal.set_on(False)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("⏹ Остановлено | Space: старт")
        self.status_label.setStyleSheet("color: #ff0040; font-size: 11px; padding: 4px 10px; background: #1a0a0a; border-radius: 4px;")
    
    def _start_visualization_timer(self):
        self.viz_timer = QTimer(self)
        self.viz_timer.timeout.connect(self._update_visuals)
        self.viz_timer.start(33)
    
    def _update_visuals(self):
        if self._running and self.engine.is_playing:
            self.oscilloscope.set_buffer(self.engine.last_buffer)
            self.oscilloscope.set_signal_info(self.engine.signal_type, self.engine.freq_left)
            
            self.vu_left.set_level(self.engine.current_level_left)
            self.vu_right.set_level(self.engine.current_level_right)
            
            if self.engine.current_level_left > 90 or self.engine.current_level_right > 90:
                self.led_clip.set_on(True)
            else:
                self.led_clip.set_on(False)
        else:
            self.vu_left.set_level(0)
            self.vu_right.set_level(0)
            self.led_clip.set_on(False)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if self._running:
                self._on_stop()
            else:
                self._on_start()
    
    def closeEvent(self, event):
        self.engine.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(18, 18, 31))
    palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.Base, QColor(26, 26, 46))
    palette.setColor(QPalette.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.Button, QColor(42, 42, 74))
    palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.Highlight, QColor(0, 212, 255))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()