"""
nestube/ui_qt/dialogs/profile_manager.py
Dialog to manage custom profiles: list on the left, inline property editor on the right.
"""
from __future__ import annotations

import os
import shutil
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget,
)

from nestube import app_config
from nestube.app_config import CustomProfileEntry
from nestube.i18n import t
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.icons import themed_icon
from nestube.naming import BASE_MATERIALS as _BUILTIN_MATERIALS, canonical_material, localize_material


def _is_number(v) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


class ProfileManager(QDialog):
    """Dialog for managing custom profiles with an inline property editor."""

    def __init__(
        self,
        parent: QWidget,
        on_change: Optional[Callable] = None,
        initial_select_id: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("manage_profiles"))
        self.resize(820, 560)
        self.setMinimumSize(640, 440)
        self.setModal(True)

        self._on_change = on_change
        self._selected_entry: Optional[CustomProfileEntry] = None
        self._field_rows: List[Tuple[QLineEdit, QLineEdit, QPushButton]] = []
        self._detail_scroll: Optional[QScrollArea] = None
        self._suppress_save = False

        self._build()
        self._refresh_list()

        if initial_select_id:
            entry = next(
                (e for e in app_config.get().custom_profiles if e.id == initial_select_id), None
            )
            if entry:
                self._select(entry)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel(t("manage_profiles"))
        title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")
        root.addWidget(title)

        body_splitter = QSplitter(Qt.Orientation.Horizontal)
        body_splitter.setChildrenCollapsible(False)

        # ── Left: profile list ────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(180)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("search_placeholder"))
        self._search.setFixedHeight(30)
        self._search.textChanged.connect(self._refresh_list)
        lv.addWidget(self._search)

        list_scroll = QScrollArea()
        list_scroll.setWidgetResizable(True)
        list_scroll.setStyleSheet(
            f"QScrollArea {{ background: {_th.BG_CARD}; border: 1px solid {_th.BORDER}; "
            f"border-radius: 6px; }}"
        )
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(3)
        list_scroll.setWidget(self._list_widget)
        lv.addWidget(list_scroll, 1)

        del_btn = QPushButton(t("remove"))
        del_btn.setProperty("variant", "danger")
        del_btn.clicked.connect(self._delete_selected)
        lv.addWidget(del_btn)

        body_splitter.addWidget(left)

        # ── Right: detail editor ─────────────────────────────────────────
        self._detail_scroll = QScrollArea()
        self._detail_scroll.setWidgetResizable(True)
        self._detail_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._detail_container = QWidget()
        self._detail_vbox = QVBoxLayout(self._detail_container)
        self._detail_vbox.setContentsMargins(0, 0, 6, 0)
        self._detail_vbox.setSpacing(8)
        self._no_sel_lbl = QLabel(t("select_profile_msg"))
        self._no_sel_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_sel_lbl.setStyleSheet(f"color: {_th.TEXT_SEC};")
        self._detail_vbox.addWidget(self._no_sel_lbl)
        self._detail_vbox.addStretch()
        self._detail_scroll.setWidget(self._detail_container)
        body_splitter.addWidget(self._detail_scroll)

        body_splitter.setSizes([240, 560])
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)

        root.addWidget(body_splitter, 1)

    def _card(self, title: str) -> Tuple[QFrame, QFormLayout]:
        """Create a styled card frame with a title and return (card, form_layout)."""
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {_th.BG_CARD}; border: 1px solid {_th.BORDER}; "
            f"border-radius: 8px; }}"
        )
        cv = QVBoxLayout(card)
        cv.setContentsMargins(12, 10, 12, 10)
        cv.setSpacing(6)
        hdr = QLabel(title)
        hdr.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold; border: none;")
        cv.addWidget(hdr)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)
        cv.addLayout(form)
        return card, form

    # ── Profile list ─────────────────────────────────────────────────────────

    def _refresh_list(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Force full repaint to clear ghost text left by the previous render pass.
        self._list_widget.update()

        prefs = app_config.get()
        query = getattr(self, "_search", None)
        query = query.text().strip().lower() if query else ""

        visible = [
            e for e in prefs.custom_profiles
            if not query or query in e.name.lower()
        ]
        if not visible:
            lbl = QLabel(t("no_custom_profiles"))
            lbl.setStyleSheet(f"color: {_th.TEXT_SEC};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(lbl)
            self._list_layout.addStretch()
            return

        for entry in visible:
            is_sel = self._selected_entry and self._selected_entry.id == entry.id
            border_color = _th.ACCENT if is_sel else _th.BORDER
            bg = _th.BG_MID if is_sel else "transparent"

            tile = QPushButton()
            fields_txt = ", ".join(entry.fields[:3])
            if len(entry.fields) > 3:
                fields_txt += "…"
            tile.setText(f"  {entry.name}   {fields_txt}")
            icon = self._entry_icon(entry)
            if icon is not None:
                tile.setIcon(icon)
                tile.setIconSize(QSize(28, 28))
            tile.setFixedHeight(40)
            tile.setStyleSheet(
                f"QPushButton {{ text-align: left; padding-left: 8px; background: {bg}; "
                f"color: {_th.TEXT_PRI}; border: 1px solid {border_color}; border-radius: 6px; }}"
                f"QPushButton:hover {{ background: {_th.BG_MID}; }}"
            )
            tile.clicked.connect(lambda checked=False, en=entry: self._select(en))
            self._list_layout.addWidget(tile)
        self._list_layout.addStretch()

    def _entry_icon(self, entry: CustomProfileEntry):
        """Real thumbnail for a list row: the saved PNG (entry.image) if present,
        else a section rendered from meta. Returns a QIcon or None.

        The previous code tinted a generic "image" glyph for every row, which
        in light mode showed as a black square and never reflected the actual
        profile shape."""
        from PySide6.QtGui import QIcon, QPixmap
        if entry.image:
            from nestube.app_config import PROFILES_DIR
            path = os.path.join(PROFILES_DIR, entry.image)
            if os.path.isfile(path):
                px = QPixmap(path)
                if not px.isNull():
                    return QIcon(px)
        # Fallback: render the parametric section from meta.
        meta = entry.meta or {}
        geom = meta.get("geometry_type")
        if geom:
            try:
                from nestube.profile_geometry import render_section_pixmap
                px = render_section_pixmap(
                    geom,
                    float(meta.get("h", 0) or 0), float(meta.get("b", 0) or 0),
                    float(meta.get("tw", 0) or 0), float(meta.get("tf", 0) or 0),
                    macizo=bool(meta.get("macizo", False)), size=64,
                )
                if not px.isNull():
                    return QIcon(px)
            except Exception:
                pass
        return None

    @staticmethod
    def _field_value(entry: CustomProfileEntry, field_name: str) -> str:
        """Resolve a field's display value, reconciling field_defaults with the
        canonical meta values (h/b/tw/tf/…). field_defaults is keyed by the full
        label ("h (mm)"); meta is keyed by the bare token ("h"). ProfileCreator
        profiles often have an empty field_defaults but a populated meta."""
        val = entry.field_defaults.get(field_name, "")
        if val != "" and val is not None:
            return f"{float(val):g}" if _is_number(val) else str(val)
        # Derive the bare token from the label, e.g. "h (mm)" → "h".
        token = field_name.split("(")[0].strip().lower()
        meta_val = (entry.meta or {}).get(token)
        if meta_val not in (None, "", 0):
            return f"{float(meta_val):g}" if _is_number(meta_val) else str(meta_val)
        return ""

    def _select(self, entry: CustomProfileEntry) -> None:
        self._selected_entry = entry
        self._refresh_list()
        self._populate_detail(entry)

    # ── Detail panel ─────────────────────────────────────────────────────────

    def _clear_detail(self) -> None:
        while self._detail_vbox.count():
            item = self._detail_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._field_rows.clear()

    def _populate_detail(self, entry: CustomProfileEntry) -> None:
        self._suppress_save = True
        self._clear_detail()

        # ── Identity card ───────────────────────────────────────────────
        id_card, id_form = self._card(entry.name)

        self._e_name = QLineEdit(entry.name)
        self._e_name.editingFinished.connect(self._save_identity)
        id_form.addRow(t("field_name") + " *", self._e_name)

        self._combo_mat = QComboBox()
        self._combo_mat.setEditable(True)
        self._combo_mat.addItem("", 0.0)
        seen: set = set()
        # Built-in materials: localised label, canonical storage.
        for mat_name, sw in _BUILTIN_MATERIALS:
            self._combo_mat.addItem(localize_material(mat_name), sw)
            seen.add(mat_name.lower())
        from nestube.materials_db import get_materials
        for mat in get_materials().materials:
            if mat.name.lower() not in seen:
                self._combo_mat.addItem(mat.name, mat.specific_weight)
                seen.add(mat.name.lower())
        initial_mat = entry.meta.get("material", "")
        idx = self._combo_mat.findText(localize_material(initial_mat))
        self._combo_mat.setCurrentIndex(idx if idx >= 0 else 0)
        self._combo_mat.currentIndexChanged.connect(self._on_mat_changed)
        id_form.addRow(t("stock_material"), self._combo_mat)

        self._lbl_sw = QLabel("—")
        self._lbl_sw.setStyleSheet(f"color: {_th.TEXT_SEC}; border: none;")
        id_form.addRow(t("specific_weight", u_density="t/m³"), self._lbl_sw)

        self._e_quality = QLineEdit(entry.quality)
        self._e_quality.editingFinished.connect(self._save_identity)
        id_form.addRow(t("placeholder_quality"), self._e_quality)

        self._detail_vbox.addWidget(id_card)
        self._on_mat_changed()

        # ── Dimensions card ─────────────────────────────────────────────
        dim_card = QFrame()
        dim_card.setStyleSheet(
            f"QFrame {{ background: {_th.BG_CARD}; border: 1px solid {_th.BORDER}; "
            f"border-radius: 8px; }}"
        )
        dv = QVBoxLayout(dim_card)
        dv.setContentsMargins(12, 10, 12, 10)
        dv.setSpacing(6)

        dim_hdr = QLabel(t("dimensions_section"))
        dim_hdr.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold; border: none;")
        dv.addWidget(dim_hdr)

        col_hdr = QHBoxLayout()
        col_hdr.setContentsMargins(0, 0, 0, 0)
        lbl_a = QLabel(t("field_name"))
        lbl_a.setStyleSheet(f"color: {_th.TEXT_SEC}; border: none; font-size: 11px;")
        lbl_b = QLabel(t("default_value"))
        lbl_b.setStyleSheet(f"color: {_th.TEXT_SEC}; border: none; font-size: 11px;")
        col_hdr.addWidget(lbl_a, 1)
        col_hdr.addWidget(lbl_b, 1)
        col_hdr.addSpacing(34)
        dv.addLayout(col_hdr)

        self._fields_grid = QWidget()
        self._fields_grid.setStyleSheet("border: none;")
        self._grid_layout = QGridLayout(self._fields_grid)
        self._grid_layout.setContentsMargins(0, 0, 0, 6)
        self._grid_layout.setSpacing(6)
        self._grid_layout.setColumnStretch(0, 1)
        self._grid_layout.setColumnStretch(1, 1)
        dv.addWidget(self._fields_grid)

        for field_name in entry.fields:
            self._add_field_row(field_name, self._field_value(entry, field_name))

        dv.addSpacing(4)
        add_btn = QPushButton("+ " + t("profile_edit_fields"))
        add_btn.setFixedHeight(30)
        add_btn.clicked.connect(lambda: self._add_field_row("", ""))
        dv.addWidget(add_btn)

        self._detail_vbox.addWidget(dim_card)

        # ── Image & actions card ────────────────────────────────────────
        act_card = QFrame()
        act_card.setStyleSheet(
            f"QFrame {{ background: {_th.BG_CARD}; border: 1px solid {_th.BORDER}; "
            f"border-radius: 8px; }}"
        )
        av = QVBoxLayout(act_card)
        av.setContentsMargins(12, 10, 12, 10)
        av.setSpacing(6)

        act_hdr = QLabel(t("profile_creator_tools"))
        act_hdr.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold; border: none;")
        av.addWidget(act_hdr)

        if entry.image:
            from nestube.app_config import PROFILES_DIR
            img_path = os.path.join(PROFILES_DIR, entry.image)
            if os.path.isfile(img_path):
                from PySide6.QtGui import QPixmap
                px = QPixmap(img_path).scaled(
                    80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                thumb = QLabel()
                thumb.setPixmap(px)
                thumb.setStyleSheet("border: none;")
                av.addWidget(thumb)

        btn_row = QHBoxLayout()
        draw_btn = QPushButton(t("profile_creator_tools"))
        draw_btn.setIcon(themed_icon("pencil", _th.TEXT_PRI, 14))
        draw_btn.setIconSize(QSize(14, 14))
        draw_btn.clicked.connect(self._edit_drawing)
        btn_row.addWidget(draw_btn)

        img_btn = QPushButton(t("profile_assign_image"))
        img_btn.clicked.connect(self._assign_image)
        btn_row.addWidget(img_btn)
        av.addLayout(btn_row)

        self._detail_vbox.addWidget(act_card)
        self._detail_vbox.addStretch()
        self._suppress_save = False

    # ── Dimension field rows ──────────────────────────────────────────────────

    def _add_field_row(self, name: str, default: str) -> None:
        row_idx = self._grid_layout.rowCount()

        e_name = QLineEdit(name)
        e_name.setPlaceholderText(t("field_name"))
        e_name.setFixedHeight(30)
        e_name.setStyleSheet("border: 1px solid " + _th.BORDER + "; border-radius: 4px;")

        e_val = QLineEdit(default)
        e_val.setPlaceholderText("0")
        e_val.setFixedHeight(30)
        e_val.setStyleSheet("border: 1px solid " + _th.BORDER + "; border-radius: 4px;")

        del_btn = QPushButton()
        del_btn.setFixedSize(30, 30)
        del_btn.setIcon(themed_icon("x", _th.TEXT_SEC, 12))
        del_btn.setIconSize(QSize(12, 12))
        del_btn.setToolTip(t("remove"))
        del_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; }}"
            f"QPushButton:hover {{ background: {_th.DANGER_BG}; border-radius: 4px; }}"
        )

        self._grid_layout.addWidget(e_name, row_idx, 0)
        self._grid_layout.addWidget(e_val, row_idx, 1)
        self._grid_layout.addWidget(del_btn, row_idx, 2)

        triple = (e_name, e_val, del_btn)
        self._field_rows.append(triple)

        e_name.editingFinished.connect(self._save_fields)
        e_val.editingFinished.connect(self._save_fields)
        del_btn.clicked.connect(lambda checked=False, t=triple: self._remove_field_row(t))

    def _remove_field_row(self, triple: Tuple[QLineEdit, QLineEdit, QPushButton]) -> None:
        e_name, e_val, del_btn = triple
        for w in (e_name, e_val, del_btn):
            self._grid_layout.removeWidget(w)
            w.deleteLater()
        if triple in self._field_rows:
            self._field_rows.remove(triple)
        self._save_fields()

    def _read_field_rows(self):
        """Return (fields_list, field_defaults_dict) from current row widgets."""
        fields = []
        defaults = {}
        for e_name, e_val, _ in self._field_rows:
            name = e_name.text().strip()
            if not name:
                continue
            fields.append(name)
            try:
                val = float(e_val.text())
                defaults[name] = val
            except (ValueError, TypeError):
                pass
        return fields, defaults

    # ── Save helpers ──────────────────────────────────────────────────────────

    def _on_mat_changed(self) -> None:
        sw = self._combo_mat.currentData()
        self._lbl_sw.setText(f"{float(sw):.2f} t/m³" if sw else "—")
        if not self._suppress_save:
            self._save_identity()

    def _save_identity(self) -> None:
        if self._suppress_save or not self._selected_entry:
            return
        entry = self._selected_entry
        new_name = self._e_name.text().strip()
        if new_name:
            entry.name = new_name
        entry.quality = self._e_quality.text().strip()
        mat = canonical_material(self._combo_mat.currentText().strip())
        sw = self._combo_mat.currentData()
        if mat:
            entry.meta["material"] = mat
            entry.meta["specific_weight"] = float(sw) if sw else 7.85
        self._persist()

    def _save_fields(self) -> None:
        if self._suppress_save or not self._selected_entry:
            return
        fields, defaults = self._read_field_rows()
        self._selected_entry.fields = fields
        self._selected_entry.field_defaults = defaults
        self._persist()
        self._refresh_list()

    def _persist(self) -> None:
        if not self._selected_entry:
            return
        app_config.save_profile_file(self._selected_entry)
        app_config.save()
        self._notify_change()

    # ── Actions ───────────────────────────────────────────────────────────────

    _ALLOWED_IMG_EXTS = frozenset({".png", ".jpg", ".jpeg"})
    _MAX_IMAGE_BYTES = 20 * 1024 * 1024

    def _assign_image(self) -> None:
        if not self._selected_entry:
            QMessageBox.warning(self, t("warning"), t("select_profile_msg"))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, t("profile_png_title"), "", "PNG (*.png);;JPEG (*.jpg *.jpeg)",
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in self._ALLOWED_IMG_EXTS or os.path.getsize(path) > self._MAX_IMAGE_BYTES:
            QMessageBox.warning(self, t("warning"), t("profile_invalid_image_ext"))
            return
        os.makedirs(app_config.PROFILES_DIR, exist_ok=True)
        safe = (
            "".join(c if c.isalnum() or c in "_-" else "_" for c in self._selected_entry.name).strip()
            or "profile"
        )
        profiles_real = os.path.realpath(app_config.PROFILES_DIR)
        dest = os.path.join(profiles_real, f"{safe}{ext}")
        if not os.path.realpath(dest).startswith(profiles_real + os.sep):
            return
        shutil.copy2(path, dest)
        self._selected_entry.image = f"{safe}{ext}"
        self._persist()
        # Refresh detail to show new thumbnail
        self._populate_detail(self._selected_entry)
        self._refresh_list()

    def _edit_drawing(self) -> None:
        if not self._selected_entry:
            QMessageBox.warning(self, t("warning"), t("select_profile_msg"))
            return
        from nestube.ui_qt.dialogs.profile_creator import ProfileCreator
        from nestube.ui_qt.dialogs.profile_save_dialog import ProfileSaveDialog

        entry = self._selected_entry

        def on_save(data):
            thumbnail_path = data.get("thumbnail_path", "")
            fields = data.get("fields", entry.fields)
            field_defaults = data.get("field_defaults", {})
            drawing_shapes = data.get("shapes", [])
            wkt_str = data.get("wkt", "")
            meta = dict(data.get("meta", {}))
            manual_sides = list(data.get("manual_sides", []))

            def on_confirm(result):
                entry.name = result["name"]
                entry.quality = result.get("quality", "")
                entry.notes = result.get("notes", "")
                entry.fields = result.get("fields", fields)
                # Reconcile field_defaults with the canonical values so the
                # value column is populated (§21.4/§21.5).
                merged_defaults = dict(entry.field_defaults)
                merged_defaults.update(field_defaults)
                entry.field_defaults = merged_defaults
                entry.drawing_shapes = drawing_shapes
                entry.meta = meta
                entry.manual_sides = manual_sides
                if wkt_str:
                    entry.wkt = wkt_str
                if result.get("material"):
                    entry.meta["material"] = result["material"]
                    entry.meta["specific_weight"] = result.get("specific_weight", 7.85)
                if thumbnail_path and os.path.isfile(thumbnail_path):
                    os.makedirs(app_config.PROFILES_DIR, exist_ok=True)
                    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in entry.name)
                    image_name = f"{safe}.png"
                    dest = os.path.join(app_config.PROFILES_DIR, image_name)
                    shutil.copy2(thumbnail_path, dest)
                    try:
                        os.remove(thumbnail_path)
                    except OSError:
                        pass
                    entry.image = image_name
                app_config.save_profile_file(entry)
                self._store_wkt_to_db(entry, wkt_str)
                app_config.save()
                self._refresh_list()
                self._populate_detail(entry)
                self._notify_change()

            ProfileSaveDialog(
                self, fields=fields, on_confirm=on_confirm,
                initial_name=entry.name, initial_quality=entry.quality,
                initial_notes=entry.notes,
                initial_material=entry.meta.get("material", ""),
            ).exec()

        ProfileCreator(
            self, on_save=on_save, initial_shapes=entry.drawing_shapes,
            initial_meta=getattr(entry, "meta", {}),
            initial_manual_sides=getattr(entry, "manual_sides", []),
        ).exec()

    def _delete_selected(self) -> None:
        if not self._selected_entry:
            QMessageBox.warning(self, t("warning"), t("select_profile_msg"))
            return
        reply = QMessageBox.question(
            self, t("remove"),
            t("profile_delete_confirm", name=self._selected_entry.name),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        app_config.delete_profile_file(self._selected_entry)
        prefs = app_config.get()
        prefs.custom_profiles = [p for p in prefs.custom_profiles if p.id != self._selected_entry.id]
        app_config.save()
        self._selected_entry = None
        self._clear_detail()
        self._no_sel_lbl = QLabel(t("select_profile_msg"))
        self._no_sel_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_sel_lbl.setStyleSheet(f"color: {_th.TEXT_SEC};")
        self._detail_vbox.addWidget(self._no_sel_lbl)
        self._detail_vbox.addStretch()
        self._refresh_list()
        self._notify_change()

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _store_wkt_to_db(self, entry, wkt_str: str) -> None:
        if not wkt_str:
            return
        try:
            from nestube.database import get_geometry_db
            from shapely import wkt as shapely_wkt
            db = get_geometry_db()
            polygon = shapely_wkt.loads(wkt_str)
            db.store_geometry(polygon)
        except Exception:
            pass

    def _notify_change(self) -> None:
        if self._on_change:
            self._on_change()
