"""
nestify/ui_qt/dialogs/cost_defaults_dialog.py

Dialog to edit the GLOBAL cost defaults (§24) — the profile-INDEPENDENT cost
parameters (operator cost, straight-cut time, mitre extra %, profit margin) that
seed a brand-new job / material context. Values are stored in
AppPreferences.default_* and applied when a fresh context is created.

These are deliberately NOT the profile-specific values (€/kg, kg/m, etc.), which
come from the selected material/profile and are edited per sub-tab in the Costs
tab. Mirrors the OptimizationTimesDialog structure.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout, QLabel, QVBoxLayout,
)

from nestify import app_config
from nestify.i18n import t


class CostDefaultsDialog(QDialog):
    """Edit the profile-independent cost defaults for new jobs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("cost_defaults"))
        self.setModal(True)
        self._prefs = app_config.get()

        root = QVBoxLayout(self)

        hint = QLabel(t("cost_defaults_hint"))
        hint.setWordWrap(True)
        root.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # (pref attribute, label key, suffix, max, decimals)
        self._rows = [
            ("default_operator_cost", "operator_cost_plain", " /h", 100000.0, 2),
            ("default_cut_time",      "straight_cut_time",   " min", 1000.0, 2),
            ("default_miter_pct",     "miter_extra_pct",     " %",   1000.0, 1),
            ("default_profit_margin", "profit_margin",       " %",   1000.0, 1),
        ]
        self._spins: dict[str, QDoubleSpinBox] = {}
        for i, (attr, key, suffix, top, decimals) in enumerate(self._rows):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, top)
            spin.setDecimals(decimals)
            spin.setSingleStep(0.5)
            spin.setSuffix(suffix)
            spin.setValue(float(getattr(self._prefs, attr, 0.0)))
            spin.setFixedHeight(30)
            grid.addWidget(QLabel(t(key)), i, 0)
            grid.addWidget(spin, i, 1)
            self._spins[attr] = spin
        root.addLayout(grid)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _save(self) -> None:
        for attr, spin in self._spins.items():
            setattr(self._prefs, attr, max(0.0, float(spin.value())))
        app_config.save(self._prefs)
        self.accept()
