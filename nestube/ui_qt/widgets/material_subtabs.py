"""
nestube/ui_qt/widgets/material_subtabs.py
Dynamic horizontal tab bar using QPushButtons.
Supports add, remove, rename (double-click). "Total" tab always last.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QMenu, QPushButton, QWidget,
)

from nestube.i18n import t

import nestube.ui_qt.theme_qt as _th


class MaterialSubTabs(QWidget):
    """Horizontal row of buttons acting as material sub-tabs."""

    tab_changed = Signal(int)
    before_switch = Signal(int, int)  # (from_index, to_index)
    tab_renamed = Signal(int, str)
    tab_added = Signal(int)
    tab_removed = Signal(int)

    def __init__(self, parent=None, has_total: bool = False) -> None:
        super().__init__(parent)
        self._has_total = has_total
        self._tabs: List[str] = []
        self._active = 0
        self._rename_edit: Optional[QLineEdit] = None
        self._rename_idx: int = -1

        # Horizontal strip of material tab buttons; flush to its container
        # (0 margins) with a tight 2px gap between tabs.
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)

        # "+" add-tab button: a square 28×28 ghost button matching the standard
        # control height used across the toolbars.
        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(28, 28)
        self._add_btn.setToolTip("Add material")
        self._add_btn.clicked.connect(self._on_add_clicked)
        self._add_btn.setProperty("variant", "ghost")

        # Optional "Total" tab (Costs view): same 28px height as the other tabs,
        # checkable, flagged via the is_total property for distinct QSS styling.
        if has_total:
            self._total_btn = QPushButton("Total")
            self._total_btn.setFixedHeight(30)
            self._total_btn.setCheckable(True)
            self._total_btn.setProperty("is_total", True)

        # Bar height fixed at 34px: 28px buttons + 3px breathing room top/bottom.
        self.setFixedHeight(34)
        self._rebuild_layout()

    # ── Public API ────────────────────────────────────────────────────────────

    def add_tab(self, name: str) -> int:
        idx = len(self._tabs)
        self._tabs.append(name)
        self._rebuild_layout()
        return idx

    def set_tabs(self, names: List[str], active: int = 0) -> None:
        """Replace every tab to mirror the data model, emitting NO signals.

        This is the safe way to sync the visual bar to ``material_contexts``
        (on load, tab switch, rename, language change). It must NOT go through
        ``remove_tab``/``add_tab`` in a loop: ``remove_tab`` emits ``tab_removed``,
        whose handlers pop a MaterialContext — so rebuilding the bar that way
        silently deletes the user's jobs/cuts. The ``tab_added``/``tab_removed``/
        ``tab_changed`` signals are reserved for genuine user actions only.
        """
        self._tabs = list(names)
        if self._tabs:
            self._active = max(0, min(int(active), len(self._tabs) - 1))
        else:
            self._active = 0
        self._rebuild_layout()

    def remove_tab(self, idx: int) -> None:
        if 0 <= idx < len(self._tabs):
            self._tabs.pop(idx)
            # Keep _active pointing at the SAME tab after the list shifts: if a tab
            # before the active one was removed, every later tab (including the
            # active one) shifts left by one, so decrement. Without this, deleting
            # a tab before the active one left _active pointing one tab to the
            # right → the wrong MaterialContext loaded (phantom pieces / lost cuts).
            if idx < self._active:
                self._active -= 1
            if self._active >= len(self._tabs):
                self._active = max(0, len(self._tabs) - 1)
            self._rebuild_layout()
            self.tab_removed.emit(idx)

    def rename_tab(self, idx: int, name: str) -> None:
        if 0 <= idx < len(self._tabs):
            self._tabs[idx] = name
            self._rebuild_layout()

    def set_active(self, idx: int) -> None:
        if 0 <= idx < len(self._tabs):
            self._active = idx
            self._update_styles()

    def active_index(self) -> int:
        return self._active

    def count(self) -> int:
        return len(self._tabs)

    def tab_name(self, idx: int) -> str:
        return self._tabs[idx] if 0 <= idx < len(self._tabs) else ""

    # ── Internal ──────────────────────────────────────────────────────────────

    def _rebuild_layout(self) -> None:
        """Rebuild the row of tab buttons from self._tabs.

        One 28px checkable button per material tab, then the persistent "+" add
        button, the optional "Total" button, and a trailing stretch so the row
        is left-aligned. Stale tab buttons are detached synchronously (see below)
        so they don't repaint over the new layout.
        """
        # Remove all widgets except stretch
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w and w is not self._add_btn:
                if not (self._has_total and hasattr(self, "_total_btn") and w is self._total_btn):
                    # hide() now so a stale button stops painting immediately;
                    # deleteLater() only fires next event loop, and until then
                    # the orphan would keep its old geometry on screen.
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()

        for idx, name in enumerate(self._tabs):
            btn = QPushButton(name)
            btn.setFixedHeight(30)
            btn.setCheckable(True)
            btn.setChecked(idx == self._active)
            btn.setProperty("tab_idx", idx)
            btn.clicked.connect(lambda checked, i=idx: self._on_tab_clicked(i))
            btn.mouseDoubleClickEvent = lambda e, i=idx: self._start_rename(i)  # type: ignore[assignment]
            # Right-click → context menu (delete tab).
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, i=idx, b=btn: self._show_tab_menu(i, b, pos))
            self._apply_tab_style(btn, idx == self._active)
            self._layout.addWidget(btn)

        self._layout.addWidget(self._add_btn)

        if self._has_total and hasattr(self, "_total_btn"):
            self._layout.addWidget(self._total_btn)

        self._layout.addStretch()

    def _apply_tab_style(self, btn: QPushButton, active: bool) -> None:
        """Style a tab button as active or inactive (borderless, 4×12 padding).

        Active: ACCENT text + bold + a 2px ACCENT bottom border (underline tab
        indicator). Inactive: TEXT_SEC with a transparent bottom border so the
        baseline stays aligned; both brighten to BG_HOVER on hover. Colours are
        live _th values so the strip follows the theme.
        """
        if active:
            btn.setStyleSheet(
                f"QPushButton {{ color: {_th.ACCENT}; border: none; border-bottom: 2px solid {_th.ACCENT};"
                f" background: transparent; font-weight: bold; padding: 4px 12px; }}"
                f"QPushButton:hover {{ background: {_th.BG_HOVER}; }}"
            )
        else:
            btn.setStyleSheet(
                f"QPushButton {{ color: {_th.TEXT_SEC}; border: none; border-bottom: 2px solid transparent;"
                f" background: transparent; padding: 4px 12px; }}"
                f"QPushButton:hover {{ color: {_th.TEXT_PRI}; background: {_th.BG_HOVER}; }}"
            )

    def _update_styles(self) -> None:
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if w and isinstance(w, QPushButton) and w.property("tab_idx") is not None:
                idx = w.property("tab_idx")
                w.setChecked(idx == self._active)
                self._apply_tab_style(w, idx == self._active)

    def _on_tab_clicked(self, idx: int) -> None:
        if idx == self._active:
            return
        self.before_switch.emit(self._active, idx)
        self._active = idx
        self._update_styles()
        self.tab_changed.emit(idx)

    def _show_tab_menu(self, idx: int, btn: QPushButton, pos) -> None:
        """Right-click menu on a material tab: delete it."""
        menu = QMenu(self)
        menu.addAction(t("delete_tab"), lambda: self._delete_tab(idx))
        menu.exec(btn.mapToGlobal(pos))

    def _delete_tab(self, idx: int) -> None:
        """Delete a material tab. Removing the last remaining tab leaves a fresh
        empty one instead of an empty bar (per the requested behaviour)."""
        last_one = len(self._tabs) <= 1
        self.remove_tab(idx)                       # emits tab_removed → context popped
        if last_one or not self._tabs:
            # Recreate a single fresh tab so there is always at least one.
            self._tabs.append("Nesting 1")
            self._active = 0
            self._rebuild_layout()
            self.tab_added.emit(0)
            self.tab_changed.emit(0)

    def _on_add_clicked(self) -> None:
        # Default label until a material is chosen (then the tab is renamed to the
        # material). Contexts are nesting contexts → "Nesting N", not "Material N".
        name = f"Nesting {len(self._tabs) + 1}"
        idx = self.add_tab(name)
        self.tab_added.emit(idx)
        self._on_tab_clicked(idx)

    def _start_rename(self, idx: int) -> None:
        self._rename_idx = idx
        # Find button for this idx
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if w and isinstance(w, QPushButton) and w.property("tab_idx") == idx:
                geo = w.geometry()
                edit = QLineEdit(self._tabs[idx], self)
                edit.setGeometry(geo)
                edit.setStyleSheet(
                    f"QLineEdit {{ background: {_th.BG_CARD}; color: {_th.TEXT_PRI};"
                    f" border: 1px solid {_th.ACCENT}; border-radius: 4px; padding: 2px 4px; }}"
                )
                edit.selectAll()
                edit.show()
                edit.setFocus()
                edit.editingFinished.connect(lambda e=edit, i=idx: self._finish_rename(e, i))
                edit.focusOutEvent = lambda ev, e=edit, i=idx: self._finish_rename(e, i)  # type: ignore[assignment]
                self._rename_edit = edit
                break

    def _finish_rename(self, edit: QLineEdit, idx: int) -> None:
        new_name = edit.text().strip() or self._tabs[idx]
        edit.deleteLater()
        self._rename_edit = None
        self.rename_tab(idx, new_name)
        self.tab_renamed.emit(idx, new_name)
