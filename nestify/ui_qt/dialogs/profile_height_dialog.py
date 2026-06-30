"""
nestify/ui_qt/dialogs/profile_height_dialog.py

Dialog to pick which profile face/height to use as the nesting (bevel) height
when a profile exposes several candidates. Each candidate is shown as a large
clickable button — clicking one selects it and accepts the dialog. Returns the
chosen height in mm.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from nestify.i18n import t
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.nesting_scene import _text_color_for_bg


class ProfileHeightDialog(QDialog):
    """Choose one of several possible profile heights for nesting.

    The candidate rows are clickable buttons (click = choose + accept). A
    Cancel button is provided for callers that want to allow dismissal.
    """

    def __init__(self, heights: List[Tuple[str, float]], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("profile_height_select"))
        self.setModal(True)
        self.setMinimumWidth(320)
        self._heights = heights
        self._chosen: Optional[float] = heights[0][1] if heights else None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        hint = QLabel(t("profile_height_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:11px;")
        root.addWidget(hint)

        for label, val in heights:
            btn = QPushButton(f"{label}:  {val:.1f} mm")
            btn.setMinimumHeight(40)
            btn.setStyleSheet(
                f"QPushButton {{ background:{_th.BG_CARD}; color:{_th.TEXT_PRI};"
                f" border:1px solid {_th.BORDER}; border-radius:6px;"
                f" padding:8px 14px; font-size:13px; text-align:left; }}"
                f"QPushButton:hover {{ border:1px solid {_th.ACCENT};"
                f" background:{_th.BG_MID}; }}"
            )
            btn.clicked.connect(lambda _checked=False, v=val: self._choose(v))
            root.addWidget(btn)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.setMinimumHeight(30)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        root.addLayout(btn_row)

    def _choose(self, value: float) -> None:
        self._chosen = value
        self.accept()

    def chosen_height(self) -> Optional[float]:
        return self._chosen
