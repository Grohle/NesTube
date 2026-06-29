"""
nestify/ui_qt/tab_materiales.py
"Profiles & Tubes" tab (§20.5 / §21.1) — search the profile/tube catalogue
and reuse the existing creation/editing tools (ProfileCreator, ProfileManager,
MaterialsManagerDialog).  Sits between "Costs and Weight" and "Stock".

Toolbar has two groups separated by a vertical rule:
  • Profiles & Tubes: Add profile/tube (→ ProfileCreator), Edit selected
  • Materials:        Edit materials (→ MaterialsManagerDialog)
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from nestify import app_config
from nestify.app_config import CustomProfileEntry
from nestify.i18n import t
import nestify.ui_qt.theme_qt as _th
from nestify.naming import localize_material

_TILE_ICON = 96
_ROW_ICON = 48
_ROW_HEIGHT = 56

# Table columns: thumbnail, name, material, h, b, tw, tf, section, weight/m
_COL_ICON = 0
_COL_NAME = 1
_COL_MATERIAL = 2
_COL_H = 3
_COL_B = 4
_COL_TW = 5
_COL_TF = 6
_COL_SECTION = 7
_COL_WEIGHT = 8


class TabMateriales(QWidget):
    """Catalogue browser: search profiles/tubes, open the existing editors."""

    def __init__(
        self,
        on_add_profile: Optional[Callable] = None,
        on_profiles_changed: Optional[Callable] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._on_add_profile = on_add_profile
        self._on_profiles_changed = on_profiles_changed
        self._build()
        self._ensure_catalog()
        self.refresh()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _ensure_catalog(self) -> None:
        try:
            from nestify.profile_catalog import ensure_catalog_profiles
            ensure_catalog_profiles()
        except Exception:
            pass

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self._title = QLabel(t("tab_profiles_tubes"))
        self._title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold; font-size: 16px;")
        root.addWidget(self._title)

        self._hint = QLabel(t("materials_catalog_hint"))
        self._hint.setStyleSheet(f"color: {_th.TEXT_SEC};")
        root.addWidget(self._hint)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Search + view-toggle (grow to fill available space)
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("search_placeholder"))
        self._search.setFixedHeight(30)
        self._search.textChanged.connect(self.refresh)
        toolbar.addWidget(self._search, 1)

        self._btn_view_list = QPushButton(t("materials_view_list"))
        self._btn_view_list.setFixedHeight(30)
        self._btn_view_list.setCheckable(True)
        self._btn_view_list.setChecked(True)
        toolbar.addWidget(self._btn_view_list)

        self._btn_view_grid = QPushButton(t("materials_view_grid"))
        self._btn_view_grid.setFixedHeight(30)
        self._btn_view_grid.setCheckable(True)
        toolbar.addWidget(self._btn_view_grid)

        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)
        self._view_group.addButton(self._btn_view_list)
        self._view_group.addButton(self._btn_view_grid)
        self._btn_view_list.toggled.connect(self._on_view_toggled)

        # ── Profiles & Tubes group ────────────────────────────────────────
        self._btn_new = QPushButton(t("new_catalog_profile"))
        self._btn_new.setFixedHeight(30)
        self._btn_new.clicked.connect(self._add_profile)
        toolbar.addWidget(self._btn_new)

        self._btn_edit = QPushButton(t("edit"))
        self._btn_edit.setFixedHeight(30)
        self._btn_edit.setEnabled(False)
        self._btn_edit.clicked.connect(self._edit_selected)
        toolbar.addWidget(self._btn_edit)

        # ── Visual separator ──────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setFixedHeight(22)
        sep.setStyleSheet(f"color: {_th.BORDER};")
        toolbar.addWidget(sep)

        # ── Materials group ───────────────────────────────────────────────
        self._btn_material = QPushButton(t("edit_materials_btn"))
        self._btn_material.setFixedHeight(30)
        self._btn_material.clicked.connect(self._edit_materials)
        toolbar.addWidget(self._btn_material)

        root.addLayout(toolbar)

        self._stack = QStackedWidget()

        # ── List (detail) view — default ──
        self._table = QTableWidget(0, 9)
        self._table.setHorizontalHeaderLabels([
            "", t("materials_col_name"), t("stock_material"),
            "h", "b", "tw", "tf", t("section"), t("weight_per_meter"),
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setIconSize(QSize(_ROW_ICON, _ROW_ICON))
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_ICON, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_ICON, _ROW_ICON + 16)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        for col in (_COL_MATERIAL, _COL_H, _COL_B, _COL_TW, _COL_TF, _COL_SECTION, _COL_WEIGHT):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellDoubleClicked.connect(lambda _r, _c: self._edit_selected())
        self._stack.addWidget(self._table)

        # ── Grid (icon) view — alternate ──
        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(_TILE_ICON, _TILE_ICON))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setSpacing(8)
        self._list.setWordWrap(True)
        self._list.setStyleSheet(
            f"QListWidget {{ background: {_th.BG_CARD}; border: 1px solid {_th.BORDER}; "
            f"border-radius: 8px; color: {_th.TEXT_PRI}; }}"
            f"QListWidget::item:selected {{ background: {_th.BG_MID}; "
            f"border: 1px solid {_th.ACCENT}; border-radius: 6px; }}"
        )
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(lambda _i: self._edit_selected())
        self._stack.addWidget(self._list)

        root.addWidget(self._stack, 1)

        self._detail = QLabel("")
        self._detail.setStyleSheet(f"color: {_th.TEXT_SEC};")
        self._detail.setWordWrap(True)
        self._detail.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        root.addWidget(self._detail)

    # ── Data ─────────────────────────────────────────────────────────────────

    def _filtered_entries(self) -> list[CustomProfileEntry]:
        query = self._search.text().strip().lower()
        result = []
        for entry in app_config.get().custom_profiles:
            material = localize_material(entry.meta.get("material", ""))
            haystack = f"{entry.name} {material}".lower()
            if query and query not in haystack:
                continue
            result.append(entry)
        return result

    def refresh(self) -> None:
        entries = self._filtered_entries()
        self._populate_table(entries)
        self._populate_grid(entries)
        self._btn_edit.setEnabled(False)
        self._detail.setText("")

    def _populate_table(self, entries: list[CustomProfileEntry]) -> None:
        self._table.setRowCount(0)
        for entry in entries:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setRowHeight(row, _ROW_HEIGHT)

            icon_item = QTableWidgetItem()
            icon = self._icon_for(entry)
            if icon is not None:
                icon_item.setIcon(icon)
            icon_item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._table.setItem(row, _COL_ICON, icon_item)

            self._set_cell(row, _COL_NAME, entry.name)
            meta = entry.meta or {}
            material = localize_material(meta.get("material", "")) or "—"
            self._set_cell(row, _COL_MATERIAL, material)
            for col, key in ((_COL_H, "h"), (_COL_B, "b"), (_COL_TW, "tw"), (_COL_TF, "tf")):
                val = meta.get(key)
                self._set_cell(row, col, f"{val:g}" if val else "", align_right=True)
            seccion = meta.get("seccion_cm2")
            self._set_cell(row, _COL_SECTION, f"{seccion:g}" if seccion else "", align_right=True)
            peso = meta.get("peso_lineal_kg_m")
            self._set_cell(row, _COL_WEIGHT, f"{peso:g}" if peso else "", align_right=True)

    def _set_cell(self, row: int, col: int, text: str, align_right: bool = False) -> None:
        item = QTableWidgetItem(text)
        align = Qt.AlignmentFlag.AlignVCenter
        align |= Qt.AlignmentFlag.AlignRight if align_right else Qt.AlignmentFlag.AlignLeft
        item.setTextAlignment(align)
        self._table.setItem(row, col, item)

    def _populate_grid(self, entries: list[CustomProfileEntry]) -> None:
        self._list.clear()
        for entry in entries:
            item = QListWidgetItem(entry.name)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            item.setSizeHint(QSize(_TILE_ICON + 20, _TILE_ICON + 36))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            icon = self._icon_for(entry)
            if icon is not None:
                item.setIcon(icon)
            self._list.addItem(item)

    def _icon_for(self, entry: CustomProfileEntry) -> Optional[QIcon]:
        if not entry.image:
            return None
        path = os.path.join(app_config.PROFILES_DIR, entry.image)
        if not os.path.isfile(path):
            return None
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None
        return QIcon(pixmap)

    def _selected_entry(self) -> Optional[CustomProfileEntry]:
        entry_id = None
        if self._stack.currentWidget() is self._table:
            rows = self._table.selectionModel().selectedRows()
            if rows:
                item = self._table.item(rows[0].row(), _COL_ICON)
                entry_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        else:
            items = self._list.selectedItems()
            if items:
                entry_id = items[0].data(Qt.ItemDataRole.UserRole)
        if entry_id is None:
            return None
        return next((e for e in app_config.get().custom_profiles if e.id == entry_id), None)

    def _on_selection_changed(self) -> None:
        entry = self._selected_entry()
        self._btn_edit.setEnabled(entry is not None)
        self._detail.setText(self._describe(entry) if entry else "")

    def _describe(self, entry: CustomProfileEntry) -> str:
        meta = entry.meta or {}
        material = localize_material(meta.get("material", "")) or "—"
        parts = [f"{t('stock_material')}: {material}"]
        dims = []
        for key, label in (("h", "h"), ("b", "b"), ("tw", "tw"), ("tf", "tf")):
            val = meta.get(key)
            if val:
                dims.append(f"{label}={val:g} mm")
        if dims:
            parts.append(" · ".join(dims))
        seccion = meta.get("seccion_cm2")
        if seccion:
            parts.append(f"{t('section')}: {seccion:g} cm²")
        peso = meta.get("peso_lineal_kg_m")
        if peso:
            parts.append(f"{t('weight_per_meter')}: {peso:g} kg/m")
        return "\n".join(parts)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_view_toggled(self, list_checked: bool) -> None:
        self._stack.setCurrentWidget(self._table if list_checked else self._list)
        self._on_selection_changed()

    def _add_profile(self) -> None:
        if self._on_add_profile:
            self._on_add_profile()
        self.refresh()
        if self._on_profiles_changed:
            self._on_profiles_changed()

    def _edit_selected(self) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        from nestify.ui_qt.dialogs.profile_manager import ProfileManager
        ProfileManager(self, on_change=self._on_change_proxy, initial_select_id=entry.id).exec()

    def _edit_materials(self) -> None:
        from nestify.ui_qt.dialogs.materials_manager import MaterialsManagerDialog
        MaterialsManagerDialog(self).exec()
        self.refresh()

    def _on_change_proxy(self) -> None:
        self.refresh()
        if self._on_profiles_changed:
            self._on_profiles_changed()

    # ── Theme ────────────────────────────────────────────────────────────────

    def refresh_theme(self) -> None:
        self._title.setText(t("tab_profiles_tubes"))
        self._title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold; font-size: 16px;")
        self._hint.setStyleSheet(f"color: {_th.TEXT_SEC};")
        self._detail.setStyleSheet(f"color: {_th.TEXT_SEC};")
        self._list.setStyleSheet(
            f"QListWidget {{ background: {_th.BG_CARD}; border: 1px solid {_th.BORDER}; "
            f"border-radius: 8px; color: {_th.TEXT_PRI}; }}"
            f"QListWidget::item:selected {{ background: {_th.BG_MID}; "
            f"border: 1px solid {_th.ACCENT}; border-radius: 6px; }}"
        )
