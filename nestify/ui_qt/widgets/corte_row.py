"""
nestify/ui_qt/widgets/corte_row.py
One row in the cuts list -- description, length, qty, 2x bevel, shape preview, delete.
"""
from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QDoubleValidator, QIntValidator, QPainter, QPainterPath, QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSizePolicy, QWidget,
)

from nestify.i18n import t
from nestify.models import Corte
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.icons import themed_icon


# Module-level preference for skipping the delete confirmation dialog.
_skip_delete_confirm: bool = False


def _default_cut_name(n: int) -> str:
    return t("default_cut_name", n=n)


# ---------------------------------------------------------------------------
# _MiterToggle -- tiny painted toggle between up/down arrow
# ---------------------------------------------------------------------------

class _MiterToggle(QWidget):
    """Tiny custom-painted toggle showing an up/down arrow; click flips it.

    Fixed 28×26 px; the arrow direction encodes the bevel/miter side and is
    drawn in paintEvent (so it follows the theme).
    """

    toggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._up = True
        self.setFixedSize(28, 26)   # fixed footprint so the bevel group stays compact
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # -- public api --------------------------------------------------------

    def is_up(self) -> bool:
        return self._up

    def set_up(self, up: bool) -> None:
        if self._up != up:
            self._up = up
            self.update()
            self.toggled.emit()

    # -- events ------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._up = not self._up
        self.update()
        self.toggled.emit()

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Background pill
        path = QPainterPath()
        r = h / 2.0
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
        p.fillPath(path, QColor(_th.BG_CARD))
        p.setPen(QPen(QColor(_th.BORDER), 1.0))
        p.drawPath(path)

        # Arrow glyph
        cx, cy = w / 2.0, h / 2.0
        arrow_h = 5.0
        arrow_w = 5.0

        if self._up:
            # upward arrow  ^
            tri = QPolygonF([
                QPointF(cx, cy - arrow_h),
                QPointF(cx - arrow_w, cy + arrow_h * 0.3),
                QPointF(cx + arrow_w, cy + arrow_h * 0.3),
            ])
        else:
            # downward arrow  v
            tri = QPolygonF([
                QPointF(cx, cy + arrow_h),
                QPointF(cx - arrow_w, cy - arrow_h * 0.3),
                QPointF(cx + arrow_w, cy - arrow_h * 0.3),
            ])

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(_th.TEXT_PRI))
        p.drawPolygon(tri)
        p.end()


# ---------------------------------------------------------------------------
# ShapePreview -- bevel visualisation
# ---------------------------------------------------------------------------

