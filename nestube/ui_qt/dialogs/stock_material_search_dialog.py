"""
nestube/ui_qt/dialogs/stock_material_search_dialog.py
Unified search window for selecting a working material (TODO §2.3).

Two modes (toggle at the top, default = fictitious material from the
database):

  • Material  — any material/quality from the materials database, even if
                there is no physical stock for it yet ("fictitious").
  • Stock     — real bars currently in stock, with length/quantity.

Free-text search and a minimum-length filter narrow the results live as
you type. Picking a row returns a :class:`MaterialSelection`, which the
caller applies to the active material context (and, for stock bars, uses
to prefill cost/weight parameters — TODO §2.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from nestube.i18n import t
from nestube.naming import format_full_name, format_material
from nestube.materials_db import Material, get_materials, search_materials
from nestube.stock_db import StockBar, get_stock
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.nesting_scene import _text_color_for_bg


# Selection source identifiers.
SRC_PROFILE = "profile"
SRC_FICTITIOUS = "fictitious"
SRC_STOCK = "stock"


@dataclass
class MaterialSelection:
    """The outcome of the search dialog.

    ``stock_bar`` is set only for :data:`SRC_STOCK` selections; it carries
    the pricing/weight fields used to prefill the cost profile.
    """
    source: str
    profile_name: str
    material: str
    quality: str
    stock_bar: Optional[StockBar] = None

    @property
    def full_name(self) -> str:
        return format_full_name(self.profile_name, self.material, self.quality)


class StockMaterialSearchDialog(QDialog):
    """Modal picker over saved profiles, the materials database and the stock inventory."""

    def __init__(self, parent: QWidget = None, initial_query: str = "",
                 default_mode: str = SRC_PROFILE) -> None:
        super().__init__(parent)
        self._mode = default_mode
        self.result_selection: Optional[MaterialSelection] = None
        self.setStyleSheet(f"QDialog {{ background:{_th.BG_MID}; }}")

        self.setWindowTitle(t("material_search"))
        self.setMinimumSize(500, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Mode toggle: Profiles & Tubes / Material (DB) / Stock ────────
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self._btn_profile = QPushButton(t("search_mode_profile"))
        self._btn_fict = QPushButton(t("search_mode_material"))
        self._btn_stock = QPushButton(t("search_mode_stock"))
        self._mode_group = QButtonGroup(self)
        for b, mode in ((self._btn_profile, SRC_PROFILE),
                        (self._btn_fict, SRC_FICTITIOUS),
                        (self._btn_stock, SRC_STOCK)):
            b.setCheckable(True)
            b.setFixedHeight(30)
            b.setProperty("variant", "ghost")
            self._mode_group.addButton(b)
            mode_row.addWidget(b)
        mode_row.addStretch()
        self._btn_profile.setChecked(default_mode == SRC_PROFILE)
        self._btn_fict.setChecked(default_mode == SRC_FICTITIOUS)
        self._btn_stock.setChecked(default_mode == SRC_STOCK)
        self._btn_profile.clicked.connect(lambda: self._set_mode(SRC_PROFILE))
        self._btn_fict.clicked.connect(lambda: self._set_mode(SRC_FICTITIOUS))
        self._btn_stock.clicked.connect(lambda: self._set_mode(SRC_STOCK))
        root.addLayout(mode_row)

        # ── Filter row: free text + minimum length ───────────────────────
        filt_row = QHBoxLayout()
        filt_row.setSpacing(6)
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("search_placeholder"))
        self._search.setFixedHeight(30)
        self._search.setText(initial_query)
        filt_row.addWidget(self._search, 2)

        self._min_len_lbl = QLabel(t("min_length_filter"))
        self._min_len_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:10px;")
        filt_row.addWidget(self._min_len_lbl)
        self._min_len = QLineEdit()
        self._min_len.setPlaceholderText("0")
        self._min_len.setFixedSize(64, 30)
        filt_row.addWidget(self._min_len)
        root.addLayout(filt_row)

        # ── Results list ─────────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget {{ background:{_th.BG_CARD}; border:1px solid {_th.BORDER};"
            f" border-radius:4px; }}"
            f"QListWidget::item {{ padding:6px 8px; color:{_th.TEXT_PRI}; }}"
            f"QListWidget::item:selected {{ background:{_th.ACCENT}; color:{_text_color_for_bg(_th.ACCENT)}; }}"
        )
        self._list.itemDoubleClicked.connect(lambda _: self._accept_selected())
        root.addWidget(self._list, 1)

        # ── Buttons ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.setFixedHeight(30)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        self._ok = QPushButton(t("select"))
        self._ok.setFixedHeight(30)
        self._ok.setProperty("variant", "accent")
        self._ok.clicked.connect(self._accept_selected)
        btn_row.addWidget(self._ok)
        root.addLayout(btn_row)

        # Debounced live refresh as the user types.
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._refresh)
        self._search.textChanged.connect(lambda _: self._debounce.start())
        self._min_len.textChanged.connect(lambda _: self._debounce.start())
        self._search.returnPressed.connect(self._accept_selected)

        self._update_mode_styles()
        self._refresh()
        self._search.setFocus()

    # ── Mode ────────────────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self._update_mode_styles()
        # The min-length filter only makes sense for physical stock bars.
        for w in (self._min_len, self._min_len_lbl):
            w.setVisible(mode == SRC_STOCK)
        self._refresh()

    def _update_mode_styles(self) -> None:
        self._btn_profile.setChecked(self._mode == SRC_PROFILE)
        self._btn_fict.setChecked(self._mode == SRC_FICTITIOUS)
        self._btn_stock.setChecked(self._mode == SRC_STOCK)
        active = (f"QPushButton {{ background:{_th.ACCENT}; color:{_text_color_for_bg(_th.ACCENT)};"
                  f" border:none; border-radius:4px; padding:4px 14px; font-weight:bold; }}")
        inactive = (f"QPushButton {{ background:transparent; color:{_th.TEXT_SEC};"
                    f" border:1px solid {_th.BORDER}; border-radius:4px; padding:4px 14px; }}"
                    f"QPushButton:hover {{ color:{_th.TEXT_PRI}; }}")
        for btn, src in ((self._btn_profile, SRC_PROFILE),
                         (self._btn_fict, SRC_FICTITIOUS),
                         (self._btn_stock, SRC_STOCK)):
            btn.setStyleSheet(active if self._mode == src else inactive)
        for w in (self._min_len, self._min_len_lbl):
            w.setVisible(self._mode == SRC_STOCK)

    # ── Results ─────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._list.clear()
        query = self._search.text().strip()
        if self._mode == SRC_PROFILE:
            self._populate_profiles(query)
        elif self._mode == SRC_FICTITIOUS:
            self._populate_materials(query)
        else:
            self._populate_stock(query)

    def _populate_profiles(self, query: str) -> None:
        """List custom profiles+tubes from the Profiles & Tubes catalogue."""
        try:
            from nestube import app_config as _ac
            profiles = getattr(_ac.get(), "custom_profiles", [])
        except Exception:
            profiles = []
        ql = query.lower()
        rows = [
            cp for cp in profiles
            if not ql or ql in cp.name.lower()
            or ql in getattr(cp, "quality", "").lower()
        ]
        if not rows:
            self._add_empty()
            return
        for cp in rows:
            material = cp.meta.get("material", "") if hasattr(cp, "meta") and cp.meta else ""
            quality = getattr(cp, "quality", "")
            sel = MaterialSelection(
                source=SRC_PROFILE,
                profile_name=cp.name,
                material=material,
                quality=quality,
            )
            label = cp.name
            label += f"   ·   {quality or '—'}"
            if material:
                label += f"   ·   {material}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, sel)
            self._list.addItem(item)

    def _populate_materials(self, query: str) -> None:
        mats: List[Material] = search_materials(query) if query else get_materials().materials
        if not mats:
            self._add_empty()
            return
        for m in mats:
            sel = MaterialSelection(
                source=SRC_FICTITIOUS, profile_name="",
                material=m.name, quality=m.quality,
            )
            item = QListWidgetItem(format_material(m.name, m.quality))
            item.setData(Qt.ItemDataRole.UserRole, sel)
            self._list.addItem(item)

    def _populate_stock(self, query: str) -> None:
        try:
            min_len = float(self._min_len.text()) if self._min_len.text().strip() else 0.0
        except ValueError:
            min_len = 0.0
        ql = query.lower()
        bars = get_stock().bars
        rows = []
        for b in bars:
            if b.quantity <= 0:
                continue
            eff_len = b.retal_length if b.is_retal else b.length
            if eff_len < min_len:
                continue
            if ql and ql not in b.full_name.lower() and ql not in b.display_name.lower():
                continue
            rows.append((b, eff_len))
        if not rows:
            self._add_empty()
            return
        for b, eff_len in rows:
            sel = MaterialSelection(
                source=SRC_STOCK, profile_name=b.profile_name,
                material=b.material_desc, quality=b.quality, stock_bar=b,
            )
            label = f"{b.full_name}   ·   {eff_len:.0f} mm   ·   ×{b.quantity}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, sel)
            self._list.addItem(item)

    def _add_empty(self) -> None:
        item = QListWidgetItem(t("no_data"))
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self._list.addItem(item)

    # ── Accept ──────────────────────────────────────────────────────────────

    def _accept_selected(self) -> None:
        item = self._list.currentItem()
        if item is None and self._list.count() == 1:
            item = self._list.item(0)
        if item is None:
            return
        sel = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(sel, MaterialSelection):
            return
        self.result_selection = sel
        self.accept()
