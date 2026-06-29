"""
nestify/ui_qt/dialogs/cut_piece_dialog.py

Editor for a single CUT PIECE — the 2D bar piece as it appears in the nesting
(its length and the two miter/bevel ends), NOT the profile cross-section
thumbnail. Shows a large live preview of the exact piece polygon (same geometry
the nesting scene draws), lets the user edit the length and both miters, and
export the piece contour as DXF. On Save the caller applies the values to the
shared Corte so the Cuts/Nesting stay in sync.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QDoubleValidator, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
    QWidget,
)

from nestify.i18n import t
from nestify.models import Corte
from nestify import units
from nestify.bevel_geom import corte_to_bevel, vertices_local
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.widgets.corte_row import _MiterToggle


def write_piece_dxf(verts, path: str) -> None:
    """Write a closed polygon (the piece contour) to a DXF file."""
    import ezdxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline(verts, close=True)
    doc.saveas(str(path))


# Keep the shared helper importable from here for backwards compatibility.
from nestify.dxf_cache import write_piece_dxf_from_corte as _write_piece_dxf_from_corte  # noqa: E402, F401


class _PiecePreview(QWidget):
    """Large live preview of the cut piece polygon (length + miters), scaled."""

    def __init__(self, height_mm: float, parent=None) -> None:
        super().__init__(parent)
        self._H = max(1.0, float(height_mm or 50.0))
        self._corte = Corte(largo=1000.0)
        self._color: Optional[str] = None
        self.setMinimumSize(420, 200)

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
        pad = 24
        sx = (w - 2 * pad) / span_x
        sy = (h - 2 * pad) / span_y
        s = min(sx, sy)
        # Centre the (scaled) piece in the widget.
        off_x = (w - span_x * s) / 2.0
        off_y = (h - span_y * s) / 2.0

        def _map(pt):
            x = off_x + (pt[0] - minx) * s
            # Flip Y so the piece reads upright (mm Y grows downward here).
            y = off_y + (span_y - (pt[1] - miny)) * s
            return QPointF(x, y)

        poly = QPolygonF([_map(v) for v in verts])
        fill = QColor(self._color) if self._color else QColor(_th.ACCENT)
        fill.setAlpha(150)
        p.setBrush(fill)
        p.setPen(QPen(QColor(_th.TEXT_PRI), 2))
        p.drawPolygon(poly)
        p.end()


class CutPieceDialog(QDialog):
    """Edit one cut PIECE (length + miters) with a live 2D preview + DXF export."""

    def __init__(self, corte: Corte, height_mm: float,
                 color: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("edit_drawing"))
        self.setModal(True)
        self.setMinimumWidth(480)
        self._H = max(1.0, float(height_mm or 50.0))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top File menu (§27): the cut-drawing editor uses a menu bar, not the
        # profile-creator right panel — File → Export DXF / Import DXF / Save As /
        # Save. "Save" applies the edit to the shared Corte (accept); "Save As"
        # and "Export DXF" write the piece contour to a chosen .dxf; "Import DXF"
        # loads a contour and derives the piece length from its width.
        from PySide6.QtWidgets import QMenuBar
        menubar = QMenuBar(self)
        file_menu = menubar.addMenu(t("file"))
        file_menu.addAction(t("export_dxf"), self._export_dxf)
        file_menu.addAction(t("import_dxf"), self._import_dxf)
        file_menu.addSeparator()
        file_menu.addAction(t("save_as"), self._save_as_dxf)
        _save_act = file_menu.addAction(t("save"), self.accept)
        _save_act.setShortcut("Ctrl+S")
        root.setMenuBar(menubar)

        body = QVBoxLayout()
        body.setContentsMargins(14, 14, 14, 14)
        body.setSpacing(10)
        root.addLayout(body, 1)
        root = body  # everything below adds to the padded body

        # Large live preview of the actual piece polygon.
        self._preview = _PiecePreview(self._H)
        self._preview.set_color(color)
        root.addWidget(self._preview, 1)

        # Length + miter editors.
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

        self._desc = corte.descripcion

        # Bottom: just Save/Cancel — DXF export/import and Save As live in the top
        # File menu (§27), so the heavy profile-creator right panel is gone.
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

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
            descripcion=self._desc,
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
        try:
            piece = corte_to_bevel(corte)
            verts = list(vertices_local(piece, self._H))
            write_piece_dxf(verts, path)
        except Exception as exc:  # bad path / permission / disk full
            QMessageBox.critical(self, t("export_cut_dxf_title"), str(exc))
            return
        QMessageBox.information(self, t("export_cut_dxf_title"), path)

    # Save As is "export the current contour to a .dxf of my choosing" — same
    # operation as Export DXF (the cut's only persisted artifact is its DXF).
    _save_as_dxf = _export_dxf

    def _import_dxf(self) -> None:
        """Load a DXF contour and set the piece length from its overall width.

        Miter angles can't be recovered reliably from an arbitrary polyline, so
        only the length is derived; the user keeps editing the bevels parametrically.
        """
        path, _ = QFileDialog.getOpenFileName(
            self, t("import_dxf"), "", "DXF (*.dxf);;All (*.*)")
        if not path:
            return
        try:
            import ezdxf
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()
            xs = []
            for e in msp:
                if e.dxftype() == "LWPOLYLINE":
                    xs += [p[0] for p in e.get_points()]
                elif e.dxftype() == "LINE":
                    xs += [e.dxf.start.x, e.dxf.end.x]
            if not xs:
                QMessageBox.warning(self, t("import_dxf"), t("import_error"))
                return
            width = max(xs) - min(xs)
            if width > 0:
                self._e_largo.setText(f"{width:.1f}")
                self._refresh_preview()
        except Exception as exc:
            QMessageBox.critical(self, t("import_error"), str(exc))

    def result_values(self) -> dict:
        c = self._current_corte()
        return {
            "largo": c.largo,
            "inglete1": c.inglete1,
            "inglete2": c.inglete2,
            "inglete1_dir": c.inglete1_dir,
            "inglete2_dir": c.inglete2_dir,
            "inglete1_deg": c.inglete1_deg,
            "inglete2_deg": c.inglete2_deg,
        }
