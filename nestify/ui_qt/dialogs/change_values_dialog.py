"""
nestify/ui_qt/dialogs/change_values_dialog.py

Merged dialog combining the old "Change values" compact editor and the
"Edit drawing" piece viewer into one coherent panel:

  • Description + Quantity (top)
  • Large live 2D piece preview (center)
  • Length + Bevel 1 + Bevel 2 editors (bottom)
  • Export DXF  |  Save  |  Cancel

Returns the edited values; the caller applies them to the shared Corte so
the Cuts tab stays in sync.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QDoubleValidator, QIntValidator, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from nestify.i18n import t
from nestify.models import Corte
from nestify import units
from nestify.bevel_geom import corte_to_bevel, vertices_local
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.widgets.corte_row import _MiterToggle


# ── Large live piece preview (reused from cut_piece_dialog) ──────────────────

class _PiecePreview(QWidget):
    """Large live preview of the cut piece polygon (length + miters), scaled."""

    def __init__(self, height_mm: float, parent=None) -> None:
        super().__init__(parent)
        self._H = max(1.0, float(height_mm or 50.0))
        self._corte = Corte(largo=1000.0)
        self._color: Optional[str] = None
        self.setMinimumSize(420, 180)

    def set_color(self, color: Optional[str]) -> None:
        self._color = color
        self.update()

    def set_corte(self, corte: Corte) -> None:
        self._corte = corte
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(_th.BG_CANVAS))

        try:
            piece = corte_to_bevel(self._corte)
            verts = list(vertices_local(piece, self._H))
        except Exception:
            verts = [(0, 0), (self._corte.largo, 0),
                     (self._corte.largo, self._H), (0, self._H)]
        if not verts:
            p.end()
            return

        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        span_x = max(1.0, maxx - minx)
        span_y = max(1.0, maxy - miny)
        pad = 20
        sx = (w - 2 * pad) / span_x
        sy = (h - 2 * pad) / span_y
        s = min(sx, sy)
        off_x = (w - span_x * s) / 2.0
        off_y = (h - span_y * s) / 2.0

        def _map(pt):
            x = off_x + (pt[0] - minx) * s
            y = off_y + (span_y - (pt[1] - miny)) * s
            return QPointF(x, y)

        poly = QPolygonF([_map(v) for v in verts])
        fill = QColor(self._color) if self._color else QColor(_th.ACCENT)
        fill.setAlpha(150)
        p.setBrush(fill)
        p.setPen(QPen(QColor(_th.TEXT_PRI), 2))
        p.drawPolygon(poly)
        p.end()


# ── Dialog ───────────────────────────────────────────────────────────────────

class ChangeValuesDialog(QDialog):
    """Merged editor: description, qty, large piece preview, length, bevels, DXF export."""

    def __init__(self, corte: Corte, qty: int,
                 color: Optional[str] = None,
                 height_mm: float = 50.0,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("change_values"))
        self.setModal(True)
        self.setMinimumWidth(480)
        self._H = max(1.0, float(height_mm or 50.0))
        self._desc_orig = corte.descripcion or ""

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── Top: Description + Qty ────────────────────────────────────────
        top = QGridLayout()
        top.setHorizontalSpacing(8)
        top.setVerticalSpacing(6)
        self._e_desc = QLineEdit(corte.descripcion or "")
        self._e_qty  = QLineEdit(str(qty))
        self._e_qty.setValidator(QIntValidator(0, 99999, self))
        for w in (self._e_desc, self._e_qty):
            w.setFixedHeight(30)
        top.addWidget(QLabel(t("description")), 0, 0)
        top.addWidget(self._e_desc, 0, 1)
        top.addWidget(QLabel(t("placeholder_qty")), 1, 0)
        top.addWidget(self._e_qty, 1, 1)
        root.addLayout(top)

        # ── Large live preview ────────────────────────────────────────────
        self._preview = _PiecePreview(self._H)
        if color:
            self._preview.set_color(color)
        root.addWidget(self._preview, 1)

        # ── Length + Bevels ───────────────────────────────────────────────
        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        self._e_largo = QLineEdit(str(corte.largo))
        self._e_largo.setValidator(QDoubleValidator(0.0, 1e6, 2, self))
        self._e_largo.setFixedHeight(30)
        form.addWidget(QLabel(t("placeholder_length", u=units.u_len())), 0, 0)
        form.addWidget(self._e_largo, 0, 1)
        root.addLayout(form)

        self._b1_check, self._b1_dir, self._b1_deg = self._make_bevel_row(
            root, t("bevel_1"), corte.inglete1, corte.inglete1_dir, corte.inglete1_deg)
        self._b2_check, self._b2_dir, self._b2_deg = self._make_bevel_row(
            root, t("bevel_2"), corte.inglete2, corte.inglete2_dir, corte.inglete2_deg)

        # ── Buttons: Export DXF | Save | Cancel ──────────────────────────
        btn_row = QHBoxLayout()
        self._dxf_btn = QPushButton(t("export_cut_dxf_title"))
        self._dxf_btn.clicked.connect(self._export_dxf)
        btn_row.addWidget(self._dxf_btn)
        btn_row.addStretch(1)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btn_row.addWidget(btns)
        root.addLayout(btn_row)

        # Wire live preview updates.
        for chk in (self._b1_check, self._b2_check):
            chk.stateChanged.connect(self._refresh_preview)
        for tog in (self._b1_dir, self._b2_dir):
            tog.toggled.connect(self._refresh_preview)
        for ed in (self._b1_deg, self._b2_deg, self._e_largo):
            ed.textChanged.connect(self._refresh_preview)
        self._refresh_preview()

    def _make_bevel_row(self, root, label, enabled, direction, deg):
        row = QHBoxLayout()
        chk = QCheckBox(label)
        chk.setChecked(bool(enabled))
        dir_tog = _MiterToggle()
        dir_tog.set_up(direction != "down")
        deg_edit = QLineEdit(str(deg))
        deg_edit.setValidator(QDoubleValidator(5.0, 85.0, 1))
        deg_edit.setFixedWidth(56)
        deg_edit.setFixedHeight(30)
        row.addWidget(chk)
        row.addWidget(dir_tog)
        row.addWidget(QLabel("°"))
        row.addWidget(deg_edit)
        row.addStretch(1)
        root.addLayout(row)
        return chk, dir_tog, deg_edit

    def _deg(self, edit: QLineEdit, default: float) -> float:
        try:
            return max(5.0, min(85.0, float(edit.text() or default)))
        except ValueError:
            return default

    def _current_corte(self) -> Corte:
        try:
            largo = float(self._e_largo.text() or "0")
        except ValueError:
            largo = 0.0
        return Corte(
            descripcion=self._e_desc.text().strip(),
            largo=largo,
            inglete1=self._b1_check.isChecked(),
            inglete2=self._b2_check.isChecked(),
            inglete1_dir="up" if self._b1_dir.is_up() else "down",
            inglete2_dir="up" if self._b2_dir.is_up() else "down",
            inglete1_deg=self._deg(self._b1_deg, 45.0),
            inglete2_deg=self._deg(self._b2_deg, 45.0),
        )

    def _refresh_preview(self) -> None:
        self._preview.set_corte(self._current_corte())

    def _export_dxf(self) -> None:
        corte = self._current_corte()
        if corte.largo <= 0:
            QMessageBox.warning(self, t("export_cut_dxf_title"), t("export_cut_dxf_no_height"))
            return
        desc = (corte.descripcion or "cut").replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_cut_dxf_title"), f"{desc}.dxf", "DXF (*.dxf)")
        if not path:
            return
        from nestify.dxf_cache import write_piece_dxf_from_corte
        try:
            write_piece_dxf_from_corte(corte, self._H, path)
        except Exception as exc:  # bad path / permission / disk full
            QMessageBox.critical(self, t("export_cut_dxf_title"), str(exc))
            return
        QMessageBox.information(self, t("export_cut_dxf_title"), path)

    def result_values(self) -> dict:
        """Return the edited values (caller applies them to the shared Corte)."""
        c = self._current_corte()
        try:
            qty = int(self._e_qty.text() or "0")
        except ValueError:
            qty = 0
        return {
            "descripcion": c.descripcion,
            "largo": c.largo,
            "cantidad": qty,
            "inglete1": c.inglete1,
            "inglete2": c.inglete2,
            "inglete1_dir": c.inglete1_dir,
            "inglete2_dir": c.inglete2_dir,
            "inglete1_deg": c.inglete1_deg,
            "inglete2_deg": c.inglete2_deg,
        }
