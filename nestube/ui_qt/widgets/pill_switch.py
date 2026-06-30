"""
nestube/ui_qt/widgets/pill_switch.py
iOS-style animated pill toggle switch for Qt.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import (
    Property, QEasingCurve, QPropertyAnimation, QSize, Qt, Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

import nestube.ui_qt.theme_qt as _th


class PillSwitch(QWidget):
    """Animated pill toggle that emits `toggled(value_str)` on state change."""

    toggled = Signal(str)

    def __init__(
        self,
        on_value: str = "on",
        off_value: str = "off",
        on_text: str = "On",
        off_text: str = "Off",
        initial_value: Optional[str] = None,
        command: Optional[Callable[[str], None]] = None,
        width: int = 120,
        height: int = 28,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._on_value = on_value
        self._off_value = off_value
        self._on_text = on_text
        self._off_text = off_text
        self._command = command
        self._value = on_value if initial_value is None else initial_value
        self._knob_pos: float = 1.0 if self._value == on_value else 0.0

        self.setFixedSize(width, height)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knob_pos", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    # ── Qt property for animation ─────────────────────────────────────────────

    def _get_knob_pos(self) -> float:
        return self._knob_pos

    def _set_knob_pos(self, val: float) -> None:
        self._knob_pos = val
        self.update()

    knob_pos = Property(float, _get_knob_pos, _set_knob_pos)

    # ── Public API ────────────────────────────────────────────────────────────

    def value(self) -> str:
        return self._value

    def setValue(self, v: str, animate: bool = True) -> None:
        if v not in (self._on_value, self._off_value):
            return
        if v == self._value:
            return
        self._value = v
        target = 1.0 if v == self._on_value else 0.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._knob_pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._knob_pos = target
            self.update()

    def set_on_text(self, text: str) -> None:
        self._on_text = text
        self.update()

    def set_off_text(self, text: str) -> None:
        self._off_text = text
        self.update()

    # ── Events ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        new_val = self._off_value if self._value == self._on_value else self._on_value
        self.setValue(new_val)
        self.toggled.emit(new_val)
        if self._command:
            self._command(new_val)

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.height())

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        # Geometry derives entirely from the widget size so the switch scales
        # cleanly: pad = 3px inset of the knob from the track edge; knob diameter
        # fills the remaining height (h - 2·pad); track corner radius = h/2 so the
        # rounded rect reads as a full pill.
        pad = 3
        knob_d = h - pad * 2
        track_r = h / 2

        is_on = self._value == self._on_value
        t = self._knob_pos  # 0.0 = off, 1.0 = on

        # Track background: SUCCESS green when on, BG_CARD when off (both live _th).
        track_color = QColor(_th.SUCCESS if is_on else _th.BG_CARD)
        if not is_on:
            track_color = QColor(_th.BG_CARD)
        # Interpolate track color slightly
        track_path = QPainterPath()
        track_path.addRoundedRect(0, 0, w, h, track_r, track_r)
        p.fillPath(track_path, track_color)

        # Track border: 1px, ACCENT when on / BORDER when off.
        border_pen = QPen(QColor(_th.ACCENT if is_on else _th.BORDER))
        border_pen.setWidth(1)
        p.setPen(border_pen)
        p.drawPath(track_path)

        # Left label (off_text): 9px font, starts just past the knob's resting
        # position (pad + knob_d + 4px gap) and spans to the track midpoint;
        # dimmed (TEXT_DIM) when the switch is on. Hidden if the area is <10px.
        left_text_x = pad + knob_d + 4
        left_area_w = w // 2 - pad - knob_d // 2
        p.setPen(QPen(QColor(_th.TEXT_DIM if is_on else _th.TEXT_PRI)))
        p.setFont(self._make_font(9))
        if left_area_w > 10:
            p.drawText(
                int(left_text_x), 0,
                int(w // 2 - left_text_x), h,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._off_text,
            )

        # Right label (on_text): mirror of the left label, right-aligned in the
        # right half of the track; bright (TEXT_PRI) when on, dimmed when off.
        right_x = w // 2
        right_w = w // 2 - pad - knob_d // 2
        p.setPen(QPen(QColor(_th.TEXT_PRI if is_on else _th.TEXT_DIM)))
        if right_w > 10:
            p.drawText(
                int(right_x), 0,
                int(right_w), h,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                self._on_text,
            )

        # Knob: a white circle that slides along knob_travel (the free horizontal
        # run = width minus both pads and the knob diameter); knob_x interpolates
        # by the animated position t. A 1px BORDER outline keeps it visible
        # against the track in both themes (required by the accessibility rules).
        knob_travel = w - pad * 2 - knob_d
        knob_x = pad + t * knob_travel
        knob_path = QPainterPath()
        knob_path.addEllipse(knob_x, pad, knob_d, knob_d)
        p.fillPath(knob_path, QColor("#FFFFFF"))
        knob_pen = QPen(QColor(_th.BORDER), 1)
        p.setPen(knob_pen)
        p.drawPath(knob_path)

        p.end()

    @staticmethod
    def _make_font(size: int):
        """Return an IBM Plex Sans QFont at the given point size for the labels."""
        from PySide6.QtGui import QFont
        f = QFont("IBM Plex Sans", size)
        return f