class ShapePreview(QWidget):
    """Small custom-painted preview of a cut's outline (with its bevels).

    Fixed 52×28 px thumbnail at the right end of a CorteRow; paintEvent draws
    the trapezoid implied by the two miter angles/directions so the user sees
    the piece shape without opening a dialog.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(52, 28)   # fixed thumbnail size in the row's last column
        self._inglete1 = False
        self._inglete2 = False
        self._dir1_up = True
        self._dir2_up = True
        self._deg1 = 45.0
        self._deg2 = 45.0
        self._fill_color: str | None = None

    def set_color(self, color: str | None) -> None:
        self._fill_color = color
        self.update()

    def update_from(
        self, i1: bool, i2: bool, d1_up: bool, d2_up: bool,
        deg1: float, deg2: float,
    ) -> None:
        self._inglete1 = i1
        self._inglete2 = i2
        self._dir1_up = d1_up
        self._dir2_up = d2_up
        self._deg1 = max(5.0, min(85.0, deg1))
        self._deg2 = max(5.0, min(85.0, deg2))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        # 4px pad inset on every side; bar_h is the drawable height between the
        # top and bottom pads — it sets the vertical run of each miter cut.
        pad = 4
        bar_h = h - pad * 2

        def _bevel_offset(deg: float) -> float:
            """Horizontal run of a miter cut: bar_h / tan(angle).

            A near-square cut (deg→90°) has ~0 horizontal offset; shallow angles
            push the cut further along the bar. Returns 0 above 89° to avoid the
            tan() blow-up."""
            return bar_h / math.tan(math.radians(deg)) if deg < 89 else 0.0

        b1 = _bevel_offset(self._deg1) if self._inglete1 else 0.0
        b2 = _bevel_offset(self._deg2) if self._inglete2 else 0.0

        x0 = pad
        x1 = w - pad
        bar_w = x1 - x0
        yt = pad
        yb = h - pad

        # Clamp each offset to 45% of the bar width so the two end cuts can never
        # cross and the shape stays a valid (non-self-intersecting) quadrilateral.
        max_off = bar_w * 0.45
        b1 = min(b1, max_off)
        b2 = min(b2, max_off)

        # 4-point trapezoid: miter cuts inward, preserving piece length.
        # "up" = cut from top edge inward; "down" = cut from bottom edge inward.
        tl_x = x0 + (b1 if self._dir1_up else 0.0)
        bl_x = x0 + (b1 if not self._dir1_up else 0.0)
        tr_x = x1 - (b2 if self._dir2_up else 0.0)
        br_x = x1 - (b2 if not self._dir2_up else 0.0)

        poly = QPolygonF([
            QPointF(tl_x, yt), QPointF(tr_x, yt),
            QPointF(br_x, yb), QPointF(bl_x, yb),
        ])

        fill = QColor(self._fill_color) if self._fill_color else QColor(_th.BG_CARD)
        p.setPen(QPen(QColor(_th.ACCENT), 1.5))
        p.setBrush(fill)
        p.drawPolygon(poly)
        p.end()


# ---------------------------------------------------------------------------
# CorteRow -- one row in the cuts editor
# ---------------------------------------------------------------------------

class CorteRow(QWidget):
    """One row in the cuts editor: number | description | length | qty | bevel1 | bevel2 | preview | delete."""

    changed = Signal()
    deleted = Signal(int)           # row index
    tab_from_last = Signal(int)     # row index -- Tab pressed on last field
    bevel_requested = Signal()      # a bevel checkbox was turned on (needs Bar height)

    def __init__(
        self,
        numero: int,
        corte: Optional[Corte] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._numero = numero
        # One cut as a single 44px-tall row. Width expands, height is fixed.
        # Single QGridLayout, all widgets on grid row 0; columns left→right:
        #   0 badge(24) · 1 description(stretch) · 2 length(72) · 3 qty(40) ·
        #   4 bevel-1 group · 5 bevel-2 group · 6 shape preview · 7 delete.
        # 4×2 px margins, 6px inter-column spacing. Only description has no fixed
        # width, so it absorbs the row's spare horizontal space.
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        grid = QGridLayout(self)
        grid.setContentsMargins(4, 2, 4, 2)
        grid.setSpacing(6)

        # -- Col 0: Badge — fixed 24px, centred row number, BG_MID pill, 9px dim --
        self._badge = QLabel(str(numero))
        self._badge.setFixedWidth(24)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(
            f"background:{_th.BG_MID}; color:{_th.TEXT_DIM}; border-radius:3px; font-size:9px;"
        )
        grid.addWidget(self._badge, 0, 0)

        # -- Col 1: Description — min 80px, grows to fill; placeholder = default name --
        self._desc = QLineEdit(corte.descripcion if corte else "")
        self._desc.setPlaceholderText(_default_cut_name(numero))
        self._desc.setMinimumWidth(80)
        self._desc.textChanged.connect(self._on_change)
        grid.addWidget(self._desc, 0, 1)

        # -- Col 2: Length — fixed 72px, mono, numeric validator (0–99999, 2 dp) --
        self._length = QLineEdit()
        self._length.setFixedWidth(72)
        self._length.setProperty("mono", "true")
        self._length.setPlaceholderText("Length")
        self._length.setValidator(QDoubleValidator(0, 99999, 2, self._length))
        if corte:
            self._length.setText(str(int(corte.largo)) if corte.largo else "")
        self._length.textChanged.connect(self._on_change)
        grid.addWidget(self._length, 0, 2)

        # -- Col 3: Quantity — fixed 40px, mono, integer validator (1–9999) --
        self._qty = QLineEdit("1")
        self._qty.setFixedWidth(40)
        self._qty.setProperty("mono", "true")
        self._qty.setPlaceholderText("Qty")
        self._qty.setValidator(QIntValidator(1, 9999, self._qty))
        if corte:
            self._qty.setText(str(corte.cantidad))
        self._qty.textChanged.connect(self._on_change)
        grid.addWidget(self._qty, 0, 3)

        # -- Col 4: Bevel 1 ------------------------------------------------
        self._bevel1_check = QCheckBox()
        self._bevel1_dir = _MiterToggle()
        self._bevel1_deg = QLineEdit("45")
        self._bevel1_deg.setFixedWidth(36)
        self._bevel1_deg.setProperty("mono", "true")
        self._bevel1_deg.setPlaceholderText("°")
        self._bevel1_deg.setValidator(QDoubleValidator(5, 85, 1, self._bevel1_deg))

        b1_frame = QWidget()
        b1_layout = QHBoxLayout(b1_frame)
        b1_layout.setContentsMargins(0, 0, 0, 0)
        b1_layout.setSpacing(2)
        b1_layout.addWidget(self._bevel1_check)
        b1_layout.addWidget(self._bevel1_dir)
        b1_layout.addWidget(self._bevel1_deg)
        grid.addWidget(b1_frame, 0, 4)

        # -- Col 5: Bevel 2 ------------------------------------------------
        self._bevel2_check = QCheckBox()
        self._bevel2_dir = _MiterToggle()
        self._bevel2_deg = QLineEdit("45")
        self._bevel2_deg.setFixedWidth(36)
        self._bevel2_deg.setProperty("mono", "true")
        self._bevel2_deg.setPlaceholderText("°")
        self._bevel2_deg.setValidator(QDoubleValidator(5, 85, 1, self._bevel2_deg))

        b2_frame = QWidget()
        b2_layout = QHBoxLayout(b2_frame)
        b2_layout.setContentsMargins(0, 0, 0, 0)
        b2_layout.setSpacing(2)
        b2_layout.addWidget(self._bevel2_check)
        b2_layout.addWidget(self._bevel2_dir)
        b2_layout.addWidget(self._bevel2_deg)
        grid.addWidget(b2_frame, 0, 5)

        # Populate from corte if provided
        def _deg_str(v: float) -> str:
            return str(int(v)) if v == int(v) else str(v)

        if corte:
            self._bevel1_check.setChecked(corte.inglete1)
            self._bevel2_check.setChecked(corte.inglete2)
            self._bevel1_dir.set_up(corte.inglete1_dir == "up")
            self._bevel2_dir.set_up(corte.inglete2_dir == "up")
            self._bevel1_deg.setText(_deg_str(corte.inglete1_deg))
            self._bevel2_deg.setText(_deg_str(corte.inglete2_deg))

        # -- Col 6: Shape preview ------------------------------------------
        self._preview = ShapePreview()
        grid.addWidget(self._preview, 0, 6)

        # -- Col 7: Delete button ------------------------------------------
        self._del_btn = QPushButton()
        self._del_btn.setFixedSize(28, 28)
        self._del_btn.setIcon(themed_icon("x", _th.DANGER, 12))
        self._del_btn.setIconSize(QSize(12, 12))
        self._del_btn.setToolTip(t("delete_cut"))
        self._apply_del_btn_style()
        self._del_btn.clicked.connect(self._on_delete_clicked)
        grid.addWidget(self._del_btn, 0, 7)

        # Column stretches — only description expands
        grid.setColumnStretch(1, 1)

        # Connect bevel signals
        self._bevel1_check.stateChanged.connect(self._on_bevel_change)
        self._bevel2_check.stateChanged.connect(self._on_bevel_change)
        self._bevel1_dir.toggled.connect(self._on_bevel_change)
        self._bevel2_dir.toggled.connect(self._on_bevel_change)
        self._bevel1_deg.textChanged.connect(self._on_bevel_change)
        self._bevel2_deg.textChanged.connect(self._on_bevel_change)

        # Tab on last field
        self._bevel2_deg.installEventFilter(self)

        self._update_preview()

    def focus_first(self) -> None:
        """Move keyboard focus to this row's first input (description)."""
        self._desc.setFocus(Qt.FocusReason.TabFocusReason)

    # -- Event filter for Tab from last field ------------------------------

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        from PySide6.QtCore import QEvent
        if obj is self._bevel2_deg and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab:
                self.tab_from_last.emit(self._numero - 1)
                return True
        return super().eventFilter(obj, event)

    # -- Internal ----------------------------------------------------------

    def _on_change(self) -> None:
        self.changed.emit()

    def _on_bevel_change(self) -> None:
        # When a bevel is enabled the parent tab validates that a Bar height
        # exists (bevels can't be drawn/computed without it).
        if self._bevel1_check.isChecked() or self._bevel2_check.isChecked():
            self.bevel_requested.emit()
        self._update_preview()
        self.changed.emit()

    def clear_bevels(self) -> None:
        """Uncheck both bevels without re-emitting the bevel_requested signal."""
        for chk in (self._bevel1_check, self._bevel2_check):
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)
        self._update_preview()
        self.changed.emit()

    def _on_delete_clicked(self) -> None:
        global _skip_delete_confirm
        if not _skip_delete_confirm:
            msg = QMessageBox(self)
            msg.setWindowTitle("Delete Cut")
            msg.setText(f"Delete cut {self._numero}?")
            msg.setInformativeText("This action cannot be undone.")
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            msg.setDefaultButton(QMessageBox.StandardButton.No)

            cb = QCheckBox("Don't ask again")
            msg.setCheckBox(cb)

            result = msg.exec()
            if result != QMessageBox.StandardButton.Yes:
                return
            if cb.isChecked():
                _skip_delete_confirm = True

        self.deleted.emit(self._numero - 1)

    def _apply_del_btn_style(self) -> None:
        self._del_btn.setStyleSheet(
            f"QPushButton {{ "
            f"  background-color: {_th.DANGER_BG}; "
            f"  border: 1px solid {_th.DANGER_BORDER}; border-radius: 4px; "
            f"  padding: 0px; min-height: 0px; min-width: 0px; "
            f"}} "
            f"QPushButton:hover {{ background-color: {_th.DANGER_HVR}; }}"
        )

    def refresh_theme(self) -> None:
        self._badge.setStyleSheet(
            f"background:{_th.BG_MID}; color:{_th.TEXT_DIM}; border-radius:3px; font-size:9px;"
        )
        self._del_btn.setIcon(themed_icon("x", _th.DANGER, 12))
        self._apply_del_btn_style()

    def _update_preview(self) -> None:
        try:
            deg1 = float(self._bevel1_deg.text() or "45")
        except ValueError:
            deg1 = 45.0
        try:
            deg2 = float(self._bevel2_deg.text() or "45")
        except ValueError:
            deg2 = 45.0
        self._preview.update_from(
            self._bevel1_check.isChecked(),
            self._bevel2_check.isChecked(),
            self._bevel1_dir.is_up(),
            self._bevel2_dir.is_up(),
            deg1, deg2,
        )

    # -- Public API --------------------------------------------------------

    def sizeHint(self) -> QSize:
        return QSize(600, 38)

    def set_numero(self, n: int) -> None:
        self._numero = n

    def get_corte(self) -> Optional[Corte]:
        try:
            largo = float(self._length.text() or "0")
            if largo <= 0:
                return None
            cantidad = int(self._qty.text() or "1")
            try:
                deg1 = float(self._bevel1_deg.text() or "45")
            except ValueError:
                deg1 = 45.0
            try:
                deg2 = float(self._bevel2_deg.text() or "45")
            except ValueError:
                deg2 = 45.0
            return Corte(
                descripcion=self._desc.text() or f"Cut {self._numero}",
                largo=largo,
                cantidad=cantidad,
                inglete1=self._bevel1_check.isChecked(),
                inglete2=self._bevel2_check.isChecked(),
                inglete1_dir="up" if self._bevel1_dir.is_up() else "down",
                inglete2_dir="up" if self._bevel2_dir.is_up() else "down",
                inglete1_deg=deg1,
                inglete2_deg=deg2,
            )
        except (ValueError, TypeError):
            return None

    def set_corte(self, corte: Corte) -> None:
        self._desc.blockSignals(True)
        self._length.blockSignals(True)
        self._qty.blockSignals(True)
        self._desc.setText(corte.descripcion)
        self._length.setText(str(int(corte.largo)) if corte.largo else "")
        self._qty.setText(str(corte.cantidad))
        self._bevel1_check.setChecked(corte.inglete1)
        self._bevel2_check.setChecked(corte.inglete2)
        self._bevel1_dir.set_up(corte.inglete1_dir == "up")
        self._bevel2_dir.set_up(corte.inglete2_dir == "up")
        self._bevel1_deg.setText(str(corte.inglete1_deg))
        self._bevel2_deg.setText(str(corte.inglete2_deg))
        self._desc.blockSignals(False)
        self._length.blockSignals(False)
        self._qty.blockSignals(False)
        self._update_preview()

    def set_preview_color(self, color: str | None) -> None:
        self._preview.set_color(color)
