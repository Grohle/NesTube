"""
nestify/ui_qt/dialogs/stock_bar_picker_dialog.py
Pick a single physical stock bar to add to the nesting layout (TODO §16).

Used by the Nesting tab's "Add bar" button when "Use stock" is active. Lists
every in-stock bar in a spreadsheet-style table (one row per bar, columns for
length, quantity, reference, profile, material, quality, remnant and blocked
flags), with action buttons to add/remove quantity, create a new bar and
block/unblock the selected bar. A "Show remnants" toggle filters retales in
or out. A scaled preview of the selected bar is drawn at the bottom-left —
particularly useful for remnants (retales), where seeing the usable length at
a glance helps the operator choose. The chosen bar is returned via
:pyattr:`result_bar` (double-click or OK).
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from nestify.i18n import t
from nestify.stock_db import (
    StockBar, add_bar, get_stock, save_stock, update_bar,
)
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.nesting_scene import _text_color_for_bg


# Green fill used for remnants (mirrors the nesting scene's _RETAL_COLOR).
_RETAL_COLOR = "#2E7D32"


class _BarPreview(QWidget):
    """A small canvas that draws one stock bar to scale.

    Full bars render as a single block spanning the widget; remnants render
    the usable (retal) length as a green block against the faint outline of
    the original full bar, so the leftover proportion is immediately clear.
    All colours come from the live theme so the preview follows dark/light.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._bar: Optional[StockBar] = None
        self.setMinimumHeight(80)

    def set_bar(self, bar: Optional[StockBar]) -> None:
        self._bar = bar
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        # Background card.
        p.fillRect(self.rect(), QColor(_th.BG_CARD))
        p.setPen(QPen(QColor(_th.BORDER), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        if self._bar is None:
            p.setPen(QPen(QColor(_th.TEXT_DIM)))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       t("stock_bar_preview_none"))
            p.end()
            return

        bar = self._bar
        full_len = max(bar.length, 1.0)
        eff_len = bar.retal_length if bar.is_retal else bar.length
        eff_len = max(eff_len, 0.0)

        # Geometry: leave margins for labels; bar band is vertically centred.
        margin_x = 12
        band_h = 24
        band_y = (h - band_h) // 2
        band_w = max(w - 2 * margin_x, 1)

        # Outline of the full original bar (faint) — gives the retal context.
        p.setPen(QPen(QColor(_th.BORDER_LIT), 1))
        p.setBrush(QBrush(QColor(_th.BG_MID)))
        p.drawRect(margin_x, band_y, band_w, band_h)

        # Usable portion: full width for a whole bar, proportional for a retal.
        frac = (eff_len / full_len) if full_len > 0 else 1.0
        frac = min(max(frac, 0.02), 1.0)
        used_w = int(band_w * frac)
        fill = QColor(_RETAL_COLOR) if bar.is_retal else QColor(_th.ACCENT)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor("#000000"), 1))
        p.drawRect(margin_x, band_y, used_w, band_h)

        # Length label centred inside the usable block (contrast-aware text).
        len_text = f"{eff_len:.0f} mm"
        p.setPen(QPen(QColor(_text_color_for_bg(
            _RETAL_COLOR if bar.is_retal else _th.ACCENT))))
        p.drawText(margin_x, band_y, max(used_w, 60), band_h,
                   Qt.AlignmentFlag.AlignCenter, len_text)
        p.end()


