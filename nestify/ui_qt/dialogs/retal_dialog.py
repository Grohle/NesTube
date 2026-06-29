"""
nestify/ui_qt/dialogs/retal_dialog.py
Dialog to generate remnants (retales) from current nesting bars and add them to stock.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QLabel, QMessageBox, QWidget,
)

from nestify import units
from nestify.i18n import t
from nestify.ui_qt.forms.ui_retal_dialog import Ui_GenerarRetalesDialog
import nestify.ui_qt.theme_qt as _th


class GenerarRetalesDialog(QDialog):
    """Shows computed remnants for each nesting bar and lets the user add them to stock."""

    def __init__(
        self,
        parent: QWidget,
        bar_data: List[Tuple[int, float, float]],
        profile_name: str = "",
        material_desc: str = "",
        on_added: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_GenerarRetalesDialog()
        self.ui.setupUi(self)

        self._bar_data = bar_data
        self._profile_name = profile_name
        self._material_desc = material_desc
        self._on_added = on_added
        self._rows: List[dict] = []

        # Layout comes from the .ui form (ui_retal_dialog); here we only set the
        # localised text and the theme colours. Visual model: ACCENT bold title,
        # a BG_MID header row (Bar | Length | %), a BG_CARD scroll list of
        # candidate remnants, and a TEXT_SEC status line.
        # i18n: override text with t() calls after setupUi()
        self.setWindowTitle(t("generate_retales"))
        self.ui.title.setText(t("generate_retales"))
        self.ui.title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")
        self.ui.lbl_min_len.setText(t("min_retal_length", u=units.u_len()))
        self.ui.lbl_desc.setText(t("retal_description"))
        self.ui.refresh_btn.setText(t("retal_update"))

        # Header row
        self.ui.hdr.setStyleSheet(f"background: {_th.BG_MID};")
        self.ui.hdr_bar.setText(t("retal_bar_col"))
        self.ui.hdr_length.setText(t("retal_length_col") + f" ({units.u_len()})")
        self.ui.hdr_pct.setText("%")

        # Scroll area styling
        self.ui.scroll.setStyleSheet(f"QScrollArea {{ background: {_th.BG_CARD}; border: none; }}")

        # Status label
        self.ui.status_lbl.setText("")
        self.ui.status_lbl.setStyleSheet(f"color: {_th.TEXT_SEC};")

        # Buttons
        self.ui.ok_btn.setText(t("retal_add_ok"))
        self.ui.ok_btn.setProperty("variant", "accent")
        self.ui.cancel_btn.setText(t("cancel"))

        # Populate min length and description defaults
        from nestify.stock_db import get_stock
        default_min = get_stock().min_retal_length
        self.ui.min_len.setText(str(int(default_min)))
        self.ui.desc.setText(self._material_desc or self._profile_name)

        # "Delete selected" + "Delete all" buttons — inserted before spacer
        from PySide6.QtWidgets import QPushButton as _QB
        self._del_sel_btn = _QB(t("retal_delete_selected"))
        self._del_all_btn = _QB(t("retal_delete_all"))
        self._del_sel_btn.setProperty("variant", "ghost")
        self._del_all_btn.setProperty("variant", "ghost")
        self.ui.bottom_layout.insertWidget(0, self._del_sel_btn)
        self.ui.bottom_layout.insertWidget(1, self._del_all_btn)

        # Signal connections
        self.ui.refresh_btn.clicked.connect(self._refresh_list)
        self.ui.ok_btn.clicked.connect(self._add_to_stock)
        self.ui.cancel_btn.clicked.connect(self.reject)
        self._del_sel_btn.clicked.connect(self._delete_selected)
        self._del_all_btn.clicked.connect(self._delete_all)

        self._refresh_list()

    def _refresh_list(self) -> None:
        while self.ui.list_layout.count():
            item = self.ui.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()

        try:
            min_len = float(self.ui.min_len.text())
        except ValueError:
            min_len = 0.0

        qualifying = []
        for bar_idx, bar_len, used_len in self._bar_data:
            retal = bar_len - used_len
            if retal >= min_len and bar_len > 0:
                pct = (used_len / bar_len * 100) if bar_len > 0 else 0
                qualifying.append((bar_idx, bar_len, retal, pct))

        if not qualifying:
            lbl = QLabel(t("retal_no_qualifying"))
            lbl.setStyleSheet(f"color: {_th.TEXT_DIM};")
            self.ui.list_layout.addWidget(lbl, 0, 0, 1, 4)
            self.ui.status_lbl.setText("")
            self.ui.ok_btn.setEnabled(False)
            return

        self.ui.ok_btn.setEnabled(True)
        for row_idx, (bar_idx, bar_len, retal, pct) in enumerate(qualifying):
            cb = QCheckBox()
            cb.setChecked(True)
            self.ui.list_layout.addWidget(cb, row_idx, 0)

            bar_lbl = QLabel(t("bar_n", n=bar_idx + 1))
            bar_lbl.setStyleSheet(f"color: {_th.TEXT_PRI};")
            self.ui.list_layout.addWidget(bar_lbl, row_idx, 1)

            len_lbl = QLabel(f"{retal:.0f}")
            len_lbl.setStyleSheet(f"color: {_th.TEXT_SEC};")
            self.ui.list_layout.addWidget(len_lbl, row_idx, 2)

            pct_lbl = QLabel(f"{100 - pct:.1f}%")
            pct_lbl.setStyleSheet(f"color: {_th.TEXT_DIM};")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.ui.list_layout.addWidget(pct_lbl, row_idx, 3)

            self._rows.append({
                "cb": cb,
                "bar_idx": bar_idx,
                "retal_mm": retal,
            })

        self.ui.status_lbl.setText(t("retal_qualifying") + f": {len(qualifying)}")

    def _delete_selected(self) -> None:
        """Remove checked rows from the list (they won't be added to stock)."""
        self._rows = [r for r in self._rows if not r["cb"].isChecked()]
        self._refresh_list()

    def _delete_all(self) -> None:
        """Remove all rows from the list."""
        self._rows.clear()
        self._refresh_list()

    def _add_to_stock(self) -> None:
        from nestify.stock_db import add_retal

        profile = self._profile_name.strip()
        mat_desc = self.ui.desc.text().strip() or profile

        selected = [r for r in self._rows if r["cb"].isChecked()]
        if not selected:
            QMessageBox.warning(self, t("warning"), t("retal_no_qualifying"))
            return

        added = 0
        for row in selected:
            result = add_retal(
                profile_name=profile,
                material_desc=mat_desc,
                retal_length=row["retal_mm"],
            )
            if result is not None:
                added += 1

        QMessageBox.information(
            self, t("generate_retales"), t("retales_added_n", n=added),
        )

        if self._on_added:
            self._on_added(added)
        self.accept()
