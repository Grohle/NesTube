"""
nestube/ui_qt/dialogs/stock_add_dialog.py
Form dialog to add or edit a stock bar — scrollable, singleton, with profile dimensions.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QFrame, QGridLayout,
    QLabel, QLineEdit, QMessageBox, QTextEdit,
    QVBoxLayout, QWidget,
)

from nestube import app_config, units
from nestube.i18n import t
from nestube.materials_db import get_material_names
from nestube.stock_db import StockBar
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.forms.ui_stock_add_dialog import Ui_StockAddDialog


def _profile_options() -> List[str]:
    names: set = set()
    for cp in app_config.get().custom_profiles:
        if cp.name:
            names.add(cp.name)
    for key in ("profile_round", "profile_rect", "profile_l", "profile_u", "profile_h"):
        names.add(t(key))
    return sorted(names)


def _fields_for_profile(profile_name: str) -> List[tuple]:
    u = units.u_len()
    pn = profile_name.strip().lower()

    for cp in app_config.get().custom_profiles:
        if cp.name.lower() == pn:
            return [(f, f) for f in cp.fields]

    hsfx = t("dim_height_suffix")
    if pn == t("profile_round").lower():
        return [(t("dim_diameter", u=u) + hsfx, "dim_diameter")]
    if pn in (t("profile_rect").lower(), t("profile_l").lower(), t("profile_u").lower()):
        return [(t("dim_side_a", u=u) + hsfx, "dim_A"), (t("dim_side_b", u=u), "dim_B")]
    if pn == t("profile_h").lower():
        return [
            (t("dim_side_a", u=u) + hsfx, "dim_A"),
            (t("dim_side_b", u=u), "dim_B"),
            (t("dim_flange", u=u), "dim_flange"),
            (t("dim_web", u=u), "dim_web"),
        ]
    return []


class StockAddDialog(QDialog):
    """Singleton scrollable form to add or edit a stock bar."""

    _open_instance: Optional["StockAddDialog"] = None

    @classmethod
    def bring_to_front_if_open(cls) -> bool:
        if cls._open_instance is not None:
            try:
                if cls._open_instance.isVisible():
                    cls._open_instance.raise_()
                    cls._open_instance.activateWindow()
                    return True
            except RuntimeError:
                pass
            cls._open_instance = None
        return False

    def __init__(
        self,
        parent: QWidget,
        on_confirm: Optional[Callable[[dict], None]] = None,
        bar: Optional[StockBar] = None,
        currency: str = "EUR",
    ) -> None:
        super().__init__(parent)
        StockAddDialog._open_instance = self

        self.ui = Ui_StockAddDialog()
        self.ui.setupUi(self)

        self._on_confirm = on_confirm
        self._bar = bar
        self._currency = currency
        self._entries: Dict[str, QWidget] = {}
        self._field_entries: Dict[str, QLineEdit] = {}
        self._field_labels: Dict[str, str] = {}
        self._fields_container: Optional[QWidget] = None
        self._available_cb: Optional[QCheckBox] = None

        # ── i18n: override static text with t() ─────────────────────────
        title_text = t("edit_stock") if bar else t("add_to_stock")
        self.setWindowTitle(title_text)
        self.ui.title.setText(title_text)
        self.ui.title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")
        self.ui.hint.setText(t("stock_form_hint"))
        self.ui.hint.setStyleSheet(f"color: {_th.TEXT_SEC}; font-size: 11px;")
        self.ui.save_btn.setText(t("save"))
        self.ui.save_btn.setProperty("variant", "accent")
        self.ui.cancel_btn.setText(t("cancel"))

        # ── Build dynamic form cards into the scroll area ────────────────
        # Insert cards *before* the hint label that already lives in scroll_layout
        self._build_identity_card()
        self._build_dimensions_card()
        self._build_pricing_card()

        # ── Signal connections ───────────────────────────────────────────
        self.ui.save_btn.clicked.connect(self._confirm)
        self.ui.cancel_btn.clicked.connect(self.close)

        if bar:
            self._load_bar(bar)
        else:
            self._on_profile_change()

    def closeEvent(self, event) -> None:
        StockAddDialog._open_instance = None
        super().closeEvent(event)

    # ── Card helpers (dynamic — not in .ui) ──────────────────────────────

    def _insert_card(self, title: str) -> QFormLayout:
        """Create a styled card frame and insert it before the hint label.

        Card model used for the identity/dimensions/pricing sections: BG_CARD
        fill, 1px BORDER, 8px radius, 12×10 padding, an ACCENT bold title, then a
        QFormLayout body of label/field rows.
        """
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {_th.BG_CARD}; border: 1px solid {_th.BORDER};"
            f" border-radius: 8px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold; border: none;")
        card_layout.addWidget(lbl)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(form)

        # Insert before the hint label (which is followed by the spacer)
        idx = self.ui.scroll_layout.indexOf(self.ui.hint)
        self.ui.scroll_layout.insertWidget(idx, card)
        return form

    def _build_identity_card(self) -> None:
        form = self._insert_card(t("stock_profile"))

        options = _profile_options() or [""]
        self._profile_combo = QComboBox()
        self._profile_combo.setEditable(True)
        self._profile_combo.addItems(options)
        self._profile_combo.currentTextChanged.connect(self._on_profile_change)
        self._entries["profile"] = self._profile_combo
        form.addRow(t("stock_profile") + " *", self._profile_combo)

        materials = get_material_names()
        if materials:
            mat_combo = QComboBox()
            mat_combo.setEditable(True)
            mat_combo.addItems(materials)
            self._entries["material"] = mat_combo
            form.addRow(t("stock_material"), mat_combo)
        else:
            mat_entry = QLineEdit()
            self._entries["material"] = mat_entry
            form.addRow(t("stock_material"), mat_entry)

        quality_entry = QLineEdit()
        self._entries["quality"] = quality_entry
        form.addRow(t("placeholder_quality"), quality_entry)

    def _build_dimensions_card(self) -> None:
        form = self._insert_card(t("stock_dimensions_section"))

        length_entry = QLineEdit("6000")
        self._entries["length"] = length_entry
        form.addRow(t("stock_length", u=units.u_len()), length_entry)

        qty_entry = QLineEdit("1")
        self._entries["qty"] = qty_entry
        form.addRow(t("stock_qty"), qty_entry)

        self._available_cb = QCheckBox(t("stock_available"))
        self._available_cb.setChecked(True)
        self._available_cb.toggled.connect(self._on_available_toggle)
        form.addRow(self._available_cb)

        espesor_entry = QLineEdit()
        self._entries["espesor"] = espesor_entry
        form.addRow(t("wall_thickness", u=units.u_len()), espesor_entry)

        self._fields_container = QWidget()
        self._fields_container.setStyleSheet("border: none;")
        self._fields_grid = QGridLayout(self._fields_container)
        self._fields_grid.setContentsMargins(0, 0, 0, 0)
        form.addRow(self._fields_container)

    def _build_pricing_card(self) -> None:
        form = self._insert_card(t("stock_pricing_section"))
        sym = self._currency_symbol()

        for key, label_key, kwargs, default in [
            ("kg_por_m", "kg_per_meter", {"u_wpm": units.u_linear_weight()}, ""),
            ("precio_kg", "price_kg", {"sym": sym}, ""),
            ("precio_m", "price_m", {"sym": sym}, ""),
            ("precio_barra", "price_bar", {"sym": sym}, ""),
            ("peso_especifico", "specific_weight", {"u_density": units.u_density()}, "7.85"),
        ]:
            entry = QLineEdit(default)
            self._entries[key] = entry
            form.addRow(t(label_key, **kwargs), entry)

        # Wire auto-calc signals
        kg_entry = self._entries["kg_por_m"]
        pk_entry = self._entries["precio_kg"]
        pm_entry = self._entries["precio_m"]
        length_entry = self._entries.get("length")
        if isinstance(kg_entry, QLineEdit):
            kg_entry.editingFinished.connect(self._auto_calc_precio_kg)
            kg_entry.editingFinished.connect(self._auto_calc_precio_m)
        if isinstance(pk_entry, QLineEdit):
            pk_entry.editingFinished.connect(self._auto_calc_precio_m)
        if isinstance(pm_entry, QLineEdit):
            pm_entry.editingFinished.connect(self._auto_calc_precio_kg)
            pm_entry.editingFinished.connect(self._auto_calc_precio_barra)
        if isinstance(length_entry, QLineEdit):
            length_entry.editingFinished.connect(self._auto_calc_precio_barra)

        self._notes = QTextEdit()
        self._notes.setMaximumHeight(64)
        form.addRow(t("notes"), self._notes)

    # ── Behaviour methods (preserved exactly) ────────────────────────────

    def _on_available_toggle(self, checked: bool) -> None:
        qty_widget = self._entries.get("qty")
        if isinstance(qty_widget, QLineEdit):
            qty_widget.setEnabled(checked)

    def _currency_symbol(self) -> str:
        symbols = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CNY": "¥"}
        return symbols.get(self._currency, self._currency)

    def _widget_value(self, field_id: str) -> str:
        widget = self._entries.get(field_id)
        if widget is None:
            return ""
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return ""

    def _set_widget_value(self, field_id: str, value: str) -> None:
        widget = self._entries.get(field_id)
        if widget is None:
            return
        if isinstance(widget, QComboBox):
            idx = widget.findText(value)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            else:
                widget.setEditText(value)
        elif isinstance(widget, QLineEdit):
            widget.setText(value)

    def _on_profile_change(self, _value: str = "") -> None:
        profile = self._widget_value("profile")
        self._rebuild_custom_fields(_fields_for_profile(profile))
        self._prefill_from_profile_meta(profile)

    def _prefill_from_profile_meta(self, profile_name: str) -> None:
        """Pre-fill material/quality/specific_weight and dimension defaults from profile meta."""
        pn = profile_name.strip().lower()
        for cp in app_config.get().custom_profiles:
            if cp.name.lower() != pn:
                continue
            if cp.meta:
                mat = cp.meta.get("material", "")
                qual = cp.meta.get("quality", cp.quality)
                pe = cp.meta.get("specific_weight", "")
                if mat:
                    self._set_widget_value("material", mat)
                if qual and not self._widget_value("quality"):
                    self._set_widget_value("quality", qual)
                if pe:
                    self._set_widget_value("peso_especifico", str(pe))
            # Pre-fill custom dimension fields from field_defaults
            if cp.field_defaults:
                for key, entry in self._field_entries.items():
                    val = cp.field_defaults.get(key)
                    if val is not None and not entry.text().strip():
                        entry.setText(str(val))
            break

    def _float_entry(self, key: str) -> float:
        try:
            return float(self._widget_value(key))
        except (ValueError, TypeError):
            return 0.0

    def _auto_calc_precio_kg(self) -> None:
        kg = self._float_entry("kg_por_m")
        pm = self._float_entry("precio_m")
        if kg > 0 and pm > 0 and not self._float_entry("precio_kg"):
            self._set_widget_value("precio_kg", f"{pm / kg:.4f}")

    def _auto_calc_precio_m(self) -> None:
        kg = self._float_entry("kg_por_m")
        pk = self._float_entry("precio_kg")
        if kg > 0 and pk > 0 and not self._float_entry("precio_m"):
            self._set_widget_value("precio_m", f"{pk * kg:.4f}")
        self._auto_calc_precio_barra()

    def _auto_calc_precio_barra(self) -> None:
        pm = self._float_entry("precio_m")
        length_mm = self._float_entry("length")
        if pm > 0 and length_mm > 0 and not self._float_entry("precio_barra"):
            self._set_widget_value("precio_barra", f"{pm * length_mm / 1000:.4f}")

    def _rebuild_custom_fields(self, field_pairs: list) -> None:
        if self._fields_container is None:
            return

        while self._fields_grid.count():
            item = self._fields_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._field_entries.clear()
        self._field_labels.clear()

        if not field_pairs:
            return

        header = QLabel(t("dimensions_section"))
        header.setStyleSheet(f"color: {_th.TEXT_SEC}; font-size: 11px;")
        self._fields_grid.addWidget(header, 0, 0, 1, 2)

        for idx, (label, key) in enumerate(field_pairs, start=1):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {_th.TEXT_SEC};")
            self._fields_grid.addWidget(lbl, idx, 0)

            entry = QLineEdit()
            self._fields_grid.addWidget(entry, idx, 1)
            self._field_entries[key] = entry
            self._field_labels[key] = label

    def _load_bar(self, bar: StockBar) -> None:
        self._set_widget_value("profile", bar.profile_name)
        self._set_widget_value("material", bar.material_desc)
        self._set_widget_value("quality", bar.quality)
        self._set_widget_value("length", str(int(bar.length)) if bar.length else "")
        self._set_widget_value("qty", str(bar.quantity if bar.quantity > 0 else 1))
        if self._available_cb:
            self._available_cb.setChecked(bar.quantity > 0)
        self._on_available_toggle(bar.quantity > 0)
        self._set_widget_value("espesor", str(bar.espesor) if bar.espesor else "")
        self._set_widget_value("kg_por_m", str(bar.kg_por_m) if bar.kg_por_m else "")
        self._set_widget_value("precio_kg", str(bar.precio_kg) if bar.precio_kg else "")
        self._set_widget_value("precio_m", str(bar.precio_m) if bar.precio_m else "")
        self._set_widget_value("precio_barra", str(bar.precio_barra) if bar.precio_barra else "")
        self._set_widget_value("peso_especifico", str(bar.peso_especifico))
        if bar.notes:
            self._notes.setPlainText(bar.notes)

        field_pairs = _fields_for_profile(bar.profile_name)
        if not field_pairs:
            field_pairs = [(k, k) for k in bar.fields.keys()]
        self._rebuild_custom_fields(field_pairs)
        for key, entry in self._field_entries.items():
            value = bar.fields.get(key)
            if value is not None:
                entry.setText(str(value))

    def _confirm(self) -> None:
        profile = self._widget_value("profile")
        if not profile:
            QMessageBox.warning(self, t("warning"), t("stock_profile_required"))
            return

        length_raw = self._widget_value("length").strip()
        try:
            length_val = float(length_raw)
        except (ValueError, TypeError):
            length_val = 0.0
        if length_val <= 0:
            QMessageBox.warning(self, t("warning"), t("stock_length_required"))
            e = self._entries.get("length")
            if e:
                e.setFocus()
            return

        def _float(key: str, default: float = 0.0) -> float:
            try:
                return float(self._widget_value(key))
            except (ValueError, TypeError):
                return default

        try:
            qty = int(float(self._widget_value("qty") or "1"))
        except (ValueError, TypeError):
            qty = 1

        if self._available_cb and not self._available_cb.isChecked():
            qty = 0
        elif qty < 1:
            qty = 1

        custom_fields: Dict[str, float] = {}
        for key, entry in self._field_entries.items():
            raw = entry.text().strip()
            if not raw:
                continue
            try:
                custom_fields[key] = float(raw)
            except ValueError:
                label = self._field_labels.get(key, key)
                QMessageBox.warning(
                    self, t("data_error"),
                    f"{label}: {t('invalid_bar_length')}",
                )
                entry.setFocus()
                return

        material = self._widget_value("material") or profile
        result = {
            "profile_name": profile,
            "material_desc": material,
            "quality": self._widget_value("quality"),
            "length": _float("length", 6000),
            "qty": qty,
            "espesor": _float("espesor"),
            "kg_por_m": _float("kg_por_m"),
            "precio_kg": _float("precio_kg"),
            "precio_m": _float("precio_m"),
            "precio_barra": _float("precio_barra"),
            "peso_especifico": _float("peso_especifico", 7.85),
            "fields": custom_fields,
            "notes": self._notes.toPlainText().strip(),
        }

        if self._on_confirm:
            self._on_confirm(result)
        StockAddDialog._open_instance = None
        self.accept()
