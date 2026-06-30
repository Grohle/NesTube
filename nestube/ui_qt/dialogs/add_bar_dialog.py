"""
nestube/ui_qt/dialogs/add_bar_dialog.py
Dialog to add bars to nesting — from stock (with checkboxes) or fictitious.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from nestube import units
from nestube.i18n import t
from nestube.stock_db import StockBar, get_available_bars
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.forms.ui_add_bar_dialog import Ui_AddBarDialog
from nestube.ui_qt.icons import themed_icon


class AddBarDialog(QDialog):
    """Dialog to select bars from stock or create fictitious ones."""

    def __init__(
        self,
        parent: QWidget,
        material: str = "",
        quality: str = "",
        default_length: float = 6000,
        on_confirm: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_AddBarDialog()
        self.ui.setupUi(self)
        # Base layout from the .ui form; the body is built in code into
        # ui.main_layout in one of two modes: _build_stock_mode (checkable list
        # of matching stock bars) when stock exists, else _build_fictitious_mode
        # (a plain length/qty form).

        self.setWindowTitle(t("add_bar"))

        self._material = material
        self._quality = quality
        self._default_length = default_length
        self._on_confirm = on_confirm
        self._check_boxes: List[QCheckBox] = []
        self._available: List[StockBar] = []

        if material:
            self._available = get_available_bars(profile_name=material)

        if self._available:
            self._build_stock_mode()
        else:
            self._build_fictitious_mode()

    def _clear_layout(self) -> None:
        while self.ui.main_layout.count():
            item = self.ui.main_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def _build_stock_mode(self) -> None:
        # Header band: fixed 50px tall, BG_CARD, holding the "available stock —
        # material" title (ACCENT bold) plus an optional quality tag, left-aligned
        # with a trailing stretch.
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(f"background: {_th.BG_CARD};")
        h_layout = QHBoxLayout(header)
        title_text = f"{t('stock_available')} — {self._material}"
        title = QLabel(title_text)
        title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")
        h_layout.addWidget(title)
        if self._quality:
            qual = QLabel(f"({self._quality})")
            qual.setStyleSheet(f"color: {_th.TEXT_SEC};")
            h_layout.addWidget(qual)
        h_layout.addStretch()
        self.ui.main_layout.addWidget(header)

        # Scrollable list of available bars; rows packed 2px apart inside an
        # 8px margin so many bars fit without feeling cramped.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(8, 8, 8, 8)
        list_layout.setSpacing(2)

        self._check_boxes.clear()
        for bar in self._available:
            row = QHBoxLayout()
            cb = QCheckBox()
            self._check_boxes.append(cb)
            row.addWidget(cb)

            info = QVBoxLayout()
            info.setSpacing(0)
            name_lbl = QLabel(bar.display_name)
            name_lbl.setStyleSheet(f"color: {_th.TEXT_PRI};")
            info.addWidget(name_lbl)

            # Secondary detail line (length · qty · retal): smaller 11px TEXT_SEC.
            details = f"{bar.length:.0f} {units.u_len()}  ·  ×{bar.quantity}"
            if bar.is_retal:
                details += f"  ·  {t('stock_retal')}"
            det_lbl = QLabel(details)
            det_lbl.setStyleSheet(f"color: {_th.TEXT_SEC}; font-size: 11px;")
            info.addWidget(det_lbl)
            row.addLayout(info, 1)

            # Availability dot: SUCCESS green when in stock, else TEXT_SEC; fixed
            # 20px column so all dots line up at the right edge of every row.
            status_color = _th.SUCCESS if bar.quantity > 0 else _th.TEXT_SEC
            dot = QLabel()
            dot.setPixmap(themed_icon("circle", status_color, 8).pixmap(QSize(8, 8)))
            dot.setFixedWidth(20)
            row.addWidget(dot)

            list_layout.addLayout(row)
        list_layout.addStretch()
        scroll.setWidget(list_widget)
        self.ui.main_layout.addWidget(scroll, 1)

        # Button row: 12px side/bottom margins, 4px above; Cancel left, then a
        # stretch pushing the action buttons to the right.
        btn_frame = QHBoxLayout()
        btn_frame.setContentsMargins(12, 4, 12, 12)

        cancel_btn = QPushButton(t("clear"))
        cancel_btn.clicked.connect(self.reject)
        btn_frame.addWidget(cancel_btn)
        btn_frame.addStretch()

        new_btn = QPushButton(t("new"))
        new_btn.clicked.connect(self._switch_to_fictitious)
        btn_frame.addWidget(new_btn)

        ok_btn = QPushButton(t("save"))
        ok_btn.setProperty("variant", "accent")
        ok_btn.clicked.connect(self._confirm_stock)
        btn_frame.addWidget(ok_btn)

        self.ui.main_layout.addLayout(btn_frame)

    def _build_fictitious_mode(self) -> None:
        # Same 50px BG_CARD header band as stock mode, titled "Add bar" (with a
        # "(new)" suffix when there is no material context yet).
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(f"background: {_th.BG_CARD};")
        h_layout = QHBoxLayout(header)
        title_text = t("add_bar")
        if not self._material:
            title_text += f" ({t('new')})"
        title = QLabel(title_text)
        title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        self.ui.main_layout.addWidget(header)

        # Manual-entry form, generously inset (20px all round) since it is a
        # short label/field stack rather than a dense list.
        form = QWidget()
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(20, 20, 20, 20)

        len_row = QHBoxLayout()
        len_row.addWidget(QLabel(t("bar_length", u=units.u_len())))
        self._e_length = QLineEdit(str(int(self._default_length)))
        len_row.addWidget(self._e_length)
        form_layout.addLayout(len_row)

        qty_row = QHBoxLayout()
        qty_row.addWidget(QLabel(t("stock_qty")))
        self._e_qty = QLineEdit("1")
        qty_row.addWidget(self._e_qty)
        form_layout.addLayout(qty_row)

        form_layout.addStretch()
        self.ui.main_layout.addWidget(form, 1)

        # Button row: 12px side/bottom margins, 4px above; Cancel left, then a
        # stretch pushing the action buttons to the right.
        btn_frame = QHBoxLayout()
        btn_frame.setContentsMargins(12, 4, 12, 12)

        cancel_btn = QPushButton(t("clear"))
        cancel_btn.clicked.connect(self.reject)
        btn_frame.addWidget(cancel_btn)
        btn_frame.addStretch()

        ok_btn = QPushButton(t("save"))
        ok_btn.setProperty("variant", "accent")
        ok_btn.clicked.connect(self._confirm_fictitious)
        btn_frame.addWidget(ok_btn)

        self.ui.main_layout.addLayout(btn_frame)

    def _switch_to_fictitious(self) -> None:
        self._clear_layout()
        self._available = []
        self._build_fictitious_mode()

    def _confirm_stock(self) -> None:
        selected = []
        for i, cb in enumerate(self._check_boxes):
            if cb.isChecked() and i < len(self._available):
                selected.append(self._available[i])

        if not selected:
            return

        if self._on_confirm:
            for bar in selected:
                self._on_confirm({"type": "stock", "length": bar.length, "bar": bar})
        self.accept()

    def _confirm_fictitious(self) -> None:
        try:
            length = float(self._e_length.text())
            qty = int(self._e_qty.text())
        except (ValueError, TypeError):
            return

        if length <= 0 or qty <= 0:
            return

        if self._on_confirm:
            for _ in range(qty):
                self._on_confirm({"type": "fictitious", "length": length, "bar": None})
        self.accept()
