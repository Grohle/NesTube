"""
nestube/ui_qt/tab_cortes.py
"Cortes" tab — bar parameters, scrollable cut list, nesting preview.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSizePolicy, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)
from PySide6.QtCore import QPointF

from nestube.i18n import t
from nestube.models import AppState, Corte, MaterialContext
from nestube import app_config, units
from nestube.logic import calcular_barras
from nestube.context_sync import (
    ensure_material_contexts,
    apply_auto_barras,
    effective_barras,
    effective_cutting_height,
    load_context_to_state,
    save_cuts_tab_to_context,
    set_material_selection,
)
from nestube.bevel_geom import (
    corte_to_bevel, vertices_local, profile_section_height,
    profile_section_height_known,
)
from nestube.nesting_viz import compute_nesting_canvas_layout
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.widgets.stock_material_search_bar import StockMaterialSearchBar
from nestube.ui_qt.widgets.material_subtabs import MaterialSubTabs
from nestube.ui_qt.widgets.corte_row import CorteRow
from nestube.ui_qt.forms.ui_tab_cortes import Ui_TabCortes
from nestube.ui_qt.icons import themed_icon


# ── Color palette (mirrors export_utils._PALETTE without tkinter dep) ─────────

_PALETTE = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
    "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
    "#9C755F", "#BAB0AC",
]
_color_cache: dict = {}
_palette_idx: int = 0


def _get_cut_color(key) -> str:
    global _palette_idx
    if key not in _color_cache:
        if _palette_idx < len(_PALETTE):
            _color_cache[key] = _PALETTE[_palette_idx]
            _palette_idx += 1
        else:
            h = hash(str(key)) & 0xFFFFFF
            _color_cache[key] = "#{:06x}".format(h)
    return _color_cache[key]


def _clear_color_cache() -> None:
    global _palette_idx
    _color_cache.clear()
    _palette_idx = 0


# ── Nesting preview widget ────────────────────────────────────────────────────

class NestingPreviewWidget(QWidget):
    """Scrollable nesting preview: bars + pieces + scrap hatching."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state: Optional[AppState] = None
        # _content_h grows with the number of stacked bars (recomputed on paint);
        # it starts at and never falls below 80px so at least one bar row is
        # always visible even before any nesting is calculated.
        self._content_h: int = 80
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)

    def set_state(self, state: AppState) -> None:
        self._state = state
        self.update()
        QTimer.singleShot(50, self.repaint)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(400, max(self._content_h, 80))

    def paintEvent(self, event) -> None:
        # Always run the painting inside a guard that guarantees QPainter.end():
        # an unhandled exception in a paintEvent override leaves the painter
        # active, which makes Qt log "Error calling Python override of
        # QWidget::paintEvent()" and blank the widget. On any failure we fall
        # back to the placeholder instead of crashing the repaint.
        p = QPainter(self)
        try:
            self._do_paint(p)
        except Exception:
            try:
                if p.isActive():
                    self._draw_placeholder(p)
            except Exception:
                pass
        finally:
            if p.isActive():
                p.end()

    def _do_paint(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.fillRect(self.rect(), QColor(_th.BG_CARD))

        state = self._state
        if state is None:
            self._draw_placeholder(p)
            return

        try:
            ensure_material_contexts(state)
            ctx = state.material_contexts[state.active_material_index]
        except Exception:
            self._draw_placeholder(p)
            return

        barras = ctx.barras_necesarias or []
        if not barras:
            self._draw_placeholder(p)
            return

        W = self.width() - 24
        if W < 40:
            return

        default_len = ctx.longitud_barra
        kerf    = max(ctx.perdida_corte, 0.0)
        margin  = max(ctx.margen_tubo, 0.0)
        total_gap = kerf + margin
        MARGIN = 12

        bar_lengths = list(state.nesting_bar_lengths or [])
        while len(bar_lengths) < len(barras):
            bar_lengths.append(default_len)
        if not bar_lengths:
            bar_lengths = [default_len] * len(barras)

        try:
            # Compact preview layout (px): each bar drawn 24px tall, a 12px label
            # band above it, 20px vertical gap between bars, MARGIN side inset.
            # These are the on-screen sizes for this small inline preview — the
            # full interactive scene in the Nesting tab uses its own (mm) metrics.
            layout = compute_nesting_canvas_layout(
                W,
                bar_lengths[:len(barras)],
                ctx.perfil,
                real_proportions=app_config.get().nesting_real_proportions,
                fixed_bar_h_px=24,
                label_h_px=12,
                bar_gap_px=20,
                margin_px=MARGIN,
            )
        except Exception:
            layout = None
        if layout is None:
            self._draw_placeholder(p)
            return

        # Bevel/section height: prefer the user's explicit "Bar height" override
        # (required to draw bevels); fall back to the profile's own height.
        section_h = ctx.nesting_height_override or profile_section_height(ctx.perfil)

        bevel_map: dict = {}
        color_map: dict = {}
        for c in ctx.cortes:
            bevel_map.setdefault(c.largo, c)
            key = (c.descripcion, c.largo)
            if key not in color_map:
                color_map[key] = _get_cut_color(key)

        lbl_font = QFont("IBM Plex Sans", 8, QFont.Weight.Bold)
        num_font = QFont("DejaVu Sans Mono", 7)

        for bar_layout, barra in zip(layout.bars, barras):
            longitud    = bar_layout.bar_length_mm
            px_per_mm   = bar_layout.px_per_mm
            y           = bar_layout.y_top
            bar_h       = bar_layout.bar_height_px
            draw_w      = bar_layout.draw_width_px
            i           = bar_layout.bar_index
            retal       = longitud - sum(barra)
            uso         = sum(barra) / longitud * 100 if longitud > 0 else 0

            # Bar label
            p.setFont(lbl_font)
            p.setPen(QPen(QColor(_th.TEXT_PRI)))
            p.drawText(
                int(MARGIN), int(bar_layout.label_y),
                t("bar_n", n=i + 1),
            )

            # Efficiency label (right-aligned)
            p.setFont(num_font)
            p.setPen(QPen(QColor(_th.TEXT_SEC)))
            eff_text = f"{uso:.1f}%  R{retal:.0f}"
            fm = p.fontMetrics()
            eff_w = fm.horizontalAdvance(eff_text)
            p.drawText(int(MARGIN + W - eff_w), int(bar_layout.label_y), eff_text)

            # Bar background
            p.setPen(QPen(QColor(_th.BORDER), 1))
            p.setBrush(QBrush(QColor(_th.BG_CANVAS)))
            p.drawRect(int(MARGIN), int(y), int(draw_w), int(bar_h))

            # Pieces — draw actual bevel polygon from engine geometry
            x = float(MARGIN)
            for idx, corte_len in enumerate(barra):
                gap_px = total_gap * px_per_mm if idx < len(barra) - 1 else 0.0
                cw = max(corte_len * px_per_mm - gap_px, 1.0)
                c_info = bevel_map.get(corte_len)
                key = (c_info.descripcion, corte_len) if c_info else corte_len
                color = color_map.get(key) or _get_cut_color(key)
                has_bevel = bool(
                    c_info and (c_info.inglete1 or c_info.inglete2)
                    and section_h > 0
                )

                p.setPen(QPen(QColor("#080808"), 1))
                p.setBrush(QBrush(QColor(color)))

                if has_bevel:
                    bvl = corte_to_bevel(c_info)
                    bl, br, tr, tl = vertices_local(bvl, section_h)
                    mn = min(bl[0], tl[0])
                    if mn < -0.001:
                        bl = (bl[0] - mn, bl[1])
                        br = (br[0] - mn, br[1])
                        tr = (tr[0] - mn, tr[1])
                        tl = (tl[0] - mn, tl[1])
                    ext = max(bl[0], br[0], tr[0], tl[0])
                    xs = cw / ext if ext > 0.01 else 1.0
                    ys = bar_h / section_h
                    poly = QPolygonF([
                        QPointF(x + bl[0] * xs, y + bar_h - bl[1] * ys),
                        QPointF(x + br[0] * xs, y + bar_h - br[1] * ys),
                        QPointF(x + tr[0] * xs, y + bar_h - tr[1] * ys),
                        QPointF(x + tl[0] * xs, y + bar_h - tl[1] * ys),
                    ])
                    p.drawPolygon(poly)
                else:
                    p.drawRect(int(x), int(y), int(cw), int(bar_h))

                if cw > 20:
                    p.setFont(num_font)
                    from nestube.ui_qt.nesting_scene import _text_color_for_bg
                    p.setPen(QPen(QColor(_text_color_for_bg(color))))
                    label_text = f"{corte_len:.0f}"
                    label_w = p.fontMetrics().horizontalAdvance(label_text)
                    p.drawText(
                        int(x + cw / 2 - label_w / 2),
                        int(y + bar_h / 2 + p.fontMetrics().ascent() / 2 - 1),
                        label_text,
                    )

                x += cw
                if gap_px > 0:
                    p.setPen(QPen(QColor(_th.BG_HOVER), 1))
                    p.drawLine(int(x), int(y + 2), int(x), int(y + bar_h - 2))
                    x += gap_px

            # Scrap hatching
            if retal > 0.5:
                rw = max(retal * px_per_mm, 1.0)
                self._draw_hatch(p, x, y, x + rw, y + bar_h, _th.TEXT_DIM)

        # Update content height for scroll
        if layout.bars:
            self._content_h = int(layout.bars[-1].y_bottom + 20 + MARGIN)

        # Tell scroll area about new preferred height. Defer to avoid mutating
        # geometry mid-paint; end the painter first (done by the caller's finally,
        # but geometry changes are scheduled, not applied here).
        if self.minimumHeight() != self._content_h:
            new_h = self._content_h
            def _apply_h():
                if self.minimumHeight() != new_h:
                    self.setMinimumHeight(new_h)
                    self.updateGeometry()
            QTimer.singleShot(0, _apply_h)

    def _draw_placeholder(self, p: QPainter) -> None:
        p.setFont(QFont("IBM Plex Sans", 10))
        p.setPen(QPen(QColor(_th.TEXT_DIM)))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, t("press_calculate"))

    @staticmethod
    def _draw_hatch(p: QPainter, x0: float, y0: float, x1: float, y1: float, color: str) -> None:
        p.setPen(QPen(QColor(color), 1))
        w = x1 - x0
        h = y1 - y0
        total = w + h
        step = 6
        for offset in range(step, int(total), step):
            lx0 = x0 + min(offset, w)
            ly0 = y0 + max(0.0, offset - w)
            lx1 = x0 + max(0.0, offset - h)
            ly1 = y0 + min(offset, h)
            p.drawLine(int(lx0), int(ly0), int(lx1), int(ly1))


