"""
nestify/ui_qt/widgets/material_autocomplete.py
Autocomplete widgets for material/quality fields.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtCore import QStringListModel
from PySide6.QtWidgets import (
    QCompleter, QHBoxLayout, QLineEdit, QPushButton,
    QWidget,
)

from nestify.ui_qt.icons import themed_icon


class SimpleAutocomplete(QWidget):
    """Single QLineEdit with debounced dropdown suggestions from a source callable."""

    selected = Signal(str)

    def __init__(
        self,
        placeholder: str = "",
        source: Optional[Callable[[str], List[str]]] = None,
        on_select: Optional[Callable[[str], None]] = None,
        height: int = 28,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._source = source or (lambda _: [])
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(180)
        self._debounce.timeout.connect(self._update_completions)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText(placeholder)
        self._entry.setFixedHeight(height)
        self._entry.textChanged.connect(lambda _: self._debounce.start())
        layout.addWidget(self._entry)

        self._model = QStringListModel()
        self._completer = QCompleter(self._model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._entry.setCompleter(self._completer)

        if on_select:
            self.selected.connect(on_select)
        self._completer.activated.connect(self._on_activated)

    def sizeHint(self) -> "QSize":
        from PySide6.QtCore import QSize
        return QSize(200, self._entry.height())

    def value(self) -> str:
        return self._entry.text()

    def set_value(self, v: str) -> None:
        self._entry.blockSignals(True)
        self._entry.setText(v)
        self._entry.blockSignals(False)

    def setPlaceholderText(self, text: str) -> None:
        self._entry.setPlaceholderText(text)

    def _update_completions(self) -> None:
        text = self._entry.text()
        suggestions = self._source(text)
        self._model.setStringList(suggestions)

    def _on_activated(self, text: str) -> None:
        self.selected.emit(text)


class MaterialAutocomplete(QWidget):
    """Material + quality autocomplete pair with optional material picker dialog."""

    picked = Signal(str, str)  # (material, quality)

    def __init__(
        self,
        placeholder_material: str = "Material",
        placeholder_quality: str = "Quality",
        on_pick: Optional[Callable[[str, str], None]] = None,
        stock_source: Optional[Callable[[], List[str]]] = None,
        height: int = 28,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._stock_source = stock_source or (lambda: [])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Material entry with autocomplete
        self._material_ac = SimpleAutocomplete(
            placeholder=placeholder_material,
            source=self._material_suggestions,
            height=height,
        )
        self._material_ac._entry.textChanged.connect(self._on_material_changed)
        layout.addWidget(self._material_ac, 2)

        # Quality entry with autocomplete
        self._quality_ac = SimpleAutocomplete(
            placeholder=placeholder_quality,
            source=self._quality_suggestions,
            height=height,
        )
        layout.addWidget(self._quality_ac, 1)

        # Material picker button. Themed SVG magnifier (not a 🔍 emoji, which
        # renders inconsistently on Linux); retinted on theme switch via
        # refresh_icon().
        self._picker_btn = QPushButton()
        self._picker_btn.setFixedSize(height, height)
        self._picker_btn.setProperty("variant", "icon")
        self._picker_btn.setIconSize(QSize(16, 16))
        self._picker_btn.setToolTip("Search material")
        self._picker_btn.clicked.connect(self._open_picker)
        layout.addWidget(self._picker_btn)
        self.refresh_icon()

        if on_pick:
            self.picked.connect(on_pick)

    def refresh_icon(self) -> None:
        """Re-tint the magnifier icon to the live theme text colour."""
        self._picker_btn.setIcon(themed_icon("search"))

    def sizeHint(self) -> "QSize":
        return QSize(400, self._picker_btn.height())

    def material(self) -> str:
        return self._material_ac.value()

    def quality(self) -> str:
        return self._quality_ac.value()

    def set_material(self, m: str) -> None:
        self._material_ac.set_value(m)

    def set_quality(self, q: str) -> None:
        self._quality_ac.set_value(q)

    def _material_suggestions(self, text: str) -> List[str]:
        seen: set = set()
        result: List[str] = []
        tl = text.lower()

        # Primary source: stock database (bars already in use)
        try:
            from nestify.stock_db import get_stock
            for b in get_stock().bars:
                md = b.material_desc
                if md and md not in seen and tl in md.lower():
                    seen.add(md)
                    result.append(md)
        except Exception:
            pass

        # Fallback / supplement: materials defined in the materials manager
        try:
            from nestify.materials_db import get_materials_db
            for m in get_materials_db().list_materials():
                name = m.get("name", "")
                qual = m.get("quality", "")
                label = f"{name} {qual}".strip() if qual else name
                if label and label not in seen and tl in label.lower():
                    seen.add(label)
                    result.append(label)
        except Exception:
            pass

        return sorted(result)[:20]

    def _quality_suggestions(self, text: str) -> List[str]:
        from nestify.stock_db import get_stock
        try:
            bars = get_stock().bars
            mat = self._material_ac.value().lower()
            seen = set()
            result = []
            tl = text.lower()
            for b in bars:
                if mat and mat not in b.material_desc.lower():
                    continue
                q = b.quality or ""
                if q and q not in seen and tl in q.lower():
                    seen.add(q)
                    result.append(q)
            return sorted(result)[:20]
        except Exception:
            return []

    def _on_material_changed(self, text: str) -> None:
        # Reset quality when material changes
        pass

    def _open_picker(self) -> None:
        try:
            from nestify.ui_qt.dialogs.material_picker_dialog import MaterialPickerDialog
            dlg = MaterialPickerDialog(parent=self.window())
            if dlg.exec():
                mat, qual = dlg.result_material, dlg.result_quality
                self.set_material(mat)
                self.set_quality(qual)
                self.picked.emit(mat, qual)
        except Exception:
            pass
