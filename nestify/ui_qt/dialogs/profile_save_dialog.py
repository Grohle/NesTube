"""
nestify/ui_qt/dialogs/profile_save_dialog.py
Dialog to fill in profile details when saving from the creator.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QCompleter, QDialog, QWidget

from nestify.i18n import t
from nestify.naming import BASE_MATERIALS as _BUILTIN_MATERIALS, canonical_material, localize_material
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.forms.ui_profile_save_dialog import Ui_ProfileSaveDialog


class ProfileSaveDialog(QDialog):
    """Form dialog for entering profile name, material, quality, notes, and fields."""

    def __init__(
        self,
        parent: QWidget,
        fields: list,
        on_confirm: Optional[Callable] = None,
        initial_name: str = "",
        initial_quality: str = "",
        initial_notes: str = "",
        initial_material: str = "",
        edit_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_ProfileSaveDialog()
        self.ui.setupUi(self)

        self._on_confirm = on_confirm
        self._fields_list = fields
        self._result = None

        self.setWindowTitle(t("edit_profile_type") if edit_mode else t("add_profile_type"))
        self.ui.lbl_name.setText(t("field_name") + " *")
        self.ui.e_name.setPlaceholderText(t("field_name"))
        self.ui.lbl_material.setText(t("stock_material"))
        self.ui.lbl_sw.setText(t("specific_weight", u_density="t/m³"))
        self.ui.lbl_sw.setStyleSheet(f"color: {_th.TEXT_SEC};")
        self.ui.lbl_sw_value.setStyleSheet(f"color: {_th.TEXT_SEC};")
        self.ui.lbl_quality.setText(t("placeholder_quality"))
        self.ui.e_quality.setPlaceholderText(t("placeholder_quality"))
        self.ui.lbl_notes.setText(t("notes"))
        self.ui.lbl_fields.setText(t("profile_edit_fields"))
        self.ui.lbl_hint.setText(t("profile_save_hint"))
        self.ui.lbl_hint.setStyleSheet(f"color: {_th.TEXT_SEC};")

        self.ui.e_name.setText(initial_name)
        self.ui.e_quality.setText(initial_quality)
        if initial_notes:
            self.ui.e_notes.setPlainText(initial_notes)
        self.ui.e_fields.setText(", ".join(fields))

        self._setup_name_completer()
        self._setup_material_combo(initial_material)

        self.ui.button_box.accepted.connect(self._confirm)
        self.ui.button_box.rejected.connect(self.reject)

    def _setup_name_completer(self) -> None:
        names: list[str] = []
        for cp in __import__("nestify.app_config", fromlist=["get"]).get().custom_profiles:
            if cp.name:
                names.append(cp.name)
        if not names:
            return
        model = QStringListModel(sorted(set(names)))
        completer = QCompleter(model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.ui.e_name.setCompleter(completer)

    def _setup_material_combo(self, initial_material: str) -> None:
        from nestify.materials_db import get_materials
        self.ui.combo_material.clear()
        self.ui.combo_material.addItem("", 0.0)

        # Built-in materials are shown with their localised label but stored
        # canonically (see naming.canonical_material), so existing data matches.
        seen: set[str] = set()
        for name, sw in _BUILTIN_MATERIALS:
            self.ui.combo_material.addItem(localize_material(name), sw)
            seen.add(name.lower())

        for mat in get_materials().materials:
            if mat.name.lower() not in seen:
                self.ui.combo_material.addItem(mat.name, mat.specific_weight)
                seen.add(mat.name.lower())

        if initial_material:
            # initial_material is canonical; match it by its localised label.
            idx = self.ui.combo_material.findText(localize_material(initial_material))
            if idx >= 0:
                self.ui.combo_material.setCurrentIndex(idx)
            else:
                self.ui.combo_material.addItem(initial_material, 7.85)
                self.ui.combo_material.setCurrentText(initial_material)

        self.ui.combo_material.currentIndexChanged.connect(self._on_material_changed)
        self._on_material_changed()

    def _on_material_changed(self) -> None:
        sw = self.ui.combo_material.currentData()
        if sw:
            self.ui.lbl_sw_value.setText(f"{float(sw):.2f} t/m³")
        else:
            self.ui.lbl_sw_value.setText("—")

    def _confirm(self) -> None:
        name = self.ui.e_name.text().strip()
        if not name:
            self.ui.e_name.setFocus()
            return

        quality = self.ui.e_quality.text().strip()
        notes = self.ui.e_notes.toPlainText().strip()
        fields_str = self.ui.e_fields.text().strip()
        fields = [f.strip() for f in fields_str.split(",") if f.strip()] or self._fields_list

        # Convert the (possibly localised) label back to the canonical name.
        material = canonical_material(self.ui.combo_material.currentText().strip())
        sw_data = self.ui.combo_material.currentData()
        specific_weight = float(sw_data) if sw_data else 7.85

        self._result = {
            "name": name,
            "quality": quality,
            "notes": notes,
            "fields": fields,
            "material": material,
            "specific_weight": specific_weight,
        }

        if self._on_confirm:
            self._on_confirm(self._result)
        self.accept()

    @property
    def result(self):
        return self._result
