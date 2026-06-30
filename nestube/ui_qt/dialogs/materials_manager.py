"""
nestube/ui_qt/dialogs/materials_manager.py
Full material manager: a master/detail window with a left sidebar (search +
material list + New/Delete) and a right detail editor (name, quality, specific
weight). Mirrors the ProfileManager layout so material management feels like a
complete menu rather than a small add form.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from nestube.i18n import t
from nestube.materials_db import (
    Material, add_material, find_duplicate,
    get_materials, remove_material, search_materials, update_material,
)
import nestube.ui_qt.theme_qt as _th


class MaterialsManagerDialog(QDialog):
    """CRUD dialog for the materials database (left list + right editor)."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._selected: Optional[Material] = None
        self.setWindowTitle(t("manage_materials"))
        self.resize(820, 560)
        self.setMinimumSize(640, 440)
        self._build()
        self._refresh_list()
        self._update_detail()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel(t("manage_materials"))
        title.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold; font-size:14px;")
        root.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left: search + list + actions ────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(220)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("search_placeholder"))
        self._search.setFixedHeight(30)
        self._search.textChanged.connect(lambda _=None: self._refresh_list())
        lv.addWidget(self._search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background:{_th.BG_CARD}; border:1px solid {_th.BORDER};"
            f" border-radius:6px; }}")
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(6, 6, 6, 6)
        self._list_layout.setSpacing(4)
        scroll.setWidget(self._list_widget)
        lv.addWidget(scroll, 1)

        new_btn = QPushButton("＋ " + t("new"))
        new_btn.setFixedHeight(30)
        new_btn.setProperty("variant", "accent")
        new_btn.clicked.connect(self._new_material)
        lv.addWidget(new_btn)

        self._del_btn = QPushButton(t("remove"))
        self._del_btn.setFixedHeight(30)
        self._del_btn.setProperty("variant", "danger")
        self._del_btn.clicked.connect(self._delete_selected)
        lv.addWidget(self._del_btn)

        splitter.addWidget(left)

        # ── Right: detail editor ─────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(8)

        self._detail_card = QFrame()
        self._detail_card.setStyleSheet(
            f"QFrame {{ background:{_th.BG_CARD}; border:1px solid {_th.BORDER};"
            f" border-radius:8px; }}")
        grid = QGridLayout(self._detail_card)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        def _lbl(text):
            l = QLabel(text)
            l.setStyleSheet(f"color:{_th.TEXT_SEC}; border:none;")
            return l

        self._e_name = QLineEdit()
        self._e_name.setPlaceholderText(t("material_name"))
        self._e_name.setFixedHeight(30)
        self._e_quality = QLineEdit()
        self._e_quality.setPlaceholderText(t("material_quality"))
        self._e_quality.setFixedHeight(30)
        self._e_sw = QLineEdit()
        self._e_sw.setPlaceholderText("7.85")
        self._e_sw.setFixedHeight(30)
        grid.addWidget(_lbl(t("material_name") + " *"), 0, 0)
        grid.addWidget(self._e_name, 0, 1)
        grid.addWidget(_lbl(t("material_quality")), 1, 0)
        grid.addWidget(self._e_quality, 1, 1)
        grid.addWidget(_lbl(t("specific_weight", u_density="t/m³")), 2, 0)
        grid.addWidget(self._e_sw, 2, 1)
        grid.setColumnStretch(1, 1)
        rv.addWidget(self._detail_card)

        self._hint = QLabel(t("material_form_hint"))
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:11px;")
        rv.addWidget(self._hint)
        rv.addStretch(1)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self._save_btn = QPushButton(t("save"))
        self._save_btn.setFixedHeight(30)
        self._save_btn.setProperty("variant", "accent")
        self._save_btn.clicked.connect(self._save)
        save_row.addWidget(self._save_btn)
        rv.addLayout(save_row)

        splitter.addWidget(right)
        splitter.setSizes([260, 540])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self._e_name.returnPressed.connect(self._save)

    # ── List ──────────────────────────────────────────────────────────────
    def _refresh_list(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self._search.text().strip()
        materials = search_materials(query) if query else get_materials().materials
        if not materials:
            lbl = QLabel(t("no_materials"))
            lbl.setStyleSheet(f"color:{_th.TEXT_SEC};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(lbl)
            self._list_layout.addStretch()
            return

        for mat in materials:
            is_sel = self._selected is not None and self._selected.id == mat.id
            sw_str = f"{mat.specific_weight:.2f} t/m³"
            tile = QPushButton(f"{mat.name}   ·   {mat.quality or '—'}   ·   {sw_str}")
            tile.setFixedHeight(34)
            border = _th.ACCENT if is_sel else _th.BORDER
            bg = _th.BG_MID if is_sel else "transparent"
            tile.setStyleSheet(
                f"QPushButton {{ text-align:left; padding-left:8px; background:{bg};"
                f" color:{_th.TEXT_PRI}; border:1px solid {border}; border-radius:4px; }}"
                f"QPushButton:hover {{ background:{_th.BG_MID}; }}")
            tile.clicked.connect(lambda checked=False, m=mat: self._select(m))
            self._list_layout.addWidget(tile)
        self._list_layout.addStretch()

    # ── Actions ─────────────────────────────────────────────────────────────
    def _select(self, mat: Material) -> None:
        self._selected = mat
        self._e_name.setText(mat.name)
        self._e_quality.setText(mat.quality)
        self._e_sw.setText(str(mat.specific_weight))
        self._refresh_list()
        self._update_detail()

    def _new_material(self) -> None:
        self._selected = None
        self._e_name.clear()
        self._e_quality.clear()
        self._e_sw.clear()
        self._refresh_list()
        self._update_detail()
        self._e_name.setFocus()

    def _update_detail(self) -> None:
        editing = self._selected is not None
        self._del_btn.setEnabled(editing)
        self._save_btn.setText(t("save"))

    def _read_form(self):
        name = self._e_name.text().strip()
        if not name:
            QMessageBox.warning(self, t("warning"), t("material_name_required"))
            self._e_name.setFocus()
            return None
        quality = self._e_quality.text().strip()
        sw_text = self._e_sw.text().strip()
        try:
            specific_weight = float(sw_text) if sw_text else 7.85
        except ValueError:
            specific_weight = 7.85
        return name, quality, specific_weight

    def _save(self) -> None:
        data = self._read_form()
        if data is None:
            return
        name, quality, specific_weight = data
        exclude_id = self._selected.id if self._selected else ""
        if find_duplicate(name, quality, exclude_id=exclude_id):
            QMessageBox.warning(self, t("warning"), t("material_duplicate"))
            return
        if self._selected:
            update_material(self._selected.id, name, quality,
                            specific_weight=specific_weight)
        else:
            add_material(name, quality, specific_weight=specific_weight)
        self._new_material()
        QMessageBox.information(self, t("materials"), t("material_saved"))

    def _delete_selected(self) -> None:
        if not self._selected:
            QMessageBox.warning(self, t("warning"), t("select_material_msg"))
            return
        reply = QMessageBox.question(
            self, t("remove"),
            t("material_delete_confirm", name=self._selected.display),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        remove_material(self._selected.id)
        self._new_material()
