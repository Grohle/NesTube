"""
nestube/ui_qt/dialogs/material_picker_dialog.py
Search and pick a material or profile from the database.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QWidget

from nestube.i18n import t
from nestube.materials_db import Material, get_materials, search_materials
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.forms.ui_material_picker_dialog import Ui_MaterialPickerDialog


class MaterialPickerDialog(QDialog):
    """Modal list to pick a material (name + quality) or a custom profile."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_select: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_MaterialPickerDialog()
        self.ui.setupUi(self)

        self._on_select = on_select

        # Result attributes — set when the user picks an entry.
        self.result_material: str = ""
        self.result_quality: str = ""
        self.result_profile_id: Optional[str] = None

        self.setWindowTitle(t("material_search"))

        # i18n text overrides
        self.ui.title.setText(t("material_search"))
        self.ui.title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")

        self.ui.search.setPlaceholderText(t("placeholder_material"))
        self.ui.manage_btn.setText(t("manage_materials"))

        self.ui.scroll.setStyleSheet(
            f"QScrollArea {{ background: {_th.BG_CARD}; border: none; }}"
        )

        # Signal connections
        self.ui.search.textChanged.connect(self._refresh_list)
        self.ui.search.returnPressed.connect(self._pick_first)
        self.ui.manage_btn.clicked.connect(self._open_manager)

        self._refresh_list()
        self.ui.search.setFocus()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _section_header(self, text: str) -> QLabel:
        """Return a bold accent-colored section header label."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {_th.ACCENT}; font-weight: bold; font-size: 11px;"
        )
        return lbl

    def _empty_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {_th.TEXT_DIM};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _make_row_btn(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(28)
        btn.setStyleSheet(
            f"QPushButton {{ text-align: left; padding-left: 8px; "
            f"background: {_th.BG_MID}; color: {_th.TEXT_PRI}; border: none; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {_th.ACCENT}; }}"
        )
        return btn

    # ── list population ───────────────────────────────────────────────────────

    def _refresh_list(self) -> None:
        while self.ui.list_layout.count():
            item = self.ui.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self.ui.search.text().strip()

        # ── Profiles & Tubes section ─────────────────────────────────────────
        self.ui.list_layout.addWidget(self._section_header(t("profiles_and_tubes")))

        from nestube import app_config
        profiles = app_config.get().custom_profiles
        if query:
            q_lower = query.lower()
            profiles = [p for p in profiles if q_lower in p.name.lower()]

        if profiles:
            for profile in profiles:
                btn = self._make_row_btn(profile.name)
                btn.clicked.connect(
                    lambda checked=False, p=profile: self._pick_profile(p)
                )
                self.ui.list_layout.addWidget(btn)
        else:
            self.ui.list_layout.addWidget(self._empty_label(t("no_profiles")))

        # ── Materials section ─────────────────────────────────────────────────
        self.ui.list_layout.addWidget(self._section_header(t("materials")))

        mat_items = search_materials(query) if query else get_materials().materials

        if mat_items:
            for mat in mat_items:
                btn = self._make_row_btn(mat.display)
                btn.setFixedHeight(30)
                btn.clicked.connect(
                    lambda checked=False, m=mat: self._pick_material(m)
                )
                self.ui.list_layout.addWidget(btn)
        else:
            self.ui.list_layout.addWidget(self._empty_label(t("no_materials")))

        self.ui.list_layout.addStretch()

    def _pick_first(self) -> None:
        """Pick the first available entry (profile or material) on Enter."""
        query = self.ui.search.text().strip()

        from nestube import app_config
        profiles = app_config.get().custom_profiles
        if query:
            q_lower = query.lower()
            profiles = [p for p in profiles if q_lower in p.name.lower()]

        if profiles:
            self._pick_profile(profiles[0])
            return

        mat_items = search_materials(query) if query else get_materials().materials
        if mat_items:
            self._pick_material(mat_items[0])

    # ── pick handlers ─────────────────────────────────────────────────────────

    def _pick_profile(self, profile) -> None:
        self.result_profile_id = profile.name
        self.result_material = ""
        self.result_quality = ""
        if self._on_select is not None:
            # Build a small compat object for callers that use on_select.
            class _ProfileResult:
                def __init__(self, p):
                    self.name = ""
                    self.quality = ""
                    self.profile_id = p.name
            self._on_select(_ProfileResult(profile))
        self.accept()

    def _pick_material(self, mat: Material) -> None:
        self.result_profile_id = None
        self.result_material = mat.name
        self.result_quality = mat.quality
        if self._on_select is not None:
            self._on_select(mat)
        self.accept()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _open_manager(self) -> None:
        from nestube.ui_qt.dialogs.materials_manager import MaterialsManagerDialog
        dlg = MaterialsManagerDialog(self)
        dlg.exec()
        self._refresh_list()