class StockBarPickerDialog(QDialog):
    """Modal picker returning one in-stock bar to add to the layout."""

    # Column indices for the results table.
    _COL_LENGTH = 0
    _COL_QTY = 1
    _COL_REF = 2
    _COL_PROFILE = 3
    _COL_MATERIAL = 4
    _COL_QUALITY = 5
    _COL_RETAL = 6
    _COL_BLOCKED = 7

    def __init__(self, parent: QWidget = None, initial_query: str = "", *,
                 profile_name: str = "", material: str = "", quality: str = "") -> None:
        super().__init__(parent)
        self.result_bar: Optional[StockBar] = None

        # When a material is already chosen for the nesting, the list is locked to
        # that material (profile · material · quality). Empty filters → show all,
        # so the very first pick can establish the material for the whole app.
        self._f_profile = (profile_name or "").strip().lower()
        self._f_material = (material or "").strip().lower()
        self._f_quality = (quality or "").strip().lower()
        self._locked = bool(self._f_profile or self._f_material or self._f_quality)

        self.setWindowTitle(t("stock_bar_picker_title"))
        self.setMinimumSize(820, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        hint = QLabel(t("stock_bar_picker_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:10px;")
        root.addWidget(hint)

        # Show which material the list is locked to (or that picking sets it).
        from nestify.naming import format_full_name
        if self._locked:
            locked_name = format_full_name(profile_name, material, quality)
            badge = QLabel(t("stock_bar_filtered_to", name=locked_name))
        else:
            badge = QLabel(t("stock_bar_sets_material"))
        badge.setWordWrap(True)
        badge.setStyleSheet(
            f"color:{_th.ACCENT}; font-size:10px; font-weight:bold;"
        )
        root.addWidget(badge)

        # Free-text filter.
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("search_placeholder"))
        self._search.setFixedHeight(30)
        self._search.setText(initial_query)
        self._search.textChanged.connect(lambda _: self._refresh())
        root.addWidget(self._search)

        # Results table — spreadsheet style (gridlines, header row).
        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels([
            t("stock_picker_col_length"),
            t("stock_picker_col_qty"),
            t("stock_picker_col_ref"),
            t("stock_picker_col_profile"),
            t("stock_picker_col_material"),
            t("stock_picker_col_quality"),
            t("stock_picker_col_retal"),
            t("stock_picker_col_blocked"),
        ])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(
            f"QTableWidget {{ background:{_th.BG_CARD}; border:1px solid {_th.BORDER};"
            f" gridline-color:{_th.BORDER}; color:{_th.TEXT_PRI};"
            f" alternate-background-color:{_th.BG_MID}; }}"
            f"QTableWidget::item {{ padding:3px 6px; }}"
            f"QTableWidget::item:selected {{ background:{_th.ACCENT};"
            f" color:{_text_color_for_bg(_th.ACCENT)}; }}"
            f"QHeaderView::section {{ background:{_th.BG_MID}; color:{_th.TEXT_PRI};"
            f" padding:4px 6px; border:0px; border-right:1px solid {_th.BORDER};"
            f" border-bottom:1px solid {_th.BORDER}; font-weight:bold; }}"
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(self._COL_REF, QHeaderView.ResizeMode.Stretch)
        for col in (self._COL_LENGTH, self._COL_QTY, self._COL_PROFILE,
                    self._COL_MATERIAL, self._COL_QUALITY, self._COL_RETAL,
                    self._COL_BLOCKED):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._update_preview)
        self._table.itemDoubleClicked.connect(lambda _: self._accept_selected())
        root.addWidget(self._table, 1)

        # ── Bottom bar: preview (left) · "show remnants" · action buttons ──────
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self._preview = _BarPreview()
        self._preview.setFixedWidth(180)
        bottom.addWidget(self._preview)

        self._show_retales = QCheckBox(t("stock_picker_show_retales"))
        self._show_retales.setChecked(True)
        self._show_retales.toggled.connect(lambda _: self._refresh())
        bottom.addWidget(self._show_retales, 0, Qt.AlignmentFlag.AlignTop)

        bottom.addStretch(1)

        # Action buttons laid out in a 3×2 grid, mirroring the reference dialog.
        btn_grid = QGridLayout()
        btn_grid.setSpacing(6)

        self._add_qty_btn = QPushButton(t("stock_picker_add_qty"))
        self._add_qty_btn.clicked.connect(self._add_qty)
        self._del_qty_btn = QPushButton(t("stock_picker_del_qty"))
        self._del_qty_btn.clicked.connect(self._del_qty)
        self._create_btn = QPushButton(t("stock_picker_create_new"))
        self._create_btn.clicked.connect(self._create_new)
        self._block_btn = QPushButton(t("stock_picker_block"))
        self._block_btn.clicked.connect(self._toggle_block)
        self._ok = QPushButton(t("ok"))
        self._ok.setProperty("variant", "accent")
        self._ok.clicked.connect(self._accept_selected)
        self._cancel = QPushButton(t("cancel"))
        self._cancel.clicked.connect(self.reject)

        for btn in (self._add_qty_btn, self._del_qty_btn, self._create_btn,
                    self._block_btn, self._ok, self._cancel):
            btn.setFixedHeight(30)
            btn.setMinimumWidth(110)

        btn_grid.addWidget(self._add_qty_btn, 0, 0)
        btn_grid.addWidget(self._del_qty_btn, 0, 1)
        btn_grid.addWidget(self._create_btn, 1, 0)
        btn_grid.addWidget(self._block_btn, 1, 1)
        btn_grid.addWidget(self._ok, 2, 0)
        btn_grid.addWidget(self._cancel, 2, 1)
        bottom.addLayout(btn_grid)

        root.addLayout(bottom)

        self._refresh()
        self._search.setFocus()

    # ── Results ───────────────────────────────────────────────────────────────

    def _visible_bars(self) -> List[StockBar]:
        """Bars matching the material lock, search query and 'show remnants' toggle."""
        ql = self._search.text().strip().lower()
        show_retales = self._show_retales.isChecked()
        rows: List[StockBar] = []
        for b in get_stock().bars:
            if b.quantity <= 0:
                continue
            if b.is_retal and not show_retales:
                continue
            # Lock to the nesting's material when one is selected: every set
            # filter field must match (case-insensitive). Unset fields are wild.
            if self._f_profile and self._f_profile != (b.profile_name or "").lower():
                continue
            if self._f_material and self._f_material != (b.material or "").lower():
                continue
            if self._f_quality and self._f_quality != (b.quality or "").lower():
                continue
            if ql and ql not in b.full_name.lower() and ql not in b.display_name.lower():
                continue
            rows.append(b)
        return rows

    def _refresh(self, select_id: str = "") -> None:
        self._table.setRowCount(0)
        rows = self._visible_bars()
        if not rows:
            self._update_buttons()
            self._preview.set_bar(None)
            return

        for b in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            eff_len = b.retal_length if b.is_retal else b.length
            cells = [
                (self._COL_LENGTH, f"{eff_len:.0f}", Qt.AlignmentFlag.AlignRight),
                (self._COL_QTY, str(b.quantity), Qt.AlignmentFlag.AlignRight),
                (self._COL_REF, b.full_name, Qt.AlignmentFlag.AlignLeft),
                (self._COL_PROFILE, b.profile_name, Qt.AlignmentFlag.AlignLeft),
                (self._COL_MATERIAL, b.material_desc, Qt.AlignmentFlag.AlignLeft),
                (self._COL_QUALITY, b.quality, Qt.AlignmentFlag.AlignLeft),
                (self._COL_RETAL, "R" if b.is_retal else "", Qt.AlignmentFlag.AlignCenter),
                (self._COL_BLOCKED, "B" if b.blocked else "", Qt.AlignmentFlag.AlignCenter),
            ]
            for col, text, align in cells:
                item = QTableWidgetItem(text)
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if b.blocked:
                    item.setForeground(QColor(_th.TEXT_DIM))
                self._table.setItem(r, col, item)
            # Stash the bar on the first cell so we can recover it later.
            self._table.item(r, 0).setData(Qt.ItemDataRole.UserRole, b)

        # Restore selection (after add/remove qty or block) or default to first.
        target = 0
        if select_id:
            for r in range(self._table.rowCount()):
                bar = self._table.item(r, 0).data(Qt.ItemDataRole.UserRole)
                if isinstance(bar, StockBar) and bar.id == select_id:
                    target = r
                    break
        self._table.selectRow(target)
        self._update_preview()

    def _selected_bar(self) -> Optional[StockBar]:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        bar = self._table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        return bar if isinstance(bar, StockBar) else None

    def _update_preview(self) -> None:
        self._preview.set_bar(self._selected_bar())
        self._update_buttons()

    def _update_buttons(self) -> None:
        bar = self._selected_bar()
        has_sel = bar is not None
        for btn in (self._add_qty_btn, self._del_qty_btn, self._block_btn):
            btn.setEnabled(has_sel)
        self._ok.setEnabled(has_sel and not (bar and bar.blocked))
        if bar and bar.blocked:
            self._block_btn.setText(t("stock_picker_unblock"))
        else:
            self._block_btn.setText(t("stock_picker_block"))

    # ── Actions ─────────────────────────────────────────────────────────────

    def _add_qty(self) -> None:
        bar = self._selected_bar()
        if bar is None:
            return
        update_bar(bar.id, quantity=bar.quantity + 1)
        self._refresh(select_id=bar.id)

    def _del_qty(self) -> None:
        bar = self._selected_bar()
        if bar is None:
            return
        new_qty = max(bar.quantity - 1, 0)
        update_bar(bar.id, quantity=new_qty)
        # Quantity 0 drops out of the list; fall back to default selection.
        self._refresh(select_id=bar.id if new_qty > 0 else "")

    def _toggle_block(self) -> None:
        bar = self._selected_bar()
        if bar is None:
            return
        bar.blocked = not bar.blocked
        save_stock()
        self._refresh(select_id=bar.id)

    def _create_new(self) -> None:
        from nestify.ui_qt.dialogs.stock_add_dialog import StockAddDialog

        currency = "EUR"
        parent = self.parent()
        if parent is not None and hasattr(parent, "_state"):
            currency = getattr(parent._state, "currency", "EUR")

        new_id_holder = {"id": ""}

        def on_confirm(data: dict) -> None:
            new_bar = add_bar(
                profile_name=data["profile_name"],
                material_desc=data["material_desc"],
                length=data["length"],
                quantity=data["qty"],
                quality=data["quality"],
                espesor=data["espesor"],
                kg_por_m=data["kg_por_m"],
                precio_kg=data["precio_kg"],
                precio_m=data["precio_m"],
                precio_barra=data["precio_barra"],
                peso_especifico=data["peso_especifico"],
                fields=data["fields"],
                notes=data["notes"],
            )
            new_id_holder["id"] = new_bar.id

        dlg = StockAddDialog(parent=self, currency=currency, on_confirm=on_confirm)
        dlg.exec()
        self._refresh(select_id=new_id_holder["id"])

    # ── Accept ────────────────────────────────────────────────────────────────

    def _accept_selected(self) -> None:
        bar = self._selected_bar()
        if bar is None:
            return
        if bar.blocked:
            QMessageBox.information(
                self, t("stock_bar_picker_title"), t("stock_picker_blocked_warn"))
            return
        self.result_bar = bar
        self.accept()
