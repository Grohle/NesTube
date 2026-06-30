"""
nestube/ui_qt/dialogs/optimization_times_dialog.py

Dialog to edit the auto-nest optimization time limits (levels 1–5 in seconds;
level 6 is unlimited). Mirrors the legacy _configure_opt_times flow. Values are
stored in AppPreferences.opt_time_level_*.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout, QLabel, QVBoxLayout,
)

from nestube import app_config
from nestube.i18n import t


class OptimizationTimesDialog(QDialog):
    """Edit per-level optimization time limits (seconds)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("opt_time_levels"))
        self.setModal(True)
        self._prefs = app_config.get()

        # Label/spin grid: 10px between the label and the field column, 6px
        # between rows.
        root = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # Levels 1–5 are editable second limits (0.1–3600s, 0.5s steps); each
        # spin box is 30px tall to match the standard control height.
        self._spins: dict[int, QDoubleSpinBox] = {}
        for level in range(1, 6):
            spin = QDoubleSpinBox()
            spin.setRange(0.1, 3600.0)
            spin.setDecimals(1)
            spin.setSingleStep(0.5)
            spin.setSuffix(" s")
            spin.setValue(float(getattr(self._prefs, f"opt_time_level_{level}", level)))
            spin.setFixedHeight(30)
            grid.addWidget(QLabel(t("opt_time_level_n", n=level)), level - 1, 0)
            grid.addWidget(spin, level - 1, 1)
            self._spins[level] = spin

        # Level 6 is a fixed "unlimited" row (no spin box, just a caption).
        grid.addWidget(QLabel(t("opt_time_level_n", n=6)), 5, 0)
        grid.addWidget(QLabel(t("opt_level_unlimited")), 5, 1)
        root.addLayout(grid)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _save(self) -> None:
        for level, spin in self._spins.items():
            setattr(self._prefs, f"opt_time_level_{level}", max(0.1, float(spin.value())))
        app_config.save(self._prefs)
        self.accept()