# ── Tab ───────────────────────────────────────────────────────────────────────

class TabCortes(QWidget):
    """Complete Cortes tab: material subtabs, header, controls, cuts list, nesting preview."""

    def __init__(
        self,
        state: AppState,
        on_state_change: Optional[Callable] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._on_state_change = on_state_change
        self._rows: List[CorteRow] = []
        self._calc_timer = QTimer(self)
        self._calc_timer.setSingleShot(True)
        self._calc_timer.setInterval(800)
        self._calc_timer.timeout.connect(self._auto_refresh_preview)

        # ── Set up UI from .ui form ──────────────────────────────────────
        self.ui = Ui_TabCortes()
        self.ui.setupUi(self)

        # Column stretches not expressible in .ui
        for col in range(4):
            self.ui.header_grid.setColumnStretch(col, 1)

        # Move result_lbl (e.g. "3 bars · 94.2%") out of controls_layout and
        # into a QHBoxLayout beside preview_hdr ("Nesting Preview | ── | metric").
        self.ui.controls_layout.removeWidget(self.ui.result_lbl)
        self.ui.preview_panel_layout.removeWidget(self.ui.preview_hdr)
        _preview_hdr_row = QHBoxLayout()
        _preview_hdr_row.setContentsMargins(0, 0, 0, 0)
        _preview_hdr_row.setSpacing(4)
        _preview_hdr_row.addWidget(self.ui.preview_hdr)
        _preview_hdr_row.addStretch()
        _preview_hdr_row.addWidget(self.ui.result_lbl)
        self.ui.preview_panel_layout.insertLayout(0, _preview_hdr_row)

        # ── Convenience aliases for widgets used heavily in logic ─────────
        self._header_grid = self.ui.header_grid
        self._e_pedido = self.ui.e_pedido
        self._e_oferta = self.ui.e_oferta
        self._e_cliente = self.ui.e_cliente
        self._e_bar_len = self.ui.e_bar_len
        self._e_kerf = self.ui.e_kerf
        self._e_margin = self.ui.e_margin
        self._e_bar_height = self.ui.e_bar_height
        self._result_lbl = self.ui.result_lbl
        self._rows_layout = self.ui.rows_layout
        self._rows_container = self.ui.rows_container
        self._custom_fields_widget = self.ui.custom_fields_widget
        self._custom_fields_layout = self.ui.custom_fields_layout
        self._splitter = self.ui.splitter

        # ── Material subtabs (custom widget, inserted at top) ────────────
        self._subtabs = MaterialSubTabs(has_total=False)
        self._subtabs.before_switch.connect(self._on_before_subtab)
        self._subtabs.tab_changed.connect(self._on_subtab_change)
        self._subtabs.tab_added.connect(self._on_tab_added)
        self._subtabs.tab_removed.connect(self._on_tab_removed)
        self._subtabs.tab_renamed.connect(self._on_tab_renamed)
        self.ui.main_layout.insertWidget(0, self._subtabs)

        # ── Stock/material search bar (custom widget in header) ──────────
        # Single field that searches both the stock inventory and the
        # materials database (fictitious). Picking one selects it for Cuts,
        # Nesting and Costs (TODO §2.2). height=30 matches the order/offer/
        # client line edits beside it.
        self._search_bar = StockMaterialSearchBar(
            placeholder=t("search_placeholder"),
            height=30,
        )
        self._search_bar.selected.connect(self._on_material_selected)
        placeholder_layout = QHBoxLayout(self.ui.mat_ac_placeholder)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.setSpacing(0)
        placeholder_layout.addWidget(self._search_bar)

        # ── NestingPreviewWidget (custom-painted, set as scroll widget) ──
        self._preview = NestingPreviewWidget()
        self.ui.preview_scroll.setWidget(self._preview)

        # ── Style/property fixups not expressible in .ui ─────────────────
        # role="card" makes these QFrames pick up the themed card surface from
        # the global QSS (BG_CARD fill, rounded corners, border); style().polish()
        # re-evaluates the stylesheet so the property takes effect immediately.
        # header_card = the top material/order/client block; controls_card = the
        # Kerf/Margin/Bar-length row with the Calculate button.
        self.ui.header_card.setProperty("role", "card")
        self.ui.header_card.style().polish(self.ui.header_card)
        self.ui.controls_card.setProperty("role", "card")
        self.ui.controls_card.style().polish(self.ui.controls_card)

        # Scoped (object-name) so the transparent rule can't leak into tooltips.
        self.ui.field_btns.setStyleSheet("#field_btns{background:transparent;}")
        self._custom_fields_widget.setObjectName("custom_fields_widget")
        self._custom_fields_widget.setStyleSheet(
            "#custom_fields_widget{background:transparent;}")

        self.ui.add_field_btn.setStyleSheet(
            f"QPushButton {{ color:{_th.TEXT_SEC}; background:transparent; border:none; font-size:10px; }}"
            f"QPushButton:hover {{ color:{_th.ACCENT}; }}"
        )
        self.ui.edit_fields_btn.setStyleSheet(
            f"QPushButton {{ color:{_th.TEXT_SEC}; background:transparent; border:none; font-size:10px; }}"
            f"QPushButton:hover {{ color:{_th.ACCENT}; }}"
        )

        # Section headers ("Cuts" / "Nesting Preview"): 11px bold ACCENT.
        self.ui.cuts_hdr.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold; font-size:11px;")
        self.ui.preview_hdr.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold; font-size:11px;")

        # Numeric param fields → "mono" property selects DejaVu Sans Mono via QSS.
        self._e_bar_len.setProperty("mono", "true")
        self._e_kerf.setProperty("mono", "true")
        self._e_margin.setProperty("mono", "true")
        self._e_bar_height.setProperty("mono", "true")

        # Add-cut = ghost (outline) button; Calculate = accent (orange) button.
        # Both sizes/shapes come from their variant rule in the global QSS.
        self.ui.add_btn.setProperty("variant", "ghost")
        self.ui.add_btn.style().polish(self.ui.add_btn)
        self.ui.calc_btn.setProperty("variant", "accent")
        self.ui.calc_btn.style().polish(self.ui.calc_btn)

        # Result summary ("N bars · XX.X%"): 11px bold ACCENT, transparent bg.
        self._result_lbl.setStyleSheet(f"color:{_th.ACCENT}; font-size:11px; font-weight:bold; background:transparent;")

        # ── Apply translated / dynamic label text ────────────────────────
        self.ui.add_field_btn.setText(f"+ {t('add_field')}")
        self.ui.edit_fields_btn.setText(t("edit_field"))
        self.ui.edit_fields_btn.setIcon(themed_icon("pencil", _th.TEXT_SEC, 14))
        self.ui.edit_fields_btn.setIconSize(QSize(14, 14))
        _lbl_style = f"color:{_th.TEXT_SEC}; font-size:10px; background:transparent;"
        self.ui.lbl_kerf.setText(t("kerf_loss", u=units.u_len()))
        self.ui.lbl_kerf.setStyleSheet(_lbl_style)
        self.ui.lbl_kerf.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.ui.e_kerf.setToolTip(t("tip_kerf"))
        self.ui.lbl_margin.setText(t("tube_margin", u=units.u_len()))
        self.ui.lbl_margin.setStyleSheet(_lbl_style)
        self.ui.lbl_margin.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.ui.e_margin.setToolTip(t("tip_margin"))
        self.ui.lbl_bar_len.setText(t("bar_length", u=units.u_len()))
        self.ui.lbl_bar_len.setStyleSheet(_lbl_style)
        self.ui.lbl_bar_len.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.ui.e_bar_len.setToolTip(t("tip_bar_length"))
        self.ui.lbl_bar_height.setText(t("bar_height", u=units.u_len()))
        self.ui.lbl_bar_height.setStyleSheet(_lbl_style)
        self.ui.lbl_bar_height.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.ui.e_bar_height.setToolTip(t("tip_bar_height"))
        self.ui.add_btn.setText("Cut")
        self.ui.add_btn.setIcon(themed_icon("plus", _th.TEXT_PRI, 16))
        self.ui.add_btn.setIconSize(QSize(16, 16))
        self.ui.add_btn.setFixedHeight(30)
        self.ui.add_btn.setToolTip(t("add_cut"))
        self.ui.calc_btn.setText(t("calculate"))
        self.ui.calc_btn.setIcon(themed_icon("gear", "#FFFFFF", 14))
        self.ui.calc_btn.setIconSize(QSize(14, 14))
        self.ui.calc_btn.setFixedHeight(30)
        self.ui.calc_btn.setToolTip(t("tip_calculate"))
        self.ui.cuts_hdr.setText(t("tab_cuts"))
        self.ui.preview_hdr.setText(t("nesting_preview"))

        # ── Connect signals ──────────────────────────────────────────────
        self._e_pedido.textChanged.connect(self._on_header_change)
        self._e_oferta.textChanged.connect(self._on_header_change)
        self._e_cliente.textChanged.connect(self._on_header_change)
        self._e_bar_len.editingFinished.connect(self._on_bar_params_change)
        self._e_kerf.editingFinished.connect(self._on_bar_params_change)
        self._e_margin.editingFinished.connect(self._on_bar_params_change)
        self._e_bar_height.editingFinished.connect(self._on_bar_params_change)
        self.ui.add_field_btn.clicked.connect(self._add_custom_field)
        self.ui.edit_fields_btn.clicked.connect(self._open_fields_editor)
        self.ui.add_btn.clicked.connect(lambda: self._add_row())
        self.ui.calc_btn.clicked.connect(self._calcular)

        # ── Calculation-system selector (lives only in the Cuts tab) ─────
        # Sets state.calc_system, which the bin-packing helper and the cost
        # calculation (Profiles tab) both read. Items show the human-readable
        # system name; default selection follows the persisted preference.
        for sys_id, key in (("ffd", "calc_system_ffd"),
                            ("bfd", "calc_system_bfd"),
                            ("nfd", "calc_system_nfd")):
            self.ui.calc_combo_cuts.addItem(t(key), userData=sys_id)
        cur_sys = getattr(self._state, "calc_system", "ffd")
        idx_sys = self.ui.calc_combo_cuts.findData(cur_sys)
        if idx_sys >= 0:
            self.ui.calc_combo_cuts.setCurrentIndex(idx_sys)
        self.ui.calc_combo_cuts.setFixedHeight(30)
        self.ui.calc_combo_cuts.setToolTip(t("tip_calc_system"))
        self.ui.calc_combo_cuts.currentIndexChanged.connect(self._on_calc_system_change)
        # Tighten the controls row padding so all widgets fit on one line.
        self.ui.controls_layout.setContentsMargins(8, 4, 8, 4)
        self.ui.controls_layout.setSpacing(6)

        # ── Import/export buttons (left of the optimization selector) ────
        # Download XLSX template + Import XLSX cut list + Export PDF. The
        # actual file actions live at the app level (Export PDF needs the
        # nesting tab / multi-material flow), so these buttons are exposed as
        # attributes and wired by NesTubeApp after construction. They are
        # inserted just before the calc-system combo so they sit to its left.
        # Template: Excel icon + down-arrow (download)
        self.btn_template = QPushButton()
        self.btn_template.setIcon(themed_icon("arrow-down", _th.TEXT_PRI, 14))
        self.btn_template.setIconSize(QSize(14, 14))
        self.btn_template.setToolTip(t("tip_cuts_download_template"))
        # Import: Excel icon + up-arrow (import into app)
        self.btn_import = QPushButton()
        self.btn_import.setIcon(themed_icon("arrow-up", _th.TEXT_PRI, 14))
        self.btn_import.setIconSize(QSize(14, 14))
        self.btn_import.setToolTip(t("tip_cuts_import_xlsx"))
        # Export PDF: pdf icon + export arrow
        self.btn_export_pdf = QPushButton()
        self.btn_export_pdf.setIcon(themed_icon("export", _th.TEXT_PRI, 14))
        self.btn_export_pdf.setIconSize(QSize(14, 14))
        self.btn_export_pdf.setToolTip(t("tip_cuts_export_pdf"))
        # Export XLSX: excel icon + export arrow
        self.btn_export_xlsx = QPushButton()
        self.btn_export_xlsx.setIcon(themed_icon("excel", _th.TEXT_PRI, 14))
        self.btn_export_xlsx.setIconSize(QSize(14, 14))
        self.btn_export_xlsx.setToolTip(t("tip_cuts_export_xlsx"))
        # Export DXF: export cut contours as 2D DXF files. Uses a dedicated
        # "DXF" text-badge icon (a document glyph with the format lettering).
        self.btn_export_dxf = QPushButton()
        self.btn_export_dxf.setIcon(themed_icon("dxf", _th.TEXT_PRI, 18))
        self.btn_export_dxf.setIconSize(QSize(18, 18))
        self.btn_export_dxf.setToolTip(t("tip_cuts_export_dxf"))
        self.btn_export_dxf.clicked.connect(self._export_cut_dxf)
        for b in (self.btn_template, self.btn_import, self.btn_export_pdf,
                  self.btn_export_xlsx, self.btn_export_dxf):
            b.setFixedSize(30, 30)
            b.setProperty("variant", "ghost")
            b.style().polish(b)
        for b in (self.btn_template, self.btn_import, self.btn_export_pdf,
                  self.btn_export_xlsx, self.btn_export_dxf):
            idx = self.ui.controls_layout.indexOf(self.ui.calc_combo_cuts)
            self.ui.controls_layout.insertWidget(idx, b)

        # ── Header alignment: order/offer match the autocomplete height ──
        # Placeholders set via t() (not the .ui defaults) so they follow a live
        # language switch instead of staying in the build-time English.
        self._e_pedido.setFixedHeight(30)
        self._e_pedido.setPlaceholderText(t("order_number"))
        self._e_oferta.setFixedHeight(30)
        self._e_oferta.setPlaceholderText(t("offer_number"))
        self._e_cliente.setFixedHeight(30)
        self._e_cliente.setPlaceholderText(t("client"))

        # "Add field" / "Edit field" are hidden for now (custom-field code
        # is kept, only the entry-point buttons are removed from the header).
        self.ui.field_btns.setVisible(False)

        # ── Splitter setup ───────────────────────────────────────────────
        prefs = app_config.get()
        split_pos = getattr(prefs, "split_cortes", 560)
        self._splitter.setSizes([split_pos, max(200, self.width() - split_pos)])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.splitterMoved.connect(
            lambda pos, _: self._save_split(self._splitter)
        )

        # Splitter gets stretch=1 in the main layout
        self.ui.main_layout.setStretchFactor(self._splitter, 1)

        # Make the controls row horizontally scrollable (§21.6): on a narrow
        # window "Calculate" and the strategy combo were clipped/overlapping.
        self._wrap_controls_scrollable()

        # Load initial state
        self.load_state(state)

    def _wrap_controls_scrollable(self) -> None:
        """Wrap the Kerf/Margin/Bar-length + Calculate controls row in a horizontal
        QScrollArea so its buttons are never clipped on a narrow window (it still
        stretches to fill a wide one)."""
        from PySide6.QtWidgets import QScrollArea, QFrame as _QFrame
        ui = self.ui
        idx = ui.main_layout.indexOf(ui.controls_card)
        if idx < 0:
            return
        scroll = QScrollArea()
        scroll.setObjectName("controls_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(_QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea#controls_scroll{background:transparent;border:0;}")
        ui.main_layout.removeWidget(ui.controls_card)
        scroll.setWidget(ui.controls_card)
        ui.main_layout.insertWidget(idx, scroll)
        self._controls_scroll = scroll
        QTimer.singleShot(0, self._sync_controls_scroll_metrics)

    def _sync_controls_scroll_metrics(self) -> None:
        scroll = getattr(self, "_controls_scroll", None)
        if scroll is None:
            return
        card = self.ui.controls_card
        card.setMinimumWidth(card.minimumSizeHint().width())
        h = card.sizeHint().height()
        sb = scroll.horizontalScrollBar().sizeHint().height()
        scroll.setMinimumHeight(h)
        scroll.setMaximumHeight(h + sb + 2)

    # ── Row management ────────────────────────────────────────────────────────

    def _add_row(self, corte: Optional[Corte] = None) -> CorteRow:
        n = len(self._rows) + 1
        row = CorteRow(numero=n, corte=corte)
        row.changed.connect(self._on_row_change)
        row.deleted.connect(self._delete_row)
        row.tab_from_last.connect(self._advance_from_row)
        row.bevel_requested.connect(lambda r=row: self._validate_bevel_height(r))
        # Insert before the trailing stretch
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
        self._rows.append(row)
        return row

    def _delete_row(self, idx: int) -> None:
        if len(self._rows) <= 1:
            return
        row = self._rows.pop(idx)
        self._rows_layout.removeWidget(row)
        row.deleteLater()
        for i, r in enumerate(self._rows):
            r.set_numero(i + 1)
        self._on_row_change()

    def _advance_from_row(self, idx: int) -> None:
        # Tab on a row's last field moves to the next row, creating one when on
        # the last row, and lands focus on that row's first field so the user
        # can keep typing without reaching for the mouse.
        if idx >= len(self._rows) - 1:
            new_row = self._add_row()
        else:
            new_row = self._rows[idx + 1]
        new_row.focus_first()

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.hide()
            self._rows_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()

    # ── Custom fields ─────────────────────────────────────────────────────────

    def _rebuild_custom_fields(self) -> None:
        # Clear existing (keep stretch at end)
        while self._custom_fields_layout.count() > 1:
            item = self._custom_fields_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        fields = getattr(ctx, "custom_fields", {}) or {}

        if not fields:
            self._custom_fields_widget.setVisible(False)
            return

        self._custom_fields_widget.setVisible(True)
        for key, val in list(fields.items()):
            w = self._make_custom_field_widget(key, val)
            self._custom_fields_layout.insertWidget(self._custom_fields_layout.count() - 1, w)

    def _make_custom_field_widget(self, key: str, val: str) -> QWidget:
        # One user-defined header field: [ key: ][100px input][✕]. Compact row
        # (2px spacing, no margins) so several fit on the custom-fields line.
        w = QWidget()
        w.setObjectName("custom_field_row")
        w.setStyleSheet("#custom_field_row{background:transparent;}")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Caption "key:" — 10px secondary text.
        lbl = QLabel(f"{key}:")
        lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:10px;")
        layout.addWidget(lbl)

        # Value editor: fixed 100×22 so all custom fields line up uniformly.
        entry = QLineEdit(val)
        entry.setFixedWidth(100)
        entry.setFixedHeight(22)
        entry.textChanged.connect(lambda v, k=key: self._update_custom_field(k, v))
        layout.addWidget(entry)

        del_btn = QPushButton()
        del_btn.setIcon(themed_icon("x", _th.DANGER, 12))
        del_btn.setIconSize(QSize(12, 12))
        del_btn.setFixedSize(18, 18)
        del_btn.setStyleSheet("background:transparent; border:none;")
        del_btn.clicked.connect(lambda _, k=key: self._remove_custom_field(k))
        layout.addWidget(del_btn)

        return w

    def _add_custom_field(self) -> None:
        key, ok = QInputDialog.getText(
            self, t("add_field"), t("field_name") if "field_name" in dir() else "Field name:"
        )
        if not ok or not key.strip():
            return
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        if not hasattr(ctx, "custom_fields") or ctx.custom_fields is None:
            ctx.custom_fields = {}
        ctx.custom_fields[key.strip()] = ""
        self._rebuild_custom_fields()

    def _remove_custom_field(self, key: str) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        if hasattr(ctx, "custom_fields") and ctx.custom_fields:
            ctx.custom_fields.pop(key, None)
        self._rebuild_custom_fields()

    def _update_custom_field(self, key: str, value: str) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        if hasattr(ctx, "custom_fields") and ctx.custom_fields is not None:
            ctx.custom_fields[key] = value

    def _open_fields_editor(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        fields = getattr(ctx, "custom_fields", {}) or {}

        dlg = QDialog(self)
        dlg.setWindowTitle(t("edit_field"))
        dlg.setMinimumWidth(320)
        dlg_layout = QVBoxLayout(dlg)

        info_lbl = QLabel("Enter custom field names (one per line):")
        info_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:11px;")
        dlg_layout.addWidget(info_lbl)

        text_edit = QTextEdit()
        text_edit.setPlainText("\n".join(fields.keys()))
        text_edit.setMinimumHeight(120)
        dlg_layout.addWidget(text_edit)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btn_box)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_names = [
                line.strip()
                for line in text_edit.toPlainText().splitlines()
                if line.strip()
            ]
            old_fields = dict(fields)
            new_fields = {}
            for name in new_names:
                new_fields[name] = old_fields.get(name, "")
            if not hasattr(ctx, "custom_fields") or ctx.custom_fields is None:
                ctx.custom_fields = {}
            ctx.custom_fields = new_fields
            self._rebuild_custom_fields()

    # ── Calculation ───────────────────────────────────────────────────────────

    def _calcular(self) -> None:
        try:
            bar_len = float(self._e_bar_len.text() or "0")
        except ValueError:
            bar_len = 0.0
        if bar_len <= 0:
            QMessageBox.warning(self, t("warning"), t("invalid_bar_length"))
            return

        cortes = [r.get_corte() for r in self._rows]
        if any(c is None for c in cortes):
            QMessageBox.warning(self, t("warning"), t("data_error"))
            return
        cortes_valid = [c for c in cortes if c is not None]

        for c in cortes_valid:
            if c.largo > bar_len:
                QMessageBox.warning(
                    self, t("warning"),
                    f"{t('cut_exceeds_bar')}: {c.largo} > {bar_len}",
                )
                return

        try:
            kerf   = float(self._e_kerf.text() or "0")
            margin = float(self._e_margin.text() or "0")
        except ValueError:
            kerf = margin = 0.0

        _clear_color_cache()

        # This method only prepares user-selected parameters for the advanced
        # engine. It must not alter the engine's internal algorithms.
        barras = calcular_barras(
            bar_len, cortes_valid,
            system=getattr(self._state, "calc_system", "ffd"),
            gap=kerf + margin,
        )

        self._state.longitud_barra  = bar_len
        self._state.perdida_corte   = kerf
        self._state.margen_tubo     = margin
        self._state.cortes          = cortes_valid

        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.longitud_barra   = bar_len
        ctx.perdida_corte    = kerf
        ctx.margen_tubo      = margin
        ctx.cortes           = cortes_valid
        apply_auto_barras(self._state, ctx, barras)

        n_bars = len(barras)
        used   = sum(sum(b) for b in barras)
        total  = n_bars * bar_len
        eff    = used / total * 100 if total > 0 else 0
        self._result_lbl.setText(f"{n_bars} {t('bars_abbr')} · {eff:.1f}%")

        self._preview.set_state(self._state)
        self._assign_row_colors()

        if self._on_state_change:
            self._on_state_change()

    def _assign_row_colors(self) -> None:
        for row in self._rows:
            c = row.get_corte()
            if c is not None and c.largo > 0:
                key = (c.descripcion, c.largo)
                row.set_preview_color(_get_cut_color(key))
            else:
                row.set_preview_color(None)

    def _auto_refresh_preview(self) -> None:
        self._preview.set_state(self._state)

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_row_change(self) -> None:
        self._calc_timer.start()

    def _on_header_change(self) -> None:
        self._sync_header()

    def _on_calc_system_change(self, _idx: int) -> None:
        """Persist the chosen bin-packing system and recompute the preview."""
        sys_id = self.ui.calc_combo_cuts.currentData() or "ffd"
        self._state.calc_system = sys_id
        app_config.get().calc_system = sys_id
        app_config.save()
        if self._rows:
            self._calc_timer.start()

    def _validate_bevel_height(self, row: "CorteRow") -> None:
        """A bevel requires an explicit Bar height. If missing, warn and revert."""
        if not self._e_bar_height.text().strip():
            QMessageBox.warning(self, t("warning"), t("bevel_needs_height"))
            row.clear_bevels()
            self._e_bar_height.setFocus()

    def _on_bar_params_change(self) -> None:
        try:
            self._state.longitud_barra = float(self._e_bar_len.text() or "0")
            self._state.perdida_corte  = float(self._e_kerf.text()    or "0")
            self._state.margen_tubo    = float(self._e_margin.text()  or "0")
        except ValueError:
            pass
        try:
            ht = self._e_bar_height.text().strip()
            self._state.nesting_height_override = float(ht) if ht else None
        except ValueError:
            self._state.nesting_height_override = None
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.longitud_barra = self._state.longitud_barra
        ctx.perdida_corte  = self._state.perdida_corte
        ctx.margen_tubo    = self._state.margen_tubo
        ctx.nesting_height_override = self._state.nesting_height_override

    def _on_before_subtab(self, from_idx: int, to_idx: int) -> None:
        self._sync_header()
        save_cuts_tab_to_context(self._state, from_idx, self.collect_cortes())

    def _on_subtab_change(self, idx: int) -> None:
        # Belt-and-suspenders save: before_switch already saved the FROM context,
        # but guard here too in case it fired with stale active_material_index.
        from_idx = self._state.active_material_index
        if from_idx != idx:
            self._sync_header()
            save_cuts_tab_to_context(self._state, from_idx, self.collect_cortes())
        load_context_to_state(self._state, idx)
        self._apply_context_to_ui()

    def _on_tab_added(self, idx: int) -> None:
        # A new sub-tab ("+") is a new independent subjob: create the matching
        # MaterialContext so each tab keeps its own cuts/profile/layout. Without
        # this every Cuts sub-tab pointed at the same context and edits bled
        # across them (the long-standing "subtabs don't work" bug).
        from nestube import app_config as _ac
        while len(self._state.material_contexts) <= idx:
            ctx = MaterialContext()
            _ac.apply_cost_defaults(ctx.perfil)   # §27 seed cost defaults
            self._state.material_contexts.append(ctx)
        ensure_material_contexts(self._state)

    def _on_tab_removed(self, idx: int) -> None:
        # Flush the currently-active tab's UI into its context BEFORE the pop, so a
        # surviving tab's freshly-edited cuts aren't lost when we reload below
        # (deleting another tab must never wipe a survivor's cuts — §27).
        old_active = self._state.active_material_index
        if 0 <= old_active < len(self._state.material_contexts) and old_active != idx:
            self._sync_header()
            save_cuts_tab_to_context(self._state, old_active, self.collect_cortes())
        if idx < len(self._state.material_contexts):
            self._state.material_contexts.pop(idx)
        ensure_material_contexts(self._state)
        # active_index() is now correct (widget shifts it with the list); load that
        # context into the working state before repainting the UI.
        self._state.active_material_index = self._subtabs.active_index()
        load_context_to_state(self._state, self._state.active_material_index)
        self._apply_context_to_ui()

    def _on_tab_renamed(self, idx: int, name: str) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[idx]
        # custom_display_name is what context_tab_label() honours (it wins over
        # the derived profile·material label); ctx.name alone was ignored once a
        # profile was set, so the rename reverted on the next bar rebuild.
        ctx.custom_display_name = name
        ctx.name = name

    def _on_material_selected(self, sel) -> None:
        """Apply a selection from the stock/material search (TODO §2.2).

        Sets profile/material/quality on the active context. For a stock-bar
        selection it also prefills the cost/weight profile and bar length
        (full prefill), so Costs is ready — matching the Use-stock flow.
        """
        from nestube.ui_qt.dialogs.stock_material_search_dialog import SRC_STOCK
        ensure_material_contexts(self._state)
        set_material_selection(
            self._state, sel.profile_name or "", sel.material or "", sel.quality or "",
        )
        ctx = self._state.material_contexts[self._state.active_material_index]

        # Reflect the selection in the search-bar widget. Without this the bar
        # stays empty and the next _sync_header (fired on every tab switch via
        # get_current_state) reads those empty fields back into the context,
        # silently WIPING the profile/material the user just picked. That was
        # the root cause of "selecting in Cuts doesn't reach the other tabs".
        self._search_bar.set_selection(
            sel.profile_name or "", sel.material or "", sel.quality or "")

        # Rename the active sub-tab to "profile · material" so the tab name
        # follows the selection everywhere (mirrors Nesting and Costs).
        label = " · ".join(filter(None, [
            (sel.profile_name or "").strip(), (sel.material or "").strip()]))
        if label:
            ctx.name = label
            self._subtabs.rename_tab(self._state.active_material_index, label)

        if sel.source == SRC_STOCK and sel.stock_bar is not None:
            from nestube.stock_prefill import apply_stock_bar_to_perfil
            from nestube.models import ConfigPerfil
            bar = sel.stock_bar
            apply_stock_bar_to_perfil(ctx.perfil, bar)
            if getattr(bar, "length", 0) and bar.length > 0:
                ctx.longitud_barra = bar.length
                self._state.longitud_barra = bar.length
                self.refresh_bar_length()
            # Propagate the prefilled profile to the shared state so the
            # Costs/Nesting tabs pick it up on their next refresh.
            self._state.perfil = ConfigPerfil.from_dict(ctx.perfil.to_dict())

        # Ask (once per profile) which face is the cutting height, then refresh
        # the read-only bar-height field from the chosen value.
        from nestube.ui_qt.cutting_height import resolve_cutting_height
        resolve_cutting_height(self.window(), self._state)
        self._e_bar_height.blockSignals(True)
        self._apply_bar_height_field(ctx)
        self._e_bar_height.blockSignals(False)

        if self._on_state_change:
            self._on_state_change()

    def _save_split(self, splitter: QSplitter) -> None:
        prefs = app_config.get()
        prefs.split_cortes = splitter.sizes()[0]
        app_config.save()

    def _export_cut_dxf(self) -> None:
        """Export each cut's 2D bevel contour as a separate DXF file."""
        cortes = self.collect_cortes()
        if not cortes:
            QMessageBox.information(self, t("no_cuts_error"), t("no_cuts_to_export"))
            return

        try:
            H = float(self._e_bar_height.text().strip() or "0")
        except ValueError:
            H = 0.0
        if H <= 0:
            QMessageBox.warning(self, t("export_cut_dxf_title"), t("export_cut_dxf_no_height"))
            return

        from nestube.bevel_geom import corte_to_bevel, vertices_local

        if len(cortes) == 1:
            c = cortes[0]
            desc = (c.descripcion or "cut1").replace(" ", "_")
            path, _ = QFileDialog.getSaveFileName(
                self, t("export_cut_dxf_title"),
                f"{desc}.dxf",
                "DXF (*.dxf)",
            )
            if not path:
                return
            piece = corte_to_bevel(c)
            verts = list(vertices_local(piece, H))
            self._write_dxf_polygon(verts, path)
            n_exported = 1
        else:
            directory = QFileDialog.getExistingDirectory(
                self, t("export_cut_dxf_dir")
            )
            if not directory:
                return
            import os
            n_exported = 0
            for i, c in enumerate(cortes):
                piece = corte_to_bevel(c)
                verts = list(vertices_local(piece, H))
                desc = (c.descripcion or f"cut{i + 1}").replace(" ", "_")
                path = os.path.join(directory, f"{i + 1:02d}_{desc}.dxf")
                self._write_dxf_polygon(verts, path)
                n_exported += 1

        QMessageBox.information(
            self, t("export_cut_dxf_title"),
            t("export_cut_dxf_ok").format(n=n_exported),
        )

    @staticmethod
    def _write_dxf_polygon(verts, path: str) -> None:
        import ezdxf
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_lwpolyline(verts, close=True)
        doc.saveas(str(path))

    # ── State sync ────────────────────────────────────────────────────────────

    def _sync_header(self) -> None:
        mat = self._search_bar.material()
        qual = self._search_bar.quality()
        prof = self._search_bar.profile_name()
        self._state.descripcion = mat
        self._state.calidad     = qual
        self._state.pedido      = self._e_pedido.text()
        self._state.oferta      = self._e_oferta.text()
        self._state.cliente     = self._e_cliente.text()
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.profile_name = prof
        ctx.material = mat
        ctx.quality  = qual

    def _apply_bar_height_field(self, ctx) -> None:
        """Auto-fill the bar-height field (read-only) from the selected profile's
        cutting height; editable only when no profile height is known."""
        h_known = effective_cutting_height(self._state) if self._state.perfil else 0
        if h_known and h_known > 0:
            ctx.nesting_height_override = h_known
            self._state.nesting_height_override = h_known
            self._e_bar_height.setText(
                str(int(h_known)) if float(h_known) == int(h_known) else str(h_known))
            self._e_bar_height.setReadOnly(True)
        else:
            h_val = getattr(ctx, "nesting_height_override", None)
            if h_val:
                self._e_bar_height.setText(
                    str(int(h_val)) if float(h_val) == int(h_val) else str(h_val))
            else:
                self._e_bar_height.setText("")
            self._e_bar_height.setReadOnly(False)

    def _apply_context_to_ui(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]

        for w in (self._e_pedido, self._e_oferta, self._e_cliente,
                  self._e_bar_len, self._e_kerf, self._e_margin, self._e_bar_height):
            w.blockSignals(True)

        self._search_bar.set_selection(
            getattr(ctx, "profile_name", "") or "", ctx.material or "", ctx.quality or "")
        self._e_pedido.setText(self._state.pedido or "")
        self._e_oferta.setText(self._state.oferta or "")
        self._e_cliente.setText(self._state.cliente or "")
        self._e_bar_len.setText(str(int(ctx.longitud_barra)) if ctx.longitud_barra else "6000")
        self._e_kerf.setText(str(ctx.perdida_corte) if ctx.perdida_corte else "2.0")
        self._e_margin.setText(str(ctx.margen_tubo) if ctx.margen_tubo else "0")
        self._apply_bar_height_field(ctx)

        for w in (self._e_pedido, self._e_oferta, self._e_cliente,
                  self._e_bar_len, self._e_kerf, self._e_margin, self._e_bar_height):
            w.blockSignals(False)

        self._clear_rows()
        if ctx.cortes:
            for c in ctx.cortes:
                self._add_row(corte=c)
        if not self._rows:
            self._add_row()

        self._rebuild_custom_fields()
        self._preview.set_state(self._state)
        self._assign_row_colors()

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh_theme(self) -> None:
        self._search_bar.refresh_icon()
        self.ui.cuts_hdr.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold; font-size:11px;")
        self.ui.preview_hdr.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold; font-size:11px;")
        self._result_lbl.setStyleSheet(f"color:{_th.ACCENT}; font-size:11px; font-weight:bold; background:transparent;")
        self.ui.add_field_btn.setStyleSheet(
            f"QPushButton {{ color:{_th.TEXT_SEC}; background:transparent; border:none; font-size:10px; }}"
            f"QPushButton:hover {{ color:{_th.ACCENT}; }}"
        )
        self.ui.edit_fields_btn.setStyleSheet(
            f"QPushButton {{ color:{_th.TEXT_SEC}; background:transparent; border:none; font-size:10px; }}"
            f"QPushButton:hover {{ color:{_th.ACCENT}; }}"
        )
        self.ui.edit_fields_btn.setIcon(themed_icon("pencil", _th.TEXT_SEC, 14))
        self.ui.add_btn.setIcon(themed_icon("plus", _th.TEXT_PRI, 14))
        self.btn_template.setIcon(themed_icon("arrow-down", _th.TEXT_PRI, 14))
        self.btn_import.setIcon(themed_icon("arrow-up", _th.TEXT_PRI, 14))
        self.btn_export_pdf.setIcon(themed_icon("export", _th.TEXT_PRI, 14))
        self.btn_export_xlsx.setIcon(themed_icon("excel", _th.TEXT_PRI, 14))
        self.btn_export_dxf.setIcon(themed_icon("dxf", _th.TEXT_PRI, 18))
        self.ui.add_btn.setIcon(themed_icon("plus", _th.TEXT_PRI, 16))
        for row in self._rows:
            row.refresh_theme()
        self.update()

    def load_state(self, state: AppState) -> None:
        self._state = state
        ensure_material_contexts(state)

        # Rebuild the subtab bar from the model WITHOUT emitting tab_removed
        # (which would pop the very contexts we are syncing to — see set_tabs).
        from nestube.naming import context_tab_label
        names = [context_tab_label(ctx, i)
                 for i, ctx in enumerate(state.material_contexts)]
        self._subtabs.set_tabs(names, state.active_material_index)

        self._apply_context_to_ui()

    def collect_cortes(self) -> List[Corte]:
        return [c for c in (r.get_corte() for r in self._rows) if c is not None]

    def refresh_bar_length(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        self._e_bar_len.blockSignals(True)
        self._e_bar_len.setText(str(int(ctx.longitud_barra)) if ctx.longitud_barra else "6000")
        self._e_bar_len.blockSignals(False)

    def sync_subtabs_bar(self) -> None:
        contexts = self._state.material_contexts
        # Mirror the bar to the model without emitting tab_removed/_added (those
        # mutate material_contexts and would corrupt the data we are syncing to).
        from nestube.naming import context_tab_label
        names = [context_tab_label(ctx, i) for i, ctx in enumerate(contexts)]
        self._subtabs.set_tabs(names, self._state.active_material_index)

    def get_current_state(self) -> AppState:
        """Return current AppState with all UI values synced."""
        self._sync_header()
        self._state.cortes = self.collect_cortes()

        try:
            self._state.longitud_barra = float(self._e_bar_len.text() or "0")
            self._state.perdida_corte  = float(self._e_kerf.text() or "0")
            self._state.margen_tubo    = float(self._e_margin.text() or "0")
        except ValueError:
            pass

        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.cortes = list(self._state.cortes)
        ctx.longitud_barra = self._state.longitud_barra
        ctx.perdida_corte = self._state.perdida_corte
        ctx.margen_tubo = self._state.margen_tubo

        return self._state
