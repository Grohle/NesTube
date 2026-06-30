"""
nestube/ui_qt/tab_perfiles.py
Profile / cost tab — vector profile selector, dimensions, results.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from nestube import app_config, units
from nestube.app_config import CustomProfileEntry
from nestube.models import (
    AppState, TipoPerfil, ConfigPerfil, MaterialContext,
    PerfilDimensiones, ParametrosMaterial, ParametrosManoObra,
)
from nestube.logic import calcular_resultado
from nestube.context_sync import (
    ensure_material_contexts, save_state_to_context, load_context_to_state,
    recompute_auto_barras, set_material_selection, layout_covers_all_cuts,
    layout_to_barras,
)
from nestube.i18n import t
from nestube.naming import localize_material
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.icons import themed_icon
from nestube.ui_qt.forms.ui_tab_perfiles import Ui_TabPerfiles
from nestube.ui_qt.widgets.material_subtabs import MaterialSubTabs
from nestube.ui_qt.widgets.profile_tile import ProfileTile
from nestube.ui_qt.widgets.stock_material_search_bar import StockMaterialSearchBar


CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CNY", "CAD", "AUD", "CHF", "SEK", "NOK"]
CURRENCY_SYMBOLS = {
    "EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CNY": "¥",
    "CAD": "CA$", "AUD": "A$", "CHF": "CHF", "SEK": "kr", "NOK": "kr",
}


def currency_display(code: str) -> str:
    return f"{CURRENCY_SYMBOLS.get(code, code)} | {code}"


def _currency_code(display: str) -> str:
    return display.split(" | ", 1)[1] if " | " in display else display


def _builtin_profiles() -> List[Tuple[str, TipoPerfil, str]]:
    return [
        ("builtin:redondo",     TipoPerfil.REDONDO,     t("profile_round")),
        ("builtin:rectangular", TipoPerfil.RECTANGULAR, t("profile_rect")),
        ("builtin:L",           TipoPerfil.L,           t("profile_l")),
        ("builtin:U",           TipoPerfil.U,           t("profile_u")),
        ("builtin:H",           TipoPerfil.H,           t("profile_h")),
    ]


# Catalogue geometry_type → builtin TipoPerfil, used so a catalogue profile
# still produces a valid ConfigPerfil for the cost calculation. Weight comes
# from meta["peso_lineal_kg_m"] (kg_por_m), so the exact tipo only refines the
# area/perimeter (unused while precio_m2 == 0); unknown types fall back to
# RECTANGULAR.
_GEOMETRY_TO_TIPO = {
    "redondo": TipoPerfil.REDONDO,
    "cuadrado": TipoPerfil.RECTANGULAR,
    "pletina": TipoPerfil.RECTANGULAR,
    "ranurado": TipoPerfil.RECTANGULAR,
    "angular": TipoPerfil.L,
    "viga u": TipoPerfil.U,
    "perfil c": TipoPerfil.U,
    "viga i": TipoPerfil.H,
    "viga h": TipoPerfil.H,
    "perfil z": TipoPerfil.RECTANGULAR,
}


def _tipo_for_geometry(geometry_type: str) -> TipoPerfil:
    return _GEOMETRY_TO_TIPO.get((geometry_type or "").strip().lower(),
                                 TipoPerfil.RECTANGULAR)


def _infer_geometry_from_name(name: str) -> str:
    """Best-effort geometry_type from a profile's designation.

    Used when a catalogue entry's meta lacks ``geometry_type`` (e.g. saved by
    an older build, or a partial duplicate), so its thumbnail shows the real
    cross-section instead of falling back to a rectangle. Returns a key that
    ``_GEOMETRY_TO_TIPO`` understands, or "" when nothing matches.
    """
    n = (name or "").strip().lower()
    if not n:
        return ""
    if n.startswith(("ipe", "ipn")):
        return "viga i"
    if n.startswith(("hea", "heb", "hem", "he ")):
        return "viga h"
    if n.startswith(("upn", "upe", "uap")) or n.startswith("u "):
        return "viga u"
    if "correa c" in n or n.startswith("c "):
        return "perfil c"
    if "correa z" in n or n.startswith("z "):
        return "perfil z"
    if n.startswith("l ") or "angular" in n:
        return "angular"
    if "ø" in n or n.startswith(("tr ", "tubo r", "redondo")):
        return "redondo"
    if n.startswith("tc ") or "cuadrad" in n:
        return "cuadrado"
    if "pletina" in n:
        return "pletina"
    if "ranurado" in n:
        return "ranurado"
    return ""


def _tipo_for_entry(entry) -> TipoPerfil:
    """TipoPerfil for a catalogue/custom entry, resilient to missing meta.

    Prefers the stored ``geometry_type``; if absent, infers it from the
    profile name so a stale entry never forces a rectangular thumbnail.
    """
    meta = getattr(entry, "meta", None) or {}
    geo = (meta.get("geometry_type") or "").strip()
    if not geo:
        geo = _infer_geometry_from_name(getattr(entry, "name", ""))
    return _tipo_for_geometry(geo)


def _tipo_dims(tipo: TipoPerfil) -> list[tuple[str, str]]:
    u = units.u_len()
    mapping = {
        TipoPerfil.REDONDO:     [(f"h ({u})", "diametro")],
        TipoPerfil.RECTANGULAR: [(f"h ({u})", "lado_a"), (f"b ({u})", "lado_b")],
        TipoPerfil.L:           [(f"h ({u})", "lado_a"), (f"b ({u})", "lado_b")],
        TipoPerfil.U:           [(f"h ({u})", "lado_a"), (f"b ({u})", "lado_b"),
                                  (f"tf ({u})", "lado_c")],
        TipoPerfil.H:           [(f"b ({u})", "lado_a"), (f"h ({u})", "lado_b"),
                                  (f"tf ({u})", "lado_c"), (f"tw ({u})", "espesor_int_H")],
    }
    return mapping.get(tipo, [])


# ── Result card ───────────────────────────────────────────────────────────────

class _ResultCard(QFrame):
    """Single result card for one cut."""

    def __init__(self, res, currency: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")   # themed card surface (BG_CARD + border)
        self.style().polish(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)   # 8px gap below each card
        layout.setSpacing(0)

        # Accent top stripe: a 3px ACCENT bar across the card top (visual anchor).
        stripe = QFrame()
        stripe.setFixedHeight(3)
        stripe.setStyleSheet(f"background:{_th.ACCENT}; border:none;")
        layout.addWidget(stripe)

        # Header line "<desc> · <largo> mm × <qty> u": 11px bold, padded.
        hdr = QLabel(
            f"{res.descripcion}  ·  {res.largo:.0f} mm  ×  {res.cantidad} {t('units_abbr')}"
        )
        hdr.setStyleSheet(f"color:{_th.TEXT_PRI}; font-weight:bold; font-size:11px; padding:8px 12px 4px 12px;")
        layout.addWidget(hdr)

        # Value rows: 2-column grid, label (10px secondary, left) + value (10px
        # mono, right-aligned). Column 0 stretches so values align on the right.
        rows = [
            (t("weight_per_unit"),    f"{res.kg_ud:.4f} kg"),
            (t("area_per_unit"),      f"{res.m2_ud:.6f} m²"),
            (t("material_price_unit"), f"{res.precio_material_ud:.2f} {currency}"),
            (t("labour_unit"),        f"{res.coste_mano_obra_ud:.2f} {currency}"),
            (t("total_price_unit"),   f"{res.precio_total_ud:.2f} {currency}"),
            (t("price_per_m", sym=currency), f"{res.precio_m:.2f} {currency}/m"),
            (t("line_total"),         f"{res.precio_total_linea:.2f} {currency}"),
        ]
        # Detail grid (label/value rows): 12px side padding aligned with the
        # header, no top gap (sits under the header), 4px bottom; 2px between rows.
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(12, 0, 12, 4)
        grid.setSpacing(2)
        grid.setColumnStretch(0, 1)   # label column absorbs slack → values right-aligned
        for i, (label, value) in enumerate(rows):
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:10px;")
            grid.addWidget(lbl, i, 0)
            val = QLabel(value)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val.setStyleSheet(f"color:{_th.TEXT_PRI}; font-family:'DejaVu Sans Mono'; font-size:10px;")
            grid.addWidget(val, i, 1)
        layout.addWidget(grid_w)


# ── Tab ───────────────────────────────────────────────────────────────────────

class TabPerfiles(QWidget):
    """Profile / cost tab with dimension inputs, pricing, labour, and result cards."""

    def __init__(self, state: AppState, on_state_change=None, on_add_profile=None, parent=None) -> None:
        super().__init__(parent)
        self._state = state
        self._on_state_change = on_state_change
        self._on_add_profile = on_add_profile   # opens the drawing module (Add profile)
        self._profile_key: Optional[str] = None
        self._tipo: Optional[TipoPerfil] = None
        self._catalog_entry: Optional[CustomProfileEntry] = None
        self._dim_entries: Dict[str, QLineEdit] = {}
        self._tiles: Dict[str, ProfileTile] = {}
        self._on_total_tab = False

        # ── Setup UI from .ui file ───────────────────────────────────────────
        self.ui = Ui_TabPerfiles()
        self.ui.setupUi(self)

        # Insert MaterialSubTabs at position 0 in main_layout (before splitter)
        self._subtabs = MaterialSubTabs(has_total=True)
        self._subtabs.before_switch.connect(self._on_before_subtab)
        self._subtabs.tab_changed.connect(self._on_subtab_change)
        self._subtabs.tab_added.connect(self._on_tab_added)
        self._subtabs.tab_removed.connect(self._on_tab_removed)
        self._subtabs.tab_renamed.connect(self._on_tab_renamed)
        self.ui.main_layout.insertWidget(0, self._subtabs)

        # Material/profile search bar (below subtabs, above the splitter)
        from PySide6.QtWidgets import QHBoxLayout, QSizePolicy as _SP
        self._mat_bar_frame = QFrame()
        self._mat_bar_frame.setStyleSheet("QFrame { background: transparent; }")
        self._mat_bar_frame.setFixedHeight(34)
        self._mat_bar_frame.setSizePolicy(_SP.Policy.Expanding, _SP.Policy.Fixed)
        _mbl = QHBoxLayout(self._mat_bar_frame)
        _mbl.setContentsMargins(4, 2, 4, 2)
        _mbl.setSpacing(4)
        self._mat_search_bar = StockMaterialSearchBar(
            placeholder=t("search_placeholder"),
            height=30,
        )
        self._mat_search_bar.selected.connect(self._on_material_selected)
        _mbl.addWidget(self._mat_search_bar)
        self.ui.main_layout.insertWidget(1, self._mat_bar_frame)

        # ── Layout stretch factors not expressible in .ui ────────────────────
        self.ui.btns0_layout.setStretch(0, 1)  # calc_btn stretch
        for i in range(self.ui.btns1_layout.count()):
            self.ui.btns1_layout.setStretch(i, 1)  # all export buttons stretch

        # §22 — Nesting source indicator: shows whether the Costs calculation
        # uses a completed Nesting-tab layout or a quick Cuts estimate.
        self._nesting_src_lbl = QLabel()
        self._nesting_src_lbl.setWordWrap(True)
        self._nesting_src_lbl.setContentsMargins(0, 2, 0, 2)
        self._nesting_src_lbl.hide()
        # Insert at position 2: after btns1(1), before weight_section_lbl(2→3).
        self.ui.config_inner_layout.insertWidget(2, self._nesting_src_lbl)
        self.ui.currency_row_layout.setStretch(1, 1)  # currency_combo stretch
        # Match the price fields above: 120px label column + 30px-tall control so
        # the currency selector lines up with Price/kg, Price/m, etc.
        self.ui.lbl_currency.setMinimumWidth(120)
        self.ui.currency_combo.setMinimumHeight(30)
        self.ui.currency_combo.setMaximumHeight(30)
        self.ui.dim_layout.setColumnStretch(1, 1)
        self.ui.field_espesor_layout.setStretch(1, 1)
        self.ui.field_kg_m_layout.setStretch(1, 1)
        self.ui.field_peso_esp_layout.setStretch(1, 1)
        self.ui.field_precio_kg_layout.setStretch(1, 1)
        self.ui.field_precio_m_layout.setStretch(1, 1)
        self.ui.field_precio_barra_layout.setStretch(1, 1)
        self.ui.field_margen_layout.setStretch(1, 1)
        self.ui.field_t_recto_layout.setStretch(1, 1)
        self.ui.field_pct_inglete_layout.setStretch(1, 1)
        self.ui.field_coste_op_layout.setStretch(1, 1)

        # ── Set "mono" property on all line edits ────────────────────────────
        for le in (
            self.ui.e_espesor, self.ui.e_kg_m, self.ui.e_peso_esp,
            self.ui.e_precio_kg, self.ui.e_precio_m,
            self.ui.e_precio_barra, self.ui.e_margen_beneficio,
            self.ui.e_t_recto, self.ui.e_pct_inglete, self.ui.e_coste_op,
        ):
            le.setProperty("mono", "true")   # numeric inputs → DejaVu Sans Mono via QSS

        # ── Style section labels ─────────────────────────────────────────────
        # "WEIGHT / PRICING / LABOUR" dividers: 9px bold secondary, 1px letter
        # spacing (small-caps look), padded, with a 1px bottom BORDER rule.
        sec_style = (
            f"color:{_th.TEXT_SEC}; font-size:9px; font-weight:bold; letter-spacing:1px;"
            f" padding:4px 0 2px 0; border-bottom:1px solid {_th.BORDER};"
        )
        self.ui.weight_section_lbl.setStyleSheet(sec_style)
        self.ui.pricing_section_lbl.setStyleSheet(sec_style)
        self.ui.labour_section_lbl.setStyleSheet(sec_style)

        # ── Style field labels ───────────────────────────────────────────────
        # All config field captions: 10px secondary text (uniform across sections).
        field_lbl_style = f"color:{_th.TEXT_SEC}; font-size:10px;"
        for lbl in (
            self.ui.lbl_espesor, self.ui.lbl_kg_m, self.ui.lbl_peso_esp,
            self.ui.lbl_precio_kg, self.ui.lbl_precio_m,
            self.ui.lbl_precio_barra, self.ui.lbl_margen,
            self.ui.lbl_t_recto, self.ui.lbl_pct_inglete, self.ui.lbl_coste_op,
            self.ui.lbl_currency,
        ):
            lbl.setStyleSheet(field_lbl_style)

        # ── Style results header ─────────────────────────────────────────────
        # "Results per cut" header on the right pane: 11px bold ACCENT, padded.
        self.ui.results_hdr.setStyleSheet(
            f"color:{_th.ACCENT}; font-weight:bold; font-size:11px; padding:4px 8px;"
        )

        # ── i18n text overrides ──────────────────────────────────────────────
        self._apply_i18n()

        # ── Button properties ────────────────────────────────────────────────
        # Calculate = accent (orange) button; size/shape from the variant QSS.
        self.ui.calc_btn.setProperty("variant", "accent")
        self.ui.calc_btn.style().polish(self.ui.calc_btn)

        # ── Connect signals ──────────────────────────────────────────────────
        # The button goes through _on_calculate_clicked so the optional cost
        # confirmation gate only applies to an explicit user calculate, not to
        # the programmatic re-renders (currency/cost-mode live refresh).
        self.ui.calc_btn.clicked.connect(self._on_calculate_clicked)
        self.ui.clear_btn.clicked.connect(self._limpiar)
        self.ui.btn_excel.clicked.connect(self._export_excel)
        self.ui.btn_pdf.clicked.connect(self._export_pdf)
        self.ui.btn_docx.clicked.connect(self._export_docx)
        self.ui.btn_print.clicked.connect(self._print)
        self.ui.profile_combo.currentIndexChanged.connect(self._on_profile_combo_change)
        self.ui.cb_macizo.toggled.connect(self._toggle_espesor)
        self.ui.currency_combo.currentIndexChanged.connect(self._on_currency_change)
        self.ui.cost_mode_combo.currentIndexChanged.connect(self._on_cost_mode_change)

        # ── Populate currency combo ──────────────────────────────────────────
        for code in CURRENCIES:
            self.ui.currency_combo.addItem(currency_display(code), code)
        idx = self.ui.currency_combo.findData(self._state.currency or "EUR")
        if idx >= 0:
            self.ui.currency_combo.setCurrentIndex(idx)

        # ── Cost mode + confirm-before-calc (moved here from the Settings menu).
        # Cost management is now centralised in this Costing tab.
        prefs0 = app_config.get()
        self.ui.cost_mode_combo.addItem(t("cost_mode_shared"), "shared")
        self.ui.cost_mode_combo.addItem(t("cost_mode_individual"), "individual")
        cm_idx = self.ui.cost_mode_combo.findData(getattr(prefs0, "cost_mode", "shared"))
        if cm_idx >= 0:
            self.ui.cost_mode_combo.setCurrentIndex(cm_idx)
        self.ui.cb_confirm_costs.setChecked(bool(getattr(prefs0, "confirm_costs", True)))
        self.ui.cb_confirm_costs.toggled.connect(self._on_confirm_costs_toggle)

        # ── Splitter settings ────────────────────────────────────────────────
        # Left config pane width is restored from prefs (split_costes, default
        # 340px); the right results pane takes the rest, floored at 200px so it
        # never disappears on a narrow window.
        prefs = app_config.get()
        split_pos = getattr(prefs, "split_costes", 340)
        self.ui.splitter.setSizes([split_pos, max(200, self.width() - split_pos)])
        self.ui.splitter.setStretchFactor(0, 0)
        self.ui.splitter.setStretchFactor(1, 1)
        self.ui.splitter.splitterMoved.connect(
            lambda pos, _: self._save_split(self.ui.splitter)
        )

        # ── Initialize dynamic content ───────────────────────────────────────
        self._rebuild_favorites()
        self._rebuild_profile_combo()
        self._show_empty_results()

    # ── i18n ─────────────────────────────────────────────────────────────────

    def _apply_i18n(self) -> None:
        """Set all translatable labels / button text via t()."""
        sym = self._cur_symbol()

        self.ui.calc_btn.setText(t("calculate"))
        self.ui.calc_btn.setIcon(themed_icon("gear", "#FFFFFF", 14))
        self.ui.calc_btn.setIconSize(QSize(14, 14))
        self.ui.clear_btn.setText(t("clear"))
        # Export/print row: icon-only ghost buttons (SVG glyph + hover tooltip),
        # mirroring the Cuts toolbar. Text labels are dropped — they were clipped
        # by the .ui's 24px height cap — and the buttons are forced to 40px so
        # the glyphs render crisply and nothing is cut off.
        self._style_costs_action_buttons()

        self.ui.weight_section_lbl.setText(t("weight_section").upper())
        self.ui.pricing_section_lbl.setText(t("pricing_section").upper())
        self.ui.labour_section_lbl.setText(t("labour_section").upper())

        # Cost-mode row + confirm checkbox (centralised cost management). The
        # combo items are language-dependent, so re-label them preserving the
        # current selection.
        self.ui.lbl_cost_mode.setText(t("cost_mode"))
        self.ui.cb_confirm_costs.setText(t("confirm_costs_label"))
        if self.ui.cost_mode_combo.count() >= 2:
            self.ui.cost_mode_combo.blockSignals(True)
            self.ui.cost_mode_combo.setItemText(0, t("cost_mode_shared"))
            self.ui.cost_mode_combo.setItemText(1, t("cost_mode_individual"))
            self.ui.cost_mode_combo.blockSignals(False)

        self.ui.lbl_espesor.setText(t("wall_thickness", u=units.u_len()))
        self.ui.cb_macizo.setText(t("solid_section"))
        self.ui.lbl_kg_m.setText("kg/m")
        self.ui.lbl_peso_esp.setText(t("specific_weight", u_density=units.u_density()))
        self.ui.lbl_precio_kg.setText(t('price_kg', sym=sym))
        self.ui.lbl_precio_m.setText(t('price_m', sym=sym))
        self.ui.lbl_precio_barra.setText(t('price_bar', sym=sym))
        self.ui.lbl_margen.setText(t('profit_margin'))
        self.ui.lbl_currency.setText(t("currency"))
        self.ui.cb_retales.setText(t("distribute_scrap"))
        self.ui.lbl_t_recto.setText(t("straight_cut_time"))
        self.ui.lbl_pct_inglete.setText(f"{t('miter_extra_pct')} (%)")
        self.ui.lbl_coste_op.setText(t('operator_cost', sym=self._cur_symbol()))
        self.ui.results_hdr.setText(t("results_per_cut"))

    def _style_costs_action_buttons(self) -> None:
        """Turn the Excel/PDF/DOCX/Print buttons into icon-only ghost buttons
        with a themed SVG glyph and a hover tooltip (like the Cuts toolbar).

        The .ui caps these at 24px (text was clipped); force 40px square so the
        glyphs are crisp and nothing is cut off. Icons are re-tinted on theme
        switch in refresh_theme()."""
        specs = (
            (self.ui.btn_excel, "excel", "tip_costs_export_excel"),
            (self.ui.btn_pdf,   "pdf",   "tip_costs_export_pdf"),
            (self.ui.btn_docx,  "doc",   "tip_costs_export_docx"),
            (self.ui.btn_print, "print", "tip_costs_print"),
        )
        for btn, icon_name, tip_key in specs:
            btn.setText("")
            btn.setToolTip(t(tip_key))
            btn.setIcon(themed_icon(icon_name, _th.TEXT_PRI, 20))
            btn.setIconSize(QSize(20, 20))
            btn.setStyleSheet("")  # drop the .ui's 10px font rule
            btn.setMinimumSize(QSize(40, 40))
            btn.setMaximumSize(QSize(40, 40))
            btn.setProperty("variant", "ghost")
            btn.style().polish(btn)

    # ── Profile management ────────────────────────────────────────────────────

    def _rebuild_favorites(self) -> None:
        # Clear existing tiles. Detach synchronously (hide + setParent(None))
        # before deleteLater: a widget pending deletion keeps its old geometry
        # and repaints over the freshly built tile, so on a theme switch the
        # stale dark "+" add-tile would otherwise linger on top of the new one.
        while self.ui.fav_widget.layout().count() > 1:
            item = self.ui.fav_widget.layout().takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        self._tiles.clear()
        import os

        # ── Locked mode: custom catalog profile active ────────────────────────
        # When a catalog profile was selected (from Nesting/Cuts or the search
        # bar), show only its thumbnail — no interactive builtin-shape tiles, no
        # combo dropdown. The user unlocks by clicking "Clear".
        if self._catalog_entry is not None:
            self.ui.profile_combo.setVisible(False)
            img = ""
            if getattr(self._catalog_entry, "image", ""):
                p = os.path.join(app_config.PROFILES_DIR, self._catalog_entry.image)
                if os.path.isfile(p):
                    img = p
            key = f"custom:{self._catalog_entry.name}"
            _ptype = _tipo_for_entry(self._catalog_entry).value
            tile = ProfileTile(
                profile_key=key,
                profile_type=_ptype,
                display_name=self._catalog_entry.name,
                image_path=img,
            )
            tile.selected = True
            self._tiles[key] = tile
            fav_lay = self.ui.fav_widget.layout()
            fav_lay.insertWidget(fav_lay.count() - 1, tile)
            return

        # ── Normal mode: no catalog profile locked ────────────────────────────
        self.ui.profile_combo.setVisible(True)
        builtins = _builtin_profiles()

        # Combined profile map (builtins + custom). Custom profiles carry their
        # thumbnail image so the gallery shows the drawing-module representation.
        all_profs: dict = {k: (tp, lbl, "") for k, tp, lbl in builtins}
        for cp in getattr(app_config.get(), "custom_profiles", []):
            img = ""
            if getattr(cp, "image", ""):
                p = os.path.join(app_config.PROFILES_DIR, cp.image)
                if os.path.isfile(p):
                    img = p
            _cp_tipo = _tipo_for_entry(cp)
            all_profs[f"custom:{cp.name}"] = (_cp_tipo, cp.name, img)

        # Up to 5 tiles: most-recently-used first (usage history), then fill with
        # builtins. Custom keys ("custom:<name>") are now eligible too.
        # Leave room for the trailing "Add profile" tile so nothing is clipped.
        max_tiles = 4 if self._on_add_profile is not None else 5
        shown_keys: list[str] = []
        top = getattr(app_config.get(), "profile_usage", {})
        for k in sorted(top, key=lambda k: -top[k]):
            if k in all_profs and k not in shown_keys:
                shown_keys.append(k)
        for k, _, _ in builtins:
            if k not in shown_keys:
                shown_keys.append(k)
            if len(shown_keys) >= max_tiles:
                break
        shown_keys = shown_keys[:max_tiles]

        fav_lay = self.ui.fav_widget.layout()
        for key in shown_keys:
            if key not in all_profs:
                continue
            tp, lbl, img = all_profs[key]
            tile = ProfileTile(
                profile_key=key,
                profile_type=tp.value if tp else "rect",
                display_name=lbl,
                image_path=img,
            )
            tile.selected = (key == self._profile_key)
            tile.clicked.connect(lambda k=key: self._select_profile(k))
            self._tiles[key] = tile
            fav_lay.insertWidget(fav_lay.count() - 1, tile)

        # "Add profile" tile at the end — opens the drawing module (same as
        # Settings → Add new profile).
        if self._on_add_profile is not None:
            add_tile = QPushButton("+")
            add_tile.setFixedSize(72, 90)
            add_tile.setToolTip(t("add_new_profile"))
            add_tile.setCursor(Qt.CursorShape.PointingHandCursor)
            # Add-tile fill is BG_MID (not BG_CARD): in light mode BG_CARD is pure
            # white and the dashed outline vanished against the near-white panel,
            # making the tile look invisible. BG_MID reads as a recessed "slot" in
            # both themes; the ACCENT "+" glyph and BORDER_LIT dashed edge keep the
            # affordance legible everywhere.
            add_tile.setStyleSheet(
                f"QPushButton {{ color:{_th.ACCENT}; background:{_th.BG_MID};"
                f" border:1px dashed {_th.BORDER_LIT}; border-radius:4px; font-size:28px; }}"
                f"QPushButton:hover {{ color:{_th.ACCENT_HVR}; background:{_th.BG_HOVER};"
                f" border-color:{_th.ACCENT}; }}"
            )
            add_tile.clicked.connect(lambda: self._on_add_profile())
            fav_lay.insertWidget(fav_lay.count() - 1, add_tile)

    def _rebuild_profile_combo(self) -> None:
        self.ui.profile_combo.blockSignals(True)
        current_key = self._profile_key
        self.ui.profile_combo.clear()
        self.ui.profile_combo.addItem(t("select_profile_dropdown"), "")
        for k, tp, lbl in _builtin_profiles():
            self.ui.profile_combo.addItem(lbl, k)
        # Custom profiles
        for cp in getattr(app_config.get(), "custom_profiles", []):
            self.ui.profile_combo.addItem(cp.name, f"custom:{cp.name}")
        if current_key:
            idx = self.ui.profile_combo.findData(current_key)
            if idx >= 0:
                self.ui.profile_combo.setCurrentIndex(idx)
        self.ui.profile_combo.blockSignals(False)

    def _select_profile(self, key: str) -> None:
        _prev_locked = self._catalog_entry is not None
        self._profile_key = key
        for k, tile in self._tiles.items():
            tile.selected = (k == key)
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.profile_key = key

        # Resolve tipo. Catalogue profiles ("custom:<name>") map their
        # geometry_type to a builtin tipo so the cost calc still works; the
        # bottom pane shows a read-only summary instead of editable dims.
        self._catalog_entry = None
        if key.startswith("custom:"):
            self._catalog_entry = self._find_catalog_entry(key[len("custom:"):])

        if self._catalog_entry is not None:
            self._tipo = _tipo_for_entry(self._catalog_entry)
        else:
            for k, tp, _ in _builtin_profiles():
                if k == key:
                    self._tipo = tp
                    break
            else:
                self._tipo = None

        # Rebuild favorites gallery when the locked/unlocked state changes.
        # Locked (catalog profile) → show only the selected thumbnail, hide combo.
        # Unlocked (builtin) → restore full MRU gallery and combo.
        _now_locked = self._catalog_entry is not None
        if _prev_locked != _now_locked:
            self._rebuild_favorites()

        # Update combo (only visible in unlocked mode, but set regardless so
        # the combo is in sync when the user unlocks via Clear).
        idx = self.ui.profile_combo.findData(key)
        self.ui.profile_combo.blockSignals(True)
        if idx >= 0:
            self.ui.profile_combo.setCurrentIndex(idx)
        self.ui.profile_combo.blockSignals(False)

        if self._catalog_entry is not None:
            self._show_catalog_panel(self._catalog_entry)
        else:
            self._rebuild_dim_fields()

        # Track usage
        usage = getattr(app_config.get(), "profile_usage", {})
        usage[key] = usage.get(key, 0) + 1
        app_config.get().profile_usage = usage

    def _find_catalog_entry(self, name: str) -> Optional[CustomProfileEntry]:
        matches = [cp for cp in getattr(app_config.get(), "custom_profiles", [])
                   if cp.name == name]
        if not matches:
            return None
        # Prefer the most complete entry: one whose meta carries a geometry_type
        # and that has a rendered thumbnail image. This stops a stale/partial
        # duplicate (a test fixture, or an entry saved by an older build without
        # geometry_type/image) from shadowing the real catalogue profile and
        # forcing a rectangular fallback thumbnail.
        def _score(cp):
            meta = cp.meta or {}
            return (
                1 if (meta.get("geometry_type") or "").strip() else 0,
                1 if getattr(cp, "image", "") else 0,
            )
        matches.sort(key=_score, reverse=True)
        return matches[0]

    def _on_profile_combo_change(self, idx: int) -> None:
        key = self.ui.profile_combo.itemData(idx)
        if key:
            self._select_profile(key)

    def _clear_dim_layout(self) -> None:
        while self.ui.dim_layout.count():
            item = self.ui.dim_layout.takeAt(0)
            w = item.widget()
            if w:
                # Detach synchronously before deleteLater: a widget pending
                # deletion keeps its old geometry and repaints over the rebuilt
                # layout, so switching from editable dim fields to the catalogue
                # summary (or vice versa) leaves ghost values overlapping the new
                # rows until the next event loop. hide()+setParent(None) removes
                # them immediately.
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._dim_entries.clear()

    def _rebuild_dim_fields(self) -> None:
        self._clear_dim_layout()
        # Clear any kg/m value set by the catalog panel so it doesn't bleed into
        # builtin cost calculations when the user switches profile types.
        self.ui.e_kg_m.setText("")
        # Re-enable weight/thickness inputs disabled by _on_kg_m_change() when
        # the catalog panel was active (e_peso_esp stays disabled otherwise).
        self._on_kg_m_change()
        # Builtin profile: editable wall thickness + macizo are relevant again.
        self.ui.field_espesor.setVisible(True)
        self.ui.cb_macizo.setVisible(True)

        if not self._tipo:
            return

        # One label/field row per dimension of the selected profile type. Labels
        # are 10px TEXT_SEC; each entry is a 30px-tall mono line edit (standard
        # control height, monospaced so numeric dimensions align).
        dims = _tipo_dims(self._tipo)
        for row_i, (label, key) in enumerate(dims):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:10px;")
            self.ui.dim_layout.addWidget(lbl, row_i, 0)
            entry = QLineEdit()
            entry.setFixedHeight(30)
            entry.setProperty("mono", "true")
            self.ui.dim_layout.addWidget(entry, row_i, 1)
            self._dim_entries[key] = entry

        self._toggle_espesor()

    def _show_catalog_panel(self, entry: CustomProfileEntry) -> None:
        """Catalogue/DB profile: replace the editable geometry fields with a
        read-only parameter summary (from entry.meta) plus a single
        "Edit material" button that opens the consolidated editor. The geometry
        is owned by the catalogue, so wall-thickness/macizo inputs are hidden;
        the pricing/labour sections stay editable for costing."""
        self._clear_dim_layout()
        self.ui.field_espesor.setVisible(False)
        self.ui.cb_macizo.setVisible(False)

        meta = entry.meta or {}
        material = localize_material(meta.get("material", "")) or "—"
        rows: list[tuple[str, str]] = [(t("stock_material"), material)]
        for key, label in (("h", "h"), ("b", "b"), ("tw", "tw"), ("tf", "tf")):
            val = meta.get(key)
            if val:
                rows.append((label, f"{val:g} {units.u_len()}"))
        seccion = meta.get("seccion_cm2")
        if seccion:
            rows.append((t("section"), f"{seccion:g} cm²"))
        peso = meta.get("peso_lineal_kg_m")
        if peso:
            rows.append((t("weight_per_meter"), f"{peso:g} kg/m"))

        for row_i, (label, value) in enumerate(rows):
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:12px;")
            self.ui.dim_layout.addWidget(lbl, row_i, 0)
            val = QLabel(value)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val.setStyleSheet(
                f"color:{_th.TEXT_PRI}; font-family:'DejaVu Sans Mono'; font-size:12px;"
            )
            self.ui.dim_layout.addWidget(val, row_i, 1)

        btn = QPushButton(t("edit_material_btn"))
        btn.setFixedHeight(30)
        btn.clicked.connect(self._edit_catalog_material)
        self.ui.dim_layout.addWidget(btn, len(rows), 0, 1, 2)

        # Auto-fill the weight inputs from meta so the existing cost path
        # (calcular_resultado uses kg_por_m when > 0) prices correctly without
        # any engine change. Specific weight backs the fallback path.
        if peso:
            self.ui.e_kg_m.setText(f"{peso:g}")
        sw = meta.get("specific_weight")
        if sw:
            self.ui.e_peso_esp.setText(f"{sw:g}")
        self._on_kg_m_change()

    def _edit_catalog_material(self) -> None:
        """Open the consolidated profile/material editor for the selected
        catalogue entry, then refresh so any changes are reflected."""
        entry = self._catalog_entry
        if entry is None:
            return
        from nestube.ui_qt.dialogs.profile_manager import ProfileManager
        ProfileManager(self, on_change=self.refresh_profile_selector,
                       initial_select_id=entry.id).exec()
        # Re-resolve the (possibly edited) entry and redraw the summary.
        if self._profile_key:
            self._select_profile(self._profile_key)

    # ── Calculation ───────────────────────────────────────────────────────────

    def _barras_for_costing(self, ctx) -> list:
        """Bars passed to the cost calculation, per the chosen cost mode.

        This only prepares the input to calcular_resultado; it does not change
        the engine. "shared" uses the globally optimised bars (waste shared
        across pieces); "individual" puts each piece on its own bar so no
        remnant is shared.

        In "shared" mode the real Nesting-tab layout wins whenever it covers
        every cut: costs then reflect that layout's actual bar count and
        remnants (manual moves, 2D nesting, common cuts included), and the
        layout is left untouched. Only when there is no complete layout do we
        fall back to the quick FFD/BFD/NFD estimate.
        """
        if app_config.get().cost_mode == "individual":
            bars = []
            for c in ctx.cortes:
                for _ in range(max(1, int(getattr(c, "cantidad", 1) or 1))):
                    bars.append([c.largo])
            return bars
        if layout_covers_all_cuts(ctx):
            return layout_to_barras(ctx.nesting_layout)
        return recompute_auto_barras(ctx, self._state.calc_system)

    def _update_nesting_src_lbl(self, ctx: MaterialContext) -> None:
        """§22: Update the indicator showing whether costs use the Nesting-tab
        layout or the quick Cuts estimate."""
        if not hasattr(self, "_nesting_src_lbl"):
            return
        if not ctx or not getattr(ctx, "cortes", None):
            self._nesting_src_lbl.hide()
            return
        if layout_covers_all_cuts(ctx):
            self._nesting_src_lbl.setText(t("costs_using_nesting"))
            self._nesting_src_lbl.setStyleSheet(
                f"color:{_th.ACCENT}; font-size:10px;"
            )
        else:
            self._nesting_src_lbl.setText(t("costs_using_quick_calc"))
            self._nesting_src_lbl.setStyleSheet(
                f"color:{_th.TEXT_SEC}; font-size:10px;"
            )
        self._nesting_src_lbl.show()

    def _calcular(self) -> None:
        if self._on_total_tab:
            self._calcular_total()
            return

        currency_idx = self.ui.currency_combo.currentIndex()
        currency = self.ui.currency_combo.itemData(currency_idx) or "EUR"
        self._state.currency = currency
        app_config.get().currency = currency
        app_config.save()

        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        cortes = ctx.cortes
        longitud = ctx.longitud_barra

        if not cortes:
            QMessageBox.critical(self, t("no_cuts_error"), t("no_cuts_msg"))
            return
        if longitud <= 0:
            QMessageBox.critical(self, t("data_error"), t("invalid_bar_length"))
            return

        barras = self._barras_for_costing(ctx)
        self._state.barras_necesarias = list(barras)

        perfil = self._build_config()
        if perfil is None:
            return

        self._state.perfil = perfil
        ctx.perfil = ConfigPerfil.from_dict(perfil.to_dict())
        save_state_to_context(self._state, self._state.active_material_index)
        n_ingletes = sum(1 for c in cortes if c.inglete1 or c.inglete2)

        self._clear_results()
        total_precio = 0.0
        for corte in cortes:
            res = calcular_resultado(corte, perfil, barras, longitud, n_ingletes)
            total_precio += res.precio_total_linea
            card = _ResultCard(res, currency)
            self.ui.results_layout.insertWidget(self.ui.results_layout.count() - 1, card)

        # Separator + total
        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background:{_th.ACCENT};")
        self.ui.results_layout.insertWidget(self.ui.results_layout.count() - 1, sep)

        total_lbl = QLabel(t("total_order", total=f"{total_precio:,.2f}", currency=currency))
        total_lbl.setStyleSheet(
            f"color:{_th.ACCENT}; font-size:14px; font-weight:bold; padding:4px 8px;"
        )
        self.ui.results_layout.insertWidget(self.ui.results_layout.count() - 1, total_lbl)

        self._update_nesting_src_lbl(ctx)

        if self._on_state_change:
            self._on_state_change()

    def _calcular_total(self) -> None:
        self._clear_results()
        ensure_material_contexts(self._state)
        grand = 0.0
        for i, ctx in enumerate(self._state.material_contexts):
            if not ctx.cortes:
                continue
            barras = self._barras_for_costing(ctx)
            perfil = ctx.perfil
            if perfil is None:
                continue
            longitud = ctx.longitud_barra
            n_ingletes = sum(1 for c in ctx.cortes if c.inglete1 or c.inglete2)
            mat_total = 0.0
            for corte in ctx.cortes:
                res = calcular_resultado(corte, perfil, barras, longitud, n_ingletes)
                mat_total += res.precio_total_linea
            grand += mat_total
            from nestube.naming import context_tab_label
            name = context_tab_label(ctx, i)
            mat_lbl = QLabel(f"── {name}: {mat_total:,.2f} {self._state.currency}")
            mat_lbl.setStyleSheet(f"color:{_th.TEXT_PRI}; font-size:11px; padding:2px 8px;")
            self.ui.results_layout.insertWidget(self.ui.results_layout.count() - 1, mat_lbl)

        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background:{_th.ACCENT};")
        self.ui.results_layout.insertWidget(self.ui.results_layout.count() - 1, sep)

        total_lbl = QLabel(
            t("total_order", total=f"{grand:,.2f}", currency=self._state.currency)
        )
        total_lbl.setStyleSheet(
            f"color:{_th.ACCENT}; font-size:14px; font-weight:bold; padding:4px 8px;"
        )
        self.ui.results_layout.insertWidget(self.ui.results_layout.count() - 1, total_lbl)

    # ── Config builder ────────────────────────────────────────────────────────

    def _read_cost_fields(self) -> Tuple[ParametrosMaterial, ParametrosManoObra]:
        """Read the profile-INDEPENDENT pricing/weight/labour inputs from the form.

        These cost fields are meaningful even with no profile geometry resolved
        (a fictitious material, prices entered before a profile is picked), so
        they are read here once and reused by both `_build_config` and the
        no-profile fallback in `_save_active_perfil` — guaranteeing every filled
        cost field in a Costs sub-tab is persisted to its MaterialContext / Job
        (§24), not silently dropped when `_tipo` is None.
        """
        material = ParametrosMaterial(
            peso_especifico=self._f(self.ui.e_peso_esp, 7.85),
            precio_kg=self._f(self.ui.e_precio_kg),
            precio_m2=0.0,   # €/m² removed from the UI (unused) — TODO §4
            precio_m=self._f(self.ui.e_precio_m),
            kg_por_m=self._f(self.ui.e_kg_m),
            precio_barra=self._f(self.ui.e_precio_barra),
            margen_beneficio=self._f(self.ui.e_margen_beneficio),
            repartir_retales=self.ui.cb_retales.isChecked(),
        )
        mano_obra = ParametrosManoObra(
            tiempo_corte_recto=self._f(self.ui.e_t_recto, 3),
            porcentaje_inglete=self._f(self.ui.e_pct_inglete, 35),
            coste_operario_hora=self._f(self.ui.e_coste_op, 30),
        )
        return material, mano_obra

    def _build_config(self, quiet: bool = False) -> Optional[ConfigPerfil]:
        if not self._tipo:
            if not quiet:
                QMessageBox.critical(
                    self, t("select_profile_error"), t("select_profile_msg")
                )
            return None

        # Catalogue profile: geometry comes from entry.meta (not editable
        # fields); pricing/labour still come from the form inputs. kg_por_m
        # from meta drives the weight via the existing calc path.
        if self._catalog_entry is not None:
            return self._build_config_from_catalog(self._catalog_entry)

        dim_vals = {k: self._f(e) for k, e in self._dim_entries.items()}
        extra = {k: v for k, v in dim_vals.items() if k.startswith("custom_")}
        material, mano_obra = self._read_cost_fields()
        return ConfigPerfil(
            dimensiones=PerfilDimensiones(
                tipo=self._tipo,
                diametro=dim_vals.get("diametro", 0),
                lado_a=dim_vals.get("lado_a", 0),
                lado_b=dim_vals.get("lado_b", 0),
                lado_c=dim_vals.get("lado_c", 0),
                espesor=self._f(self.ui.e_espesor),
                espesor_int_H=dim_vals.get("espesor_int_H", 0),
                macizo=self.ui.cb_macizo.isChecked(),
                extra_dims=extra,
            ),
            material=material,
            mano_obra=mano_obra,
        )

    def _build_config_from_catalog(self, entry: CustomProfileEntry) -> ConfigPerfil:
        """Build a ConfigPerfil for a catalogue/DB profile: dimensions and weight
        from entry.meta, pricing/labour from the form. No engine change — weight
        flows through ParametrosMaterial.kg_por_m (preferred by calcular_resultado).
        """
        meta = entry.meta or {}
        tipo = _tipo_for_geometry(meta.get("geometry_type", ""))
        h = float(meta.get("h", 0) or 0)
        b = float(meta.get("b", 0) or 0)
        tw = float(meta.get("tw", 0) or 0)
        tf = float(meta.get("tf", 0) or 0)
        # Map h/b to the builtin dimension slots the tipo expects.
        if tipo == TipoPerfil.REDONDO:
            diametro, lado_a, lado_b, lado_c = h, 0.0, 0.0, 0.0
        else:
            diametro, lado_a, lado_b, lado_c = 0.0, h, b, tf
        # kg/m: prefer the form value (auto-filled from meta), else meta directly.
        kg_m = self._f(self.ui.e_kg_m) or float(meta.get("peso_lineal_kg_m", 0) or 0)
        peso_esp = self._f(self.ui.e_peso_esp, 0.0) or float(
            meta.get("specific_weight", 7.85) or 7.85)
        return ConfigPerfil(
            dimensiones=PerfilDimensiones(
                tipo=tipo,
                diametro=diametro,
                lado_a=lado_a,
                lado_b=lado_b,
                lado_c=lado_c,
                espesor=tw,
                espesor_int_H=tw,
                macizo=bool(meta.get("macizo", False)),
            ),
            material=ParametrosMaterial(
                peso_especifico=peso_esp,
                precio_kg=self._f(self.ui.e_precio_kg),
                precio_m2=0.0,
                precio_m=self._f(self.ui.e_precio_m),
                kg_por_m=kg_m,
                precio_barra=self._f(self.ui.e_precio_barra),
                margen_beneficio=self._f(self.ui.e_margen_beneficio),
                repartir_retales=self.ui.cb_retales.isChecked(),
            ),
            mano_obra=ParametrosManoObra(
                tiempo_corte_recto=self._f(self.ui.e_t_recto, 3),
                porcentaje_inglete=self._f(self.ui.e_pct_inglete, 35),
                coste_operario_hora=self._f(self.ui.e_coste_op, 30),
            ),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _f(entry: QLineEdit, default: float = 0.0) -> float:
        try:
            return float(entry.text())
        except (ValueError, TypeError):
            return default

    def _cur_symbol(self) -> str:
        code = self._state.currency or "EUR"
        return CURRENCY_SYMBOLS.get(code, code)

    def _clear_results(self) -> None:
        # Detach synchronously (hide + setParent(None)) before deleteLater:
        # deleteLater only fires on the next event loop, and until then the old
        # result cards keep their geometry and repaint under the freshly
        # re-rendered ones — e.g. a stale EUR total showing beneath a new USD
        # render after a live currency change.
        while self.ui.results_layout.count() > 1:
            item = self.ui.results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _show_empty_results(self) -> None:
        hint = QLabel(t("empty_results_hint"))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:11px; padding:60px;")
        self.ui.results_layout.insertWidget(0, hint)

    def _toggle_espesor(self) -> None:
        macizo = self.ui.cb_macizo.isChecked()
        self.ui.e_espesor.setEnabled(not macizo)
        if macizo:
            self.ui.e_espesor.clear()

    def _on_kg_m_change(self) -> None:
        has_kg_m = bool(self.ui.e_kg_m.text().strip())
        for e in (self.ui.e_espesor, self.ui.e_peso_esp):
            e.setEnabled(not has_kg_m)
        for e in self._dim_entries.values():
            e.setEnabled(not has_kg_m)

    def _limpiar(self) -> None:
        self._profile_key = None
        self._tipo = None
        self._catalog_entry = None
        self.ui.profile_combo.setCurrentIndex(0)
        for tile in self._tiles.values():
            tile.selected = False
        self._rebuild_favorites()
        self._rebuild_dim_fields()
        for entry, default in [
            (self.ui.e_espesor, ""), (self.ui.e_precio_kg, ""),
            (self.ui.e_precio_m, ""),
            (self.ui.e_kg_m, ""), (self.ui.e_precio_barra, ""),
            (self.ui.e_margen_beneficio, ""), (self.ui.e_peso_esp, "7.85"),
            (self.ui.e_t_recto, "3"), (self.ui.e_pct_inglete, "35"),
            (self.ui.e_coste_op, "30"),
        ]:
            entry.setText(default)
        self.ui.cb_macizo.setChecked(False)
        self.ui.cb_retales.setChecked(False)
        self._toggle_espesor()
        self._clear_results()
        self._show_empty_results()

    # ── Subtab callbacks ──────────────────────────────────────────────────────

    def _on_before_subtab(self, from_idx: int, to_idx: int) -> None:
        if not self._on_total_tab:
            self._save_active_perfil()
            save_state_to_context(self._state, from_idx)

    def _on_subtab_change(self, idx: int) -> None:
        tab_count = self._subtabs.count()
        is_total = (idx >= tab_count)  # Total tab is beyond material tabs
        self._on_total_tab = is_total

        if is_total:
            # The Total tab aggregates every material context. Compute it live on
            # entry so it reflects the latest cuts/prices from all sub-tabs.
            self._calcular_total()
            return

        # Load the target context into shared state so state.cortes / perfil /
        # bar-params stay consistent with active_material_index. Without this,
        # _flush_main_tab later calls save_state_to_context with a stale
        # state.cortes (from the previous sub-tab) and overwrites the new
        # context's cuts with the old context's data.
        load_context_to_state(self._state, idx)
        ensure_material_contexts(self._state)
        self._apply_context_to_ui()

        # Each sub-tab has its own cuts/profile/prices, so the results panel must
        # follow the active sub-tab — not stay frozen on the previously-computed
        # material. Recompute live when this context has cuts; otherwise clear the
        # panel so stale numbers from another material are never shown.
        ctx = self._state.material_contexts[idx]
        if getattr(ctx, "cortes", None) and getattr(ctx, "longitud_barra", 0) > 0:
            self._calcular()
        else:
            self._clear_results()
            self._show_empty_results()

    def _save_active_perfil(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        perfil = self._build_config(quiet=True)
        if perfil is None:
            # No profile geometry resolved yet, but the user may still have
            # filled pricing/labour fields (fictitious material, prices entered
            # before a profile is chosen). Persist those onto the context's
            # existing perfil — keeping its dimensions — so they survive a
            # sub-tab switch or Job save instead of being dropped (§24).
            perfil = ConfigPerfil.from_dict(ctx.perfil.to_dict())
            perfil.material, perfil.mano_obra = self._read_cost_fields()
        self._state.perfil = perfil
        ctx.perfil = ConfigPerfil.from_dict(perfil.to_dict())

    def _on_tab_added(self, idx: int) -> None:
        # New Costs sub-tab = a new independent subjob; create the context so it
        # doesn't share data with the others (mirrors Cuts/Nesting). Seed the
        # global cost defaults (§27) so a fresh sub-tab starts at the user's
        # configured operator cost / cut time / mitre % / margin.
        from nestube import app_config as _ac
        while len(self._state.material_contexts) <= idx:
            ctx = MaterialContext()
            _ac.apply_cost_defaults(ctx.perfil)
            self._state.material_contexts.append(ctx)
        ensure_material_contexts(self._state)

    def _on_tab_removed(self, idx: int) -> None:
        # Flush the active tab's cost form into its context BEFORE the pop so a
        # surviving tab's edits aren't lost on the reload below (§27).
        old_active = self._state.active_material_index
        if 0 <= old_active < len(self._state.material_contexts) and old_active != idx:
            self._save_active_perfil()
        if idx < len(self._state.material_contexts):
            self._state.material_contexts.pop(idx)
        ensure_material_contexts(self._state)
        self._state.active_material_index = self._subtabs.active_index()
        load_context_to_state(self._state, self._state.active_material_index)
        self._apply_context_to_ui()

    def _on_tab_renamed(self, idx: int, name: str) -> None:
        ensure_material_contexts(self._state)
        if idx < len(self._state.material_contexts):
            # Persist via custom_display_name (honoured by context_tab_label).
            self._state.material_contexts[idx].custom_display_name = name
            self._state.material_contexts[idx].name = name

    def _on_material_selected(self, sel) -> None:
        set_material_selection(
            self._state, sel.profile_name or "", sel.material or "", sel.quality or "",
        )
        # Ask (once per profile) for the cutting height, like Cuts/Nesting.
        from nestube.ui_qt.cutting_height import resolve_cutting_height
        resolve_cutting_height(self.window(), self._state)
        # Rename the active sub-tab to profile · material.
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        label = " · ".join(filter(None, [
            (sel.profile_name or "").strip(),
            (sel.material or "").strip(),
        ]))
        if label:
            ctx.name = label
            self._subtabs.rename_tab(self._state.active_material_index, label)
        save_state_to_context(self._state, self._state.active_material_index)
        # Reflect the new profile in the tiles/dropdown/fields immediately.
        self._apply_context_to_ui()

    def _apply_context_to_ui(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        perfil = ctx.perfil or self._state.perfil
        if perfil:
            self.set_values(perfil.to_dict())
        # Highlight the right profile tile/combo. A catalogue profile selected by
        # name (e.g. IPE 200) wins over whatever set_values() highlighted from the
        # raw cross-section tipo, so the tab shows the actual chosen profile and
        # not the first builtin tile.
        prof = getattr(ctx, "profile_name", "") or ""
        pk = ""
        if prof and self._find_catalog_entry(prof) is not None:
            pk = "custom:" + prof
        if not pk:
            pk = getattr(ctx, "profile_key", "") or ""
        if pk:
            self._select_profile(pk)
        # Restore material/profile search bar display from context.
        prof = getattr(ctx, "profile_name", "") or ""
        mat = getattr(ctx, "material", "") or ""
        qual = getattr(ctx, "quality", "") or ""
        if hasattr(self, "_mat_search_bar"):
            self._mat_search_bar.set_selection(prof, mat, qual)

        self._update_nesting_src_lbl(ctx)

    # ── Currency ──────────────────────────────────────────────────────────────

    def _on_currency_change(self) -> None:
        currency = self.ui.currency_combo.currentData() or "EUR"
        self._state.currency = currency
        app_config.get().currency = currency
        self.refresh_currency()

    def _on_cost_mode_change(self) -> None:
        """Cost mode (shared / individual) — moved from the Settings menu to this
        tab. Persists the choice and re-renders results live."""
        mode = self.ui.cost_mode_combo.currentData() or "shared"
        prefs = app_config.get()
        prefs.cost_mode = mode
        app_config.save(prefs)
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        if self._on_total_tab:
            if getattr(ctx, "cortes", None):
                self._calcular_total()
        elif getattr(ctx, "cortes", None) and getattr(ctx, "longitud_barra", 0) > 0:
            self._calcular()

    def _on_confirm_costs_toggle(self, checked: bool) -> None:
        prefs = app_config.get()
        prefs.confirm_costs = bool(checked)
        app_config.save(prefs)

    def _on_calculate_clicked(self) -> None:
        """Calculate button. When 'confirm cost configuration' is on, show a
        summary of the cost settings and ask the user to proceed before the
        actual calculation runs."""
        if self.ui.cb_confirm_costs.isChecked():
            cur = self.ui.currency_combo.currentText()
            mode = self.ui.cost_mode_combo.currentText()
            margin = self.ui.e_margen_beneficio.text().strip() or "0"
            scrap = t("yes") if self.ui.cb_retales.isChecked() else t("no")
            summary = (
                f"{t('currency')}: {cur}\n"
                f"{t('cost_mode')}: {mode}\n"
                f"{t('profit_margin')}: {margin} %\n"
                f"{t('distribute_scrap')}: {scrap}"
            )
            box = QMessageBox(self)
            box.setWindowTitle(t("confirm_costs_title"))
            box.setIcon(QMessageBox.Icon.Question)
            box.setText(t("confirm_costs_msg"))
            box.setInformativeText(summary)
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.Yes)
            if box.exec() != QMessageBox.StandardButton.Yes:
                return
        self._calcular()

    def refresh_currency(self) -> None:
        """Apply a currency change live: re-render the price-field labels (which
        embed the symbol, e.g. "Price €/kg") and, if a calculation is already on
        screen, re-render the result cards in the new currency. Guarded so it
        never pops a dialog when there is nothing to compute."""
        self._apply_i18n()
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        if self._on_total_tab:
            if getattr(ctx, "cortes", None):
                self._calcular_total()
        elif getattr(ctx, "cortes", None) and getattr(ctx, "longitud_barra", 0) > 0:
            self._calcular()

    # ── Exports ───────────────────────────────────────────────────────────────

    def _state_for_export(self):
        """Return an AppState ready for export, always combining ALL material
        contexts so the exported document shows the full-job total.

        Cortes from every context are merged into one list; the first context
        that has both cuts and a profile drives perfil/bar-params so the cost
        formulas in exportar_* have real numbers to work with."""
        import copy
        from nestube.context_sync import ensure_material_contexts, effective_barras

        ensure_material_contexts(self._state)
        # Make a shallow copy of the shared state so we can override cortes /
        # perfil without mutating the live state that the UI reads.
        exp = copy.copy(self._state)
        exp.cortes = []
        exp.barras_necesarias = []
        first_profile_set = False
        for ctx in self._state.material_contexts:
            if not ctx.cortes:
                continue
            exp.cortes.extend(ctx.cortes)
            bars = effective_barras(ctx)
            exp.barras_necesarias.extend(bars)
            if not first_profile_set and ctx.perfil is not None:
                exp.perfil = ctx.perfil
                exp.longitud_barra = ctx.longitud_barra
                exp.perdida_corte = ctx.perdida_corte
                exp.margen_tubo = ctx.margen_tubo
                exp.descripcion = ctx.material or self._state.descripcion
                first_profile_set = True
        return exp

    def _export_excel(self) -> None:
        from nestube.export_utils import exportar_excel, _next_number
        initial_dir = self._state.export_path or "."
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_excel"),
            f"NesTube_Resultados_{_next_number(initial_dir, 'xlsx')}.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            exportar_excel(self._state_for_export(), filename=path)
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))

    def _export_pdf(self) -> None:
        from nestube.export_utils import exportar_presupuesto_pdf, _next_number
        initial_dir = self._state.export_path or "."
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_pdf"),
            f"NesTube_Presupuesto_{_next_number(initial_dir, 'pdf')}.pdf",
            "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            exportar_presupuesto_pdf(self._state_for_export(), filename=path)
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))

    def _export_docx(self) -> None:
        from nestube.export_utils import exportar_docx, _next_number
        initial_dir = self._state.export_path or "."
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_docx"),
            f"NesTube_Presupuesto_{_next_number(initial_dir, 'docx')}.docx",
            "Word DOCX (*.docx)",
        )
        if not path:
            return
        try:
            exportar_docx(self._state_for_export(), filename=path)
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))

    def _print(self) -> None:
        try:
            from nestube.export_utils import imprimir
            imprimir(self._state_for_export())
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))

    def _save_split(self, splitter: QSplitter) -> None:
        prefs = app_config.get()
        prefs.split_costes = splitter.sizes()[0]
        app_config.save()

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh_theme(self) -> None:
        # ProfileTiles repaint from live _th in their paintEvent, but the "+"
        # add-tile is a QPushButton whose stylesheet is baked once at build
        # time — without a rebuild it stays frozen at the theme the app
        # started in (the light-mode "invisible add tile" bug). Rebuild the
        # favourites so the add tile picks up the current palette.
        self._rebuild_favorites()
        # Re-tint themed icons (baked pixmaps) for the new palette.
        self.ui.btn_excel.setIcon(themed_icon("excel", _th.TEXT_PRI, 20))
        self.ui.btn_pdf.setIcon(themed_icon("pdf", _th.TEXT_PRI, 20))
        self.ui.btn_docx.setIcon(themed_icon("doc", _th.TEXT_PRI, 20))
        self.ui.btn_print.setIcon(themed_icon("print", _th.TEXT_PRI, 20))
        self.ui.calc_btn.setIcon(themed_icon("gear", "#FFFFFF", 14))
        if hasattr(self, "_mat_search_bar"):
            self._mat_search_bar.refresh_icon()
        # §22: Re-style nesting source label for new theme colours.
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        self._update_nesting_src_lbl(ctx)
        # Section labels (Weight / Pricing / Labour dividers)
        sec_style = (
            f"color:{_th.TEXT_SEC}; font-size:9px; font-weight:bold; letter-spacing:1px;"
            f" padding:4px 0 2px 0; border-bottom:1px solid {_th.BORDER};"
        )
        self.ui.weight_section_lbl.setStyleSheet(sec_style)
        self.ui.pricing_section_lbl.setStyleSheet(sec_style)
        self.ui.labour_section_lbl.setStyleSheet(sec_style)
        # Field captions
        field_lbl_style = f"color:{_th.TEXT_SEC}; font-size:10px;"
        for lbl in (
            self.ui.lbl_espesor, self.ui.lbl_kg_m, self.ui.lbl_peso_esp,
            self.ui.lbl_precio_kg, self.ui.lbl_precio_m,
            self.ui.lbl_precio_barra, self.ui.lbl_margen,
            self.ui.lbl_t_recto, self.ui.lbl_pct_inglete, self.ui.lbl_coste_op,
            self.ui.lbl_currency,
        ):
            lbl.setStyleSheet(field_lbl_style)
        # Results header
        self.ui.results_hdr.setStyleSheet(
            f"color:{_th.ACCENT}; font-weight:bold; font-size:11px; padding:4px 8px;"
        )
        self.update()

    def set_values(self, data: dict) -> None:
        try:
            perfil = ConfigPerfil.from_dict(data)
        except Exception:
            return

        self._state.perfil = perfil
        d = perfil.dimensiones
        m = perfil.material
        mo = perfil.mano_obra

        if d.tipo:
            key = f"builtin:{d.tipo.value}"
            self._select_profile(key)
            dim_map = {
                "diametro": d.diametro,
                "lado_a": d.lado_a,
                "lado_b": d.lado_b,
                "lado_c": d.lado_c,
                "espesor_int_H": d.espesor_int_H,
            }
            for k, val in dim_map.items():
                if k in self._dim_entries and val:
                    self._dim_entries[k].setText(str(val))

        def _set(entry: QLineEdit, val) -> None:
            if entry is not None and val:
                entry.setText(str(val))

        _set(self.ui.e_espesor,         d.espesor)
        _set(self.ui.e_precio_kg,       m.precio_kg)
        _set(self.ui.e_precio_m,        m.precio_m)
        _set(self.ui.e_kg_m,            m.kg_por_m)
        _set(self.ui.e_precio_barra,    m.precio_barra)
        _set(self.ui.e_peso_esp,        m.peso_especifico)
        _set(self.ui.e_t_recto,         mo.tiempo_corte_recto)
        _set(self.ui.e_pct_inglete,     mo.porcentaje_inglete)
        _set(self.ui.e_coste_op,        mo.coste_operario_hora)
        _set(self.ui.e_margen_beneficio, m.margen_beneficio)

        self.ui.cb_macizo.setChecked(bool(d.macizo))
        self.ui.cb_retales.setChecked(bool(m.repartir_retales))
        self._toggle_espesor()
        self._on_kg_m_change()

    def refresh_profile_selector(self) -> None:
        self._rebuild_favorites()
        self._rebuild_profile_combo()

    def sync_subtabs_bar(self) -> None:
        """Rebuild the material sub-tabs so the Costs tab mirrors the shared
        contexts (same names/order as the Nesting & Cuts tabs) — TODO §4.

        The old version only appended missing tabs, so it never picked up
        renames, removals or the active index from another tab. Here we
        rebuild from scratch. The "Total" button is owned separately by
        MaterialSubTabs and is preserved across the rebuild.
        """
        ensure_material_contexts(self._state)
        # Mirror the bar to the model without emitting tab_removed/_added (those
        # mutate material_contexts and would delete the user's jobs/cuts).
        from nestube.naming import context_tab_label
        names = [context_tab_label(ctx, i)
                 for i, ctx in enumerate(self._state.material_contexts)]
        self._subtabs.set_tabs(names, self._state.active_material_index)
        if self._state.material_contexts:
            self._on_total_tab = False

    def set_currency(self, code: str) -> None:
        # Called from the Settings → Currency menu. We update the combo with its
        # signal blocked (to avoid a double refresh) and then refresh the labels
        # and results ourselves so the menu path is as live as the combo path.
        self._state.currency = code
        idx = self.ui.currency_combo.findData(code)
        if idx >= 0:
            self.ui.currency_combo.blockSignals(True)
            self.ui.currency_combo.setCurrentIndex(idx)
            self.ui.currency_combo.blockSignals(False)
        self.refresh_currency()
