"""
nestify/ui_qt/tab_stock.py
Stock/inventory management tab — add, edit, filter bars and profiles.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QHeaderView, QLabel, QMenu, QMessageBox, QPushButton,
    QTableWidgetItem, QWidget,
)

import logging

from nestify.i18n import t
from nestify import units
from nestify.stock_db import get_stock, save_stock, remove_bar, add_bar, update_bar, StockBar
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.icons import themed_icon

_log = logging.getLogger(__name__)
from nestify.ui_qt.forms.ui_tab_stock import Ui_TabStock


class TabStock(QWidget):
    """Stock management tab with filterable bar/profile table."""

    # Emitted when the user clicks a job-name cell; arg is the job name string.
    open_job_requested = Signal(str)

    # Columns: 0=check, 1=dot, 2=profile, 3=material/name, 4=length, 5=qty, 6=avail, 7=retal
    #          8=creation_job, 9=used_jobs
    _COL_CHECK        = 0
    _COL_DOT          = 1
    _COL_PROFILE      = 2
    _COL_NAME         = 3
    _COL_LENGTH       = 4
    _COL_QTY          = 5
    _COL_AVAIL        = 6
    _COL_RETAL        = 7
    _COL_CREATION_JOB = 8
    _COL_USED_JOBS    = 9

    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self._state = state
        self._filter_text = ""
        self._filter_profile = ""
        self._selected_bar: Optional[StockBar] = None
        self._checked_ids: set = set()

        # Debounce timer: the filter list refreshes 200ms after the last
        # keystroke (single-shot, restarted on each edit) so typing in the search
        # box doesn't rebuild the table on every character.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._refresh_list)

        # ── Set up UI from .ui form ──────────────────────────────────────
        self.ui = Ui_TabStock()
        self.ui.setupUi(self)

        # ── Convenience aliases for widgets used heavily in logic ─────────
        self._filter_entry = self.ui.filter_entry
        # Leading magnifier as a themed SVG action icon (replaces the 🔍 emoji
        # that used to sit in the placeholder text and rendered inconsistently
        # on Linux). Stored so it can be re-tinted on theme switch.
        from PySide6.QtWidgets import QLineEdit
        self._filter_search_action = self._filter_entry.addAction(
            themed_icon("search", _th.TEXT_SEC),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._profile_combo = self.ui.profile_combo
        self._summary_lbl = self.ui.summary_lbl
        self._select_all_cb = self.ui.select_all_cb
        self._min_length_entry = self.ui.min_length_entry
        self._max_length_entry = self.ui.max_length_entry
        self._min_retal_entry = self.ui.min_retal_entry
        self._table = self.ui.table

        # ── Style/property fixups not expressible in .ui ─────────────────
        # Theme-dependent stylesheets are applied via _apply_theme_styles()
        # so they re-resolve against _th.* on every theme switch (see
        # refresh_theme). Colours baked here in __init__ alone would keep the
        # construction-time theme and not survive a dark↔light toggle.
        # Scope to the QFrame itself — a selector-less "background:transparent"
        # cascades to child widgets and would wipe the accent fill on the
        # "+ Add to stock" button (leaving white text on the toolbar).
        self.ui.row0.setStyleSheet("QFrame#row0 { background: transparent; }")
        self.ui.row1.setStyleSheet("QFrame#row1 { background: transparent; }")

        self.ui.add_btn.setProperty("variant", "accent")
        self.ui.add_btn.style().polish(self.ui.add_btn)
        self.ui.del_btn.setProperty("variant", "danger")
        self.ui.del_btn.style().polish(self.ui.del_btn)

        self._apply_theme_styles()

        self.ui.table_frame.setProperty("role", "card")
        self.ui.table_frame.style().polish(self.ui.table_frame)

        # ── i18n: override text with t() calls ──────────────────────────
        self.ui.add_btn.setText(f"+ {t('add_to_stock')}")
        self.ui.edit_btn.setText(t("profile_edit_fields"))
        self.ui.edit_btn.setIcon(themed_icon("pencil", _th.TEXT_PRI, 14))
        self.ui.edit_btn.setIconSize(QSize(14, 14))
        self.ui.del_btn.setText(t("remove"))
        self.ui.del_btn.setIcon(themed_icon("x", _th.DANGER, 14))
        self.ui.del_btn.setIconSize(QSize(14, 14))
        self._filter_entry.setPlaceholderText(f"{t('stock_profile')}…")
        self._select_all_cb.setText(t("select_all"))
        self.ui.lbl_min_length.setText(t("filter_length_min", u=units.u_len()))
        self.ui.lbl_max_length.setText(t("filter_length_max", u=units.u_len()))
        self.ui.lbl_min_retal.setText(t("min_retal_length", u=units.u_len()))

        # Table header labels
        headers = [
            "", "",
            t("stock_profile"), t("placeholder_quality"),
            t("stock_length"), t("stock_qty"),
            t("stock_available"), t("stock_retal"),
            t("stock_col_creation_job"), t("stock_col_used_jobs"),
        ]
        for col, text in enumerate(headers):
            item = self._table.horizontalHeaderItem(col)
            if item:
                item.setText(text)

        # ── Table column sizing ──────────────────────────────────────────
        # All columns have a fixed pixel width EXCEPT Material/Name, which is set
        # to Stretch so it absorbs the remaining horizontal space. Widths below
        # are in px and define each column's footprint.
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(self._COL_CHECK,        QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(self._COL_DOT,          QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(self._COL_PROFILE,      QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(self._COL_NAME,         QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(self._COL_LENGTH,       QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(self._COL_QTY,          QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(self._COL_AVAIL,        QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(self._COL_RETAL,        QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(self._COL_CREATION_JOB, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(self._COL_USED_JOBS,    QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(self._COL_CHECK,        32)   # checkbox
        self._table.setColumnWidth(self._COL_DOT,          24)   # status dot ●
        self._table.setColumnWidth(self._COL_PROFILE,      200)  # profile name (resizable)
        self._table.setColumnWidth(self._COL_LENGTH,       80)   # length (mono, right)
        self._table.setColumnWidth(self._COL_QTY,          50)   # quantity
        self._table.setColumnWidth(self._COL_AVAIL,        70)   # ✓/✕ availability toggle
        self._table.setColumnWidth(self._COL_RETAL,        70)   # remnant indicator ↩
        self._table.setColumnWidth(self._COL_CREATION_JOB, 130)  # creation job name
        self._table.setColumnWidth(self._COL_USED_JOBS,    130)  # jobs that consumed this bar

        self._table.verticalHeader().setVisible(False)        # hide row-number gutter
        self._table.verticalHeader().setDefaultSectionSize(36)  # 36px row height
        self._table.setShowGrid(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # ── Connect signals ──────────────────────────────────────────────
        self.ui.add_btn.clicked.connect(self._add_bar_dialog)
        self.ui.edit_btn.clicked.connect(self._edit_selected)
        self.ui.del_btn.clicked.connect(self._delete_selected)

        # Export-to-Excel button, inserted right after Remove (30px to match the
        # toolbar row). Stock had no export before — §4 Conectividad.
        from PySide6.QtWidgets import QPushButton
        self._export_btn = QPushButton(f"⇩ {t('export_excel')}")
        self._export_btn.setFixedHeight(30)
        self._export_btn.clicked.connect(self._export_stock)
        _del_idx = self.ui.row0_layout.indexOf(self.ui.del_btn)
        self.ui.row0_layout.insertWidget(_del_idx + 1, self._export_btn)

        self._filter_entry.textChanged.connect(lambda txt: (
            setattr(self, "_filter_text", txt) or self._filter_timer.start()
        ))
        self._profile_combo.currentTextChanged.connect(self._on_profile_filter)
        self._select_all_cb.toggled.connect(self._toggle_select_all)

        self._min_length_entry.editingFinished.connect(lambda: self._filter_timer.start())
        self._max_length_entry.editingFinished.connect(lambda: self._filter_timer.start())
        self._min_retal_entry.editingFinished.connect(self._on_min_retal_change)

        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellClicked.connect(self._on_cell_clicked)

        # ── Initial data ─────────────────────────────────────────────────
        db = get_stock()
        self._min_retal_entry.setText(str(int(db.min_retal_length)))

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh_list(self) -> None:
        self._table.setRowCount(0)
        self._rebuild_profile_combo()

        bars = self._filter_bars(get_stock().bars)

        if not bars:
            self._summary_lbl.setText(t("stock_empty"))
            return

        for bar in bars:
            self._insert_row(bar)

        total_qty = sum(b.quantity for b in bars)
        self._summary_lbl.setText(f"{len(bars)} items · {total_qty} {t('units_abbr')}")

    def _insert_row(self, bar: StockBar) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setRowHeight(row, 36)
        self._table.setProperty(f"bar_id_{row}", bar.id)

        # Col 0: checkbox
        cb = QCheckBox()
        cb.setChecked(bar.id in self._checked_ids)
        cb.setStyleSheet("QCheckBox { margin-left: 8px; }")
        cb.toggled.connect(lambda checked, bid=bar.id: self._on_check_toggled(bid, checked))
        self._table.setCellWidget(row, self._COL_CHECK, cb)

        # Col 1: status dot
        if bar.quantity == 0:
            dot_color = _th.DANGER
        elif bar.is_retal:
            dot_color = _th.SUCCESS
        else:
            dot_color = _th.SUCCESS
        dot = QLabel()
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setPixmap(themed_icon("circle", dot_color, 8).pixmap(QSize(8, 8)))
        self._table.setCellWidget(row, self._COL_DOT, dot)

        # Col 2: profile
        self._set_cell(row, self._COL_PROFILE, bar.profile_name, Qt.AlignmentFlag.AlignLeft)

        # Col 3: display name ("R:" prefix for retals)
        name = f"R: {bar.display_name}" if bar.is_retal else bar.display_name
        name_item = QTableWidgetItem(name)
        name_item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
        from PySide6.QtGui import QColor
        name_item.setForeground(QColor(_th.SUCCESS) if bar.is_retal else QColor(_th.TEXT_PRI))
        self._table.setItem(row, self._COL_NAME, name_item)

        # Col 4: length
        length = bar.retal_length if bar.is_retal else bar.length
        self._set_cell(row, self._COL_LENGTH, f"{length:.0f}", Qt.AlignmentFlag.AlignRight, mono=True)

        # Col 5: qty
        self._set_cell(row, self._COL_QTY, str(bar.quantity), Qt.AlignmentFlag.AlignCenter, mono=True)

        # Col 6: availability toggle button — fixed 50×22 to sit inside the 70px
        # column with margin; ✓/green when in stock, ✕/red when depleted.
        avail_text  = "OK" if bar.quantity > 0 else "—"
        avail_color = _th.SUCCESS if bar.quantity > 0 else _th.DANGER
        avail_btn = QPushButton(avail_text)
        avail_btn.setFixedSize(60, 28)
        avail_btn.setStyleSheet(
            f"QPushButton {{ color:{avail_color}; border:1px solid {_th.BORDER};"
            f" border-radius:3px; background:transparent; font-size:11px; }}"
            f"QPushButton:hover {{ background:{_th.BG_CARD}; }}"
        )
        avail_btn.clicked.connect(lambda _, b=bar: self._toggle_availability(b))
        self._table.setCellWidget(row, self._COL_AVAIL, avail_btn)

        # Col 7: retal indicator
        self._set_cell(row, self._COL_RETAL, "R" if bar.is_retal else "",
                       Qt.AlignmentFlag.AlignCenter)

        # Col 8: creation job — clickable link style when non-empty
        creation_job = getattr(bar, "creation_job_name", "") or ""
        cj_item = QTableWidgetItem(creation_job)
        cj_item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
        if creation_job:
            cj_item.setForeground(QColor(_th.ACCENT))
            cj_item.setToolTip(t("stock_job_click_hint"))
        else:
            cj_item.setForeground(QColor(_th.TEXT_SEC))
        self._table.setItem(row, self._COL_CREATION_JOB, cj_item)

        # Col 9: used-in jobs (comma-separated compact list) — clickable when non-empty
        used_jobs = getattr(bar, "used_in_job_names", []) or []
        used_text = ", ".join(used_jobs) if used_jobs else ""
        uj_item = QTableWidgetItem(used_text)
        uj_item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
        if used_text:
            uj_item.setForeground(QColor(_th.ACCENT))
            uj_item.setToolTip(f"{used_text}\n{t('stock_job_click_hint')}")
        else:
            uj_item.setForeground(QColor(_th.TEXT_SEC))
        self._table.setItem(row, self._COL_USED_JOBS, uj_item)

        # Tag row with bar id for hit-testing
        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item:
                item.setData(Qt.ItemDataRole.UserRole, bar.id)

    def _set_cell(self, row: int, col: int, text: str,
                  align=Qt.AlignmentFlag.AlignLeft, mono: bool = False) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(int(align | Qt.AlignmentFlag.AlignVCenter))
        item.setData(Qt.ItemDataRole.UserRole, None)
        if mono:
            # Numeric columns (length, qty) use 10pt DejaVu Sans Mono so digits
            # are fixed-width and right-aligned values line up cleanly.
            from PySide6.QtGui import QFont
            item.setFont(QFont("DejaVu Sans Mono", 10))
        self._table.setItem(row, col, item)

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _filter_bars(self, bars) -> list:
        result = list(bars)
        if self._filter_text:
            ft = self._filter_text.lower()
            result = [b for b in result if (
                ft in b.material_desc.lower()
                or ft in b.profile_name.lower()
                or ft in b.display_name.lower()
            )]
        if self._filter_profile:
            result = [b for b in result
                      if b.profile_name.lower() == self._filter_profile.lower()]
        try:
            min_len = float(self._min_length_entry.text())
            result = [b for b in result
                      if (b.retal_length if b.is_retal else b.length) >= min_len]
        except (ValueError, AttributeError):
            pass
        try:
            max_len = float(self._max_length_entry.text())
            result = [b for b in result
                      if (b.retal_length if b.is_retal else b.length) <= max_len]
        except (ValueError, AttributeError):
            pass
        return result

    def _rebuild_profile_combo(self) -> None:
        self._profile_combo.blockSignals(True)
        current = self._profile_combo.currentText()
        self._profile_combo.clear()
        self._profile_combo.addItem(t("select_profile_dropdown"), "")
        try:
            from nestify.stock_db import get_profiles_in_stock
            for p in sorted(get_profiles_in_stock()):
                self._profile_combo.addItem(p, p)
        except Exception:
            _log.exception("Failed to populate profile combo")
        idx = self._profile_combo.findText(current)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        self._profile_combo.blockSignals(False)

    # ── Signals ───────────────────────────────────────────────────────────────

    def _on_profile_filter(self, text: str) -> None:
        self._filter_profile = "" if text == t("select_profile_dropdown") else text
        self._refresh_list()

    def _on_min_retal_change(self) -> None:
        try:
            val = float(self._min_retal_entry.text())
            db = get_stock()
            db.min_retal_length = val
            save_stock()
        except (ValueError, TypeError):
            pass

    def _on_check_toggled(self, bar_id: int, checked: bool) -> None:
        if checked:
            self._checked_ids.add(bar_id)
        else:
            self._checked_ids.discard(bar_id)

    def _on_selection_changed(self) -> None:
        rows = self._table.selectedItems()
        if not rows:
            self._selected_bar = None
            return
        row = self._table.currentRow()
        bar_id = None
        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item:
                bar_id = item.data(Qt.ItemDataRole.UserRole)
                break
        if bar_id is None:
            # Try cell widgets
            cb = self._table.cellWidget(row, self._COL_CHECK)
            if cb:
                bar_id = self._table.property(f"bar_id_{row}")
        if bar_id is not None:
            self._selected_bar = next(
                (b for b in get_stock().bars if b.id == bar_id), None
            )

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Navigate to Job Explorer when user clicks a job-name cell (§11)."""
        if col not in (self._COL_CREATION_JOB, self._COL_USED_JOBS):
            return
        item = self._table.item(row, col)
        if not item:
            return
        text = item.text().strip()
        if not text:
            return
        # For "Used In Jobs", only navigate to the first job name if multiple.
        job_name = text.split(",")[0].strip() if col == self._COL_USED_JOBS else text
        if job_name:
            self.open_job_requested.emit(job_name)

    def _toggle_select_all(self, checked: bool) -> None:
        bars = self._filter_bars(get_stock().bars)
        if checked:
            self._checked_ids = {b.id for b in bars}
        else:
            self._checked_ids.clear()
        self._refresh_list()

    def _toggle_availability(self, bar: StockBar) -> None:
        bar.quantity = 0 if bar.quantity > 0 else 1
        save_stock()
        self._refresh_list()

    def _on_context_menu(self, pos) -> None:
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        bar_id = None
        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item:
                bar_id = item.data(Qt.ItemDataRole.UserRole)
                break
        if bar_id is not None:
            self._selected_bar = next(
                (b for b in get_stock().bars if b.id == bar_id), None
            )
        menu = QMenu(self)
        menu.addAction(t("profile_edit_fields"), self._edit_selected)
        menu.addAction(t("remove"), self._delete_selected)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_bar_dialog(self) -> None:
        self._open_stock_dialog()

    def _edit_selected(self) -> None:
        if not self._selected_bar:
            QMessageBox.warning(self, t("warning"), t("select_stock_msg"))
            return
        self._open_stock_dialog(self._selected_bar)

    def _open_stock_dialog(self, bar: Optional[StockBar] = None) -> None:
        try:
            from nestify.ui_qt.dialogs.stock_add_dialog import StockAddDialog
        except ImportError:
            QMessageBox.information(self, t("tab_stock"), "Stock dialog not yet implemented.")
            return

        def on_confirm(data: dict) -> None:
            if bar:
                update_bar(
                    bar.id,
                    profile_name=data["profile_name"],
                    material_desc=data["material_desc"],
                    quality=data["quality"],
                    length=data["length"],
                    quantity=data["qty"],
                    espesor=data["espesor"],
                    kg_por_m=data["kg_por_m"],
                    precio_kg=data["precio_kg"],
                    precio_m=data["precio_m"],
                    precio_barra=data["precio_barra"],
                    peso_especifico=data["peso_especifico"],
                    fields=data["fields"],
                    notes=data["notes"],
                    # The edit dialog doesn't expose the custom display name, so
                    # preserve the bar's existing one instead of blanking it —
                    # otherwise editing a remnant wiped its RET-… name (and broke
                    # remnant sequence numbering keyed off it).
                    custom_display_name=(data.get("custom_display_name")
                                         or getattr(bar, "custom_display_name", "")),
                )
            else:
                add_bar(
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
            self._refresh_list()
            QMessageBox.information(self, t("tab_stock"), t("stock_saved"))

        dlg = StockAddDialog(bar=bar, currency=self._state.currency, parent=self, on_confirm=on_confirm)
        dlg.exec()

    def _export_stock(self) -> None:
        """Export the whole stock inventory to an .xlsx file (Qt file dialog)."""
        from PySide6.QtWidgets import QFileDialog
        bars = get_stock().bars
        if not bars:
            QMessageBox.information(self, t("export_excel"), t("no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_excel"), "nestify_stock.xlsx", "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from nestify.stock_export import export_stock_to_excel
            currency = getattr(self._state, "currency", "EUR") if self._state else "EUR"
            export_stock_to_excel(path, bars, currency)
            QMessageBox.information(self, t("export_excel"), t("excel_saved", path=path))
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))

    def _delete_selected(self) -> None:
        targets = list(self._checked_ids)
        if not targets and self._selected_bar:
            targets = [self._selected_bar.id]
        if not targets:
            QMessageBox.warning(self, t("warning"), t("select_stock_msg"))
            return
        reply = QMessageBox.question(
            self, t("remove"), f"{t('remove')} ({len(targets)})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for bar_id in targets:
            remove_bar(bar_id)
        self._selected_bar = None
        self._checked_ids.clear()
        self._refresh_list()

    # ── Public API ────────────────────────────────────────────────────────────

    def _apply_theme_styles(self) -> None:
        """(Re)apply theme-dependent stylesheets on the toolbar and labels.

        Called from __init__ and from refresh_theme() so colours track the
        active theme across dark↔light switches instead of freezing at the
        construction-time theme.
        """
        self.ui.toolbar.setStyleSheet(
            f"QFrame {{ background:{_th.BG_CARD}; border-bottom:1px solid {_th.BORDER}; }}"
        )
        self._table.setStyleSheet(
            f"QTableWidget {{ gridline-color:{_th.BORDER}; border:1px solid {_th.BORDER}; }}"
            f"QTableWidget::item {{ padding:0 4px; }}"
            f"QHeaderView::section {{ background:{_th.BG_MID}; color:{_th.TEXT_SEC};"
            f" border:none; border-right:1px solid {_th.BORDER};"
            f" border-bottom:1px solid {_th.BORDER}; padding:4px; font-size:10px; }}"
        )
        self._summary_lbl.setStyleSheet(
            f"color:{_th.TEXT_SEC}; font-size:11px; background:transparent;"
        )
        self._select_all_cb.setStyleSheet(
            f"color:{_th.TEXT_SEC}; font-size:10px; background:transparent;"
        )
        for lbl_widget in (self.ui.lbl_min_length, self.ui.lbl_max_length, self.ui.lbl_min_retal):
            lbl_widget.setStyleSheet(
                f"color:{_th.TEXT_SEC}; font-size:10px; background:transparent;"
            )
        # Re-tint the leading magnifier action icon for the active palette.
        if getattr(self, "_filter_search_action", None) is not None:
            self._filter_search_action.setIcon(themed_icon("search", _th.TEXT_SEC))

    def refresh_theme(self) -> None:
        self._apply_theme_styles()
        self._refresh_list()

    def load_state(self, state) -> None:
        self._state = state
        self._refresh_list()
