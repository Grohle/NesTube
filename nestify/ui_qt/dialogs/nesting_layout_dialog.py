"""
nestify/ui_qt/dialogs/nesting_layout_dialog.py
Configure nesting panel dock sides, snap zone, and visibility.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from nestify import app_config
from nestify.i18n import t
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.forms.ui_nesting_layout_dialog import Ui_NestingLayoutDialog


class NestingLayoutDialog(QDialog):
    """Settings dialog for nesting toolbar / sidebar layout."""

    def __init__(self, parent: QWidget, on_apply: Optional[Callable] = None) -> None:
        super().__init__(parent)
        self.ui = Ui_NestingLayoutDialog()
        self.ui.setupUi(self)

        self._on_apply = on_apply
        self.setWindowTitle(t("nesting_layout_settings"))

        prefs = app_config.get()
        self._side_raw = ["left", "right"]
        self._side_label = [t("dock_side_left"), t("dock_side_right")]

        # i18n text overrides
        self.ui.title.setText(t("nesting_layout_settings"))
        self.ui.title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")

        self.ui.lbl_pieces.setText(t("nesting_panel_left"))
        self.ui.pieces_combo.addItems(self._side_label)
        self.ui.pieces_combo.setCurrentText(self._raw_to_label(prefs.nesting_pieces_side))

        self.ui.lbl_bars.setText(t("nesting_panel_right"))
        self.ui.bars_combo.addItems(self._side_label)
        self.ui.bars_combo.setCurrentText(self._raw_to_label(prefs.nesting_bars_side))

        self.ui.hint.setText(t("nesting_stack_hint"))

        self.ui.lbl_snap_zone.setText(t("nesting_snap_zone_mm"))
        self.ui.snap_zone.setText(str(prefs.nesting_snap_zone_mm))

        self.ui.use_colors.setText(t("nesting_use_cut_colors"))
        self.ui.use_colors.setChecked(prefs.nesting_use_cut_colors)

        # Signal connections
        self.ui.button_box.accepted.connect(self._apply)
        self.ui.button_box.rejected.connect(self.reject)

    def _raw_to_label(self, raw: str) -> str:
        try:
            return self._side_label[self._side_raw.index(raw)]
        except ValueError:
            return self._side_label[0]

    def _label_to_raw(self, label: str) -> str:
        try:
            return self._side_raw[self._side_label.index(label)]
        except ValueError:
            return "left"

    def _apply(self) -> None:
        prefs = app_config.get()
        prefs.nesting_pieces_side = self._label_to_raw(self.ui.pieces_combo.currentText())
        prefs.nesting_bars_side = self._label_to_raw(self.ui.bars_combo.currentText())
        prefs.nesting_use_cut_colors = self.ui.use_colors.isChecked()
        try:
            prefs.nesting_snap_zone_mm = max(5.0, float(self.ui.snap_zone.text()))
        except ValueError:
            QMessageBox.warning(self, t("warning"), t("nesting_snap_zone_invalid"))
            return
        app_config.save()
        if self._on_apply:
            self._on_apply()
        self.accept()
