"""
nestify/ui_qt/widgets/stock_material_search_bar.py
Single-field stock/material search bar for the Cuts header (TODO §2.2).

Replaces the old material+quality autocomplete pair. Behaviour:

  • Typing shows live suggestions (full names of stock bars + DB
    materials) in a completer popup. Picking a suggestion selects it
    directly (fast path).
  • The magnifier button — or pressing Enter — opens the full search
    window (:class:`StockMaterialSearchDialog`) pre-filtered by the typed
    text, for filtered browsing across stock / fictitious materials.
  • Once selected, the field shows the canonical full name
    ``profile · material · quality`` and the widget remembers the
    selection parts.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QSize, Qt, QStringListModel, Signal
from PySide6.QtWidgets import (
    QCompleter, QHBoxLayout, QLineEdit, QPushButton, QWidget,
)

from nestify.naming import format_full_name, format_material
from nestify.ui_qt.icons import themed_icon


class StockMaterialSearchBar(QWidget):
    """Search field + magnifier that yields a MaterialSelection."""

    # Emitted with a MaterialSelection when the user picks one.
    selected = Signal(object)

    def __init__(self, placeholder: str = "", height: int = 30, parent=None) -> None:
        super().__init__(parent)
        # Current selection parts (so callers can read them back).
        self._profile_name = ""
        self._material = ""
        self._quality = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText(placeholder)
        self._entry.setFixedHeight(height)
        self._entry.returnPressed.connect(self._open_dialog)
        layout.addWidget(self._entry, 1)

        # Live suggestion popup built from the current stock + materials DB.
        self._model = QStringListModel()
        self._completer = QCompleter(self._model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._entry.setCompleter(self._completer)
        self._entry.textEdited.connect(self._update_suggestions)
        self._completer.activated.connect(self._on_suggestion_activated)

        self._btn = QPushButton()
        self._btn.setFixedSize(height, height)
        self._btn.setProperty("variant", "icon")
        self._btn.setIconSize(QSize(16, 16))
        self._btn.clicked.connect(self._open_dialog)
        layout.addWidget(self._btn)
        self.refresh_icon()

    # ── Public API ──────────────────────────────────────────────────────────

    def refresh_icon(self) -> None:
        self._btn.setIcon(themed_icon("search"))

    def sizeHint(self) -> QSize:
        return QSize(360, self._entry.height())

    def material(self) -> str:
        return self._material

    def quality(self) -> str:
        return self._quality

    def profile_name(self) -> str:
        return self._profile_name

    def set_selection(self, profile_name: str, material: str, quality: str) -> None:
        """Display a selection without emitting :pyattr:`selected`."""
        self._profile_name = profile_name or ""
        self._material = material or ""
        self._quality = quality or ""
        self._entry.blockSignals(True)
        self._entry.setText(format_full_name(self._profile_name, self._material, self._quality))
        self._entry.blockSignals(False)

    def clear(self) -> None:
        self.set_selection("", "", "")

    # ── Suggestions ─────────────────────────────────────────────────────────

    def _all_options(self) -> List["object"]:
        """Build (full_name, MaterialSelection) pairs from profiles + stock + materials."""
        from nestify.ui_qt.dialogs.stock_material_search_dialog import (
            MaterialSelection, SRC_FICTITIOUS, SRC_PROFILE, SRC_STOCK,
        )
        out: list = []
        seen: set = set()
        try:
            from nestify import app_config as _ac
            for cp in getattr(_ac.get(), "custom_profiles", []):
                name = cp.name
                if name and name not in seen:
                    seen.add(name)
                    material = cp.meta.get("material", "") if hasattr(cp, "meta") and cp.meta else ""
                    out.append((name, MaterialSelection(
                        source=SRC_PROFILE, profile_name=cp.name,
                        material=material, quality=getattr(cp, "quality", ""),
                    )))
        except Exception:
            pass
        try:
            from nestify.stock_db import get_stock
            for b in get_stock().bars:
                if b.quantity <= 0:
                    continue
                name = b.full_name
                if name and name not in seen:
                    seen.add(name)
                    out.append((name, MaterialSelection(
                        source=SRC_STOCK, profile_name=b.profile_name,
                        material=b.material_desc, quality=b.quality, stock_bar=b,
                    )))
        except Exception:
            pass
        try:
            from nestify.materials_db import get_materials
            for m in get_materials().materials:
                name = format_material(m.name, m.quality)
                if name and name not in seen:
                    seen.add(name)
                    out.append((name, MaterialSelection(
                        source=SRC_FICTITIOUS, profile_name="",
                        material=m.name, quality=m.quality,
                    )))
        except Exception:
            pass
        return out

    def _update_suggestions(self, _text: str) -> None:
        self._options = self._all_options()
        self._model.setStringList([name for name, _ in self._options])

    def _on_suggestion_activated(self, text: str) -> None:
        for name, sel in getattr(self, "_options", []):
            if name == text:
                self._emit(sel)
                return

    # ── Dialog ──────────────────────────────────────────────────────────────

    def _open_dialog(self) -> None:
        from nestify.ui_qt.dialogs.stock_material_search_dialog import (
            StockMaterialSearchDialog,
        )
        dlg = StockMaterialSearchDialog(parent=self.window(), initial_query=self._entry.text().strip())
        if dlg.exec() and dlg.result_selection is not None:
            self._emit(dlg.result_selection)

    def _emit(self, sel) -> None:
        self.set_selection(sel.profile_name, sel.material, sel.quality)
        self.selected.emit(sel)
