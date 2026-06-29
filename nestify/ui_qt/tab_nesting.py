"""
nestify/ui_qt/tab_nesting.py
Interactive nesting tab — manual drag-and-place + auto-nest via QRunnable.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set, Tuple

from PySide6.QtCore import (
    QObject, QPointF, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal, Slot,
)
from PySide6.QtGui import (
    QColor, QKeySequence, QPainter, QPainterPath, QPen, QShortcut,
)
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSizePolicy, QSplitter, QVBoxLayout, QWidget,
)

from nestify.models import AppState, Corte, MaterialContext
from nestify.i18n import t
from nestify import app_config, units
from nestify.context_sync import (
    ensure_material_contexts, load_context_to_state, save_state_to_context,
    set_material_selection,
)
from nestify.bevel_geom import (
    can_place_on_bar, corte_to_bevel, cycle_orientation, max_x_extent,
    min_x_extent, profile_section_height, snap_positions_after_pieces,
)
from nestify.nesting_engine import (
    STRATEGIES, NestingParams, NestingResult, build_nesting_piece,
    nest_advanced_timed, _build_base_polygon,
    _build_all_orientations, _compute_nfp,
)
from shapely.geometry import LineString as _ShLine
from shapely import affinity as _sh_affinity
from nestify.logic import eficiencia_barras
from nestify.ui_qt.nesting_scene import NestingScene, PlacedPieceItem, BAR_GAP_MM, _text_color_for_bg
from nestify.ui_qt.nesting_view import NestingView
from nestify.ui_qt.widgets.material_subtabs import MaterialSubTabs
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.forms.ui_tab_nesting import Ui_TabNesting
from nestify.ui_qt.icons import themed_icon

# Manual-placement tolerances (mm).
#  • _PLACE_TOL_MM: inner-fit / snap-dedup tolerance — pieces this close to a bar
#    edge or each other are treated as just touching, so a piece can sit flush.
#  • _COLLIDE_TOL_MM: how far a reference point may sit inside a neighbour's exact
#    NFP-forbidden interval and still be allowed. It must exceed the engine's own
#    Bottom-Left-Fill acceptance slack (it places pieces up to 0.1 mm inside the
#    true boundary, _bottom_left_fill) plus PyClipper's NFP rounding, so that
#    auto-nested positions are accepted by the manual checker. 0.25 mm is well
#    below one screen pixel at any usable zoom — invisible, never a real overlap.
_PLACE_TOL_MM = 0.1
_COLLIDE_TOL_MM = 0.25


def _safe_unlink(path: str) -> None:
    try:
        import os as _os
        _os.unlink(path)
    except OSError:
        pass


# ── Color palette (same as tab_cortes, no tkinter dep) ────────────────────────
_PALETTE = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
    "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
    "#9C755F", "#BAB0AC",
]
_color_cache: dict = {}
_pal_idx: int = 0


def _get_color(key) -> str:
    global _pal_idx
    if key not in _color_cache:
        if _pal_idx < len(_PALETTE):
            _color_cache[key] = _PALETTE[_pal_idx]; _pal_idx += 1
        else:
            h = hash(str(key)) & 0xFFFFFF
            _color_cache[key] = "#{:06x}".format(h)
    return _color_cache[key]


def _clear_colors():
    global _pal_idx
    _color_cache.clear(); _pal_idx = 0


# ── Local data model (mirrors CTk PlacedPiece) ────────────────────────────────

@dataclass
class PlacedPiece:
    corte: Corte
    bar_index: int
    x_offset: float
    rotation: float = 0.0
    flipped_h: bool = False
    flipped_v: bool = False
    color: str = ""
    poly_local: Optional[List[Tuple[float, float]]] = field(default=None, repr=False)


@dataclass
class PieceInfo:
    corte: Corte
    total_qty: int
    placed_qty: int = 0
    color: str = ""

    @property
    def remaining(self) -> int:
        return max(0, self.total_qty - self.placed_qty)


# ── Auto-nest worker ──────────────────────────────────────────────────────────

class _NestSignals(QObject):
    live_result  = Signal(object, float)  # (NestingResult, bar_len)
    finished     = Signal(object, float)  # (NestingResult|None, bar_len)
    progress_pct = Signal(int)


class _AutoNestWorker(QRunnable):
    def __init__(self, eng_pieces, params: NestingParams, time_limit: Optional[float],
                 cancel_event: threading.Event, bar_len: float) -> None:
        super().__init__()
        self.signals = _NestSignals()
        self._pieces = eng_pieces
        self._params = params
        self._time_limit = time_limit
        self._cancel = cancel_event
        self._bar_len = bar_len
        self._last_pct = 0
        self._last_live = 0.0
        self.setAutoDelete(True)

    def run(self) -> None:
        def _progress_cb(result):
            pct = result.total_placed * 100 // max(1, result.total_pieces)
            self.signals.progress_pct.emit(pct)
            now = time.monotonic()
            if now - self._last_live >= 0.25:
                self._last_live = now
                self.signals.live_result.emit(result, self._bar_len)

        try:
            result = nest_advanced_timed(
                self._pieces, self._params,
                time_limit_sec=self._time_limit,
                stop_event=self._cancel,
                progress_cb=_progress_cb,
            )
        except Exception:
            result = None
        self.signals.finished.emit(result, self._bar_len)


# ── Compact toggle switch ─────────────────────────────────────────────────────

class _CompactToggle(QWidget):
    """Small 44×22 pill toggle with isChecked()/setChecked() API. Text goes outside."""

    toggled = Signal(bool)

    def __init__(self, initial: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._checked = initial
        # Fixed overall size of the pill: 44 px wide × 22 px tall. Everything
        # else (corner radius, knob diameter) is derived from this height.
        self.setFixedSize(44, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, v: bool) -> None:
        if self._checked != v:
            self._checked = v
            self.update()
            self.toggled.emit(v)

    def mousePressEvent(self, event) -> None:
        self.setChecked(not self._checked)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)  # smooth pill edges
        w, h = self.width(), self.height()        # 44 × 22 (from setFixedSize)
        r = h / 2                                 # corner radius = half height → full pill
        # Track: rounded rect filling the whole widget. Fill colour signals
        # state — ACCENT (orange) when on, BG_MID when off; both come from the
        # live theme so they repaint on dark↔light switch.
        track = QPainterPath()
        track.addRoundedRect(0, 0, w, h, r, r)
        p.fillPath(track, QColor(_th.ACCENT if self._checked else _th.BG_MID))
        # Track border: 1 px, ACCENT when on / BORDER when off.
        pen = QPen(QColor(_th.ACCENT if self._checked else _th.BORDER))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(track)
        # Knob: white circle. 3 px padding from the track edge, so its diameter
        # is h-6 = 16 px. Sits left when off, right when on (w-pad-knob_d).
        pad, knob_d = 3, h - 6
        knob_x = (w - pad - knob_d) if self._checked else pad
        knob = QPainterPath()
        knob.addEllipse(knob_x, pad, knob_d, knob_d)
        p.fillPath(knob, QColor("#FFFFFF"))
        # Knob border (1 px BORDER) so the white knob stays visible against the
        # white-ish track in light mode.
        p.setPen(QPen(QColor(_th.BORDER), 1))
        p.drawPath(knob)
        p.end()


def _make_toggle(label_text: str, initial: bool = False) -> tuple:
    """Return (container_widget, _CompactToggle) with label beside toggle.

    Layout: [pill toggle][5 px gap][text label] inside a transparent container
    with no margins, so it drops cleanly into a toolbar row.
    """
    from PySide6.QtWidgets import QHBoxLayout, QLabel
    container = QWidget()
    # Scope the transparent background to THIS widget only. An unscoped
    # "background:transparent" leaks into tooltips shown over the toggle (Qt
    # resolves a tooltip's stylesheet against the hovered widget's ancestors),
    # overriding the app QToolTip rule and making tooltips dark in light mode.
    container.setObjectName("toggle_box")
    container.setStyleSheet("QWidget#toggle_box { background: transparent; }")
    lay = QHBoxLayout(container)
    lay.setContentsMargins(0, 0, 0, 0)   # hug the toggle+label, no padding
    lay.setSpacing(5)                    # 5 px between knob and its caption
    toggle = _CompactToggle(initial)
    lbl = QLabel(label_text)
    # Caption: 10 px primary-text colour; transparent bg so the toolbar shows through.
    lbl.setStyleSheet(f"color:{_th.TEXT_PRI}; font-size:10px; background:transparent;")
    lay.addWidget(toggle)
    lay.addWidget(lbl)
    return container, toggle


# ── Tab ───────────────────────────────────────────────────────────────────────

class TabNesting(QWidget):
    """Interactive nesting tab."""

    _UNDO_MAX = 50

    save_requested = Signal()  # emitted when the user presses Ctrl+S inside the tab

    def __init__(
        self,
        state: AppState,
        on_state_change: Optional[Callable] = None,
        on_kerf_margin_change: Optional[Callable] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._on_state_change = on_state_change
        self._on_kerf_margin_change = on_kerf_margin_change

        # Core data
        self._bars: List[List[PlacedPiece]] = []
        self._pieces: List[PieceInfo] = []
        self._bar_lengths: List[float] = []
        # Per-bar stock id for bars added manually from stock (§16). Parallel to
        # _bars; None where a bar was auto-created or not stock-backed. Kept in
        # sync (padded with None) inside _rebuild_scene.
        self._bar_stock_ids: List[Optional[str]] = []

        # Floating/selection state
        self._selected_piece: Optional[PieceInfo] = None
        self._floating: bool = False
        self._moving_original: Optional[PlacedPiece] = None
        self._moving_original_pi: Optional[PieceInfo] = None
        self._float_flipped_h: bool = False
        self._float_flipped_v: bool = False
        self._snap_preview: Optional[Tuple[int, float]] = None  # (bar_idx, x_mm)
        # Memo cache for _compute_poly_local: building a piece's contour goes
        # through Shapely (~0.3 ms) and the moving piece's polygon is otherwise
        # rebuilt on every collision check — thousands of times per mouse-move
        # during a manual drag, which froze the UI. Keyed by the shape-affecting
        # fields so it stays correct across flips and profile-height changes.
        self._poly_cache: dict = {}
        # Engine-NFP collision caches (manual placement now uses the SAME exact
        # No-Fit-Polygon geometry as auto-nest, so what you see is what collides
        # and a picked-up piece re-drops in its exact slot — no phantom gaps, no
        # bevel overlap). `_engine_piece_cache` memoizes the engine NestingPiece
        # (real + kerf/2-inflated virtual orientations) per shape; `_viable_cache`
        # memoizes the per-bar viable-space polygon so the costly PyClipper NFP
        # union runs once per (orientation, bar layout), not once per mouse-move.
        # `_viable_cache` is cleared in _rebuild_scene whenever _bars mutates.
        self._engine_piece_cache: dict = {}
        self._viable_cache: dict = {}
        self._selected_placed: Optional[PlacedPiece] = None
        self._sel: List[PlacedPiece] = []          # placed pieces selected on the bar
        self._drag_candidate: Optional[PlacedPiece] = None
        self._drag_armed: bool = False             # mouse pressed on a piece, may become a drag
        self._drag_move: bool = False              # current float move started from a drag
        self._press_scene_pos: Optional[QPointF] = None
        self._rubber_active: bool = False          # marquee selection in progress
        self._rubber_origin: Optional[QPointF] = None
        self._has_fitted: bool = False             # view fitted once; later rebuilds keep zoom
        self._highlighted_pps: List[PlacedPiece] = []
        self._height_override: Optional[float] = None
        self._sidebar_filter: str = "all"
        self._filtered_bar: Optional[int] = None
        self._expanded_bars: Set[int] = set()

        # Undo/redo
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._nesting_dirty: bool = False

        # Auto-nest
        self._auto_nesting: bool = False
        self._auto_nest_cancel = threading.Event()
        self._auto_nest_pct: int = 0
        self._auto_nest_timer: Optional[QTimer] = None

        # Scene and view
        self._scene = NestingScene(self)
        self._view = NestingView(self._scene)

        self._scene.piece_pressed.connect(self._on_scene_piece_pressed)
        self._scene.piece_right_pressed.connect(self._on_scene_piece_right_pressed)
        self._scene.background_pressed.connect(self._on_scene_background_pressed)
        self._view.scene_pressed.connect(self._on_view_pressed)
        self._view.scene_moved.connect(self._on_view_moved)
        self._view.scene_released.connect(self._on_view_released)
        self._view.scene_right_pressed.connect(self._on_view_right_pressed)

        # ── Setup UI from .ui file ──
        self.ui = Ui_TabNesting()
        self.ui.setupUi(self)

        # ── Subtabs (inserted at position 0 of main_layout) ──
        self._subtabs = MaterialSubTabs(has_total=False)
        self._subtabs.before_switch.connect(self._on_before_subtab)
        self._subtabs.tab_changed.connect(self._on_subtab_change)
        self._subtabs.tab_added.connect(self._on_tab_added)
        self._subtabs.tab_removed.connect(self._on_tab_removed)
        self._subtabs.tab_renamed.connect(self._on_tab_renamed)
        self.ui.main_layout.insertWidget(0, self._subtabs)

        # ── Insert NestingView into splitter at index 1 ──
        self.ui.splitter.insertWidget(1, self._view)

        # ── Splitter sizing ──
        # Three panes: left pieces list (240px) · centre canvas (1200px) · right
        # bar list (200px). Only the centre has a non-zero stretch factor, so on
        # resize the canvas absorbs the extra space and the side panels keep
        # their widths.
        self.ui.splitter.setSizes([240, 1200, 200])
        self.ui.splitter.setStretchFactor(0, 0)
        self.ui.splitter.setStretchFactor(1, 1)
        self.ui.splitter.setStretchFactor(2, 0)

        # Apply saved panel sides (pieces_side / bars_side) from preferences.
        # Splitter order after insertWidget(1, _view): [pieces_panel, _view, bars_panel].
        # "right" for pieces = move pieces_panel to index 2; "left" for bars = move bars_panel to index 0.
        self._apply_panel_sides()

        # Give the splitter stretch factor 1 in main_layout
        self.ui.main_layout.setStretchFactor(self.ui.splitter, 1)

        # ── Replace bars_scroll + remnant_panel with a vertical splitter ──
        self._bars_splitter = QSplitter(Qt.Orientation.Vertical)
        bars_layout = self.ui.bars_panel_layout
        bars_layout.removeWidget(self.ui.bars_scroll)
        bars_layout.removeWidget(self.ui.remnant_panel)
        self._bars_splitter.addWidget(self.ui.bars_scroll)
        self._bars_splitter.addWidget(self.ui.remnant_panel)
        # Right column stacks the bar list above the remnant panel ~2:1
        # (300:150); neither may be collapsed to zero so both stay reachable.
        self._bars_splitter.setSizes([300, 150])
        self._bars_splitter.setChildrenCollapsible(False)
        bars_layout.addWidget(self._bars_splitter)

        # ── Populate toolbar widgets ──
        self._setup_toolbar()

        # ── Make the toolbar horizontally scrollable (§21.6) ──
        # The two-row toolbar is dense; on a narrow window the right-hand controls
        # (Auto-nest, material, Common cut…) were clipped off the edge. Wrapping it
        # in a horizontal scroll area keeps every control reachable — it stretches
        # to fill a wide window and shows a scrollbar instead of clipping a narrow
        # one.
        self._wrap_toolbar_scrollable()

        # ── Apply initial styles ──
        self._apply_initial_styles()

        # Keyboard shortcuts
        self._setup_shortcuts()

        # Remnant state
        self._show_remnants: bool = False
        self._remnant_names: dict = {}

        self.load_state(state)

    # ── Toolbar scroll wrapper (§21.6) ───────────────────────────────────────

    def _wrap_toolbar_scrollable(self) -> None:
        """Put the dense two-row toolbar inside a horizontal QScrollArea so its
        controls are never clipped on a narrow window. With widgetResizable the
        frame stretches to fill a wide viewport, but respects its own minimum
        width — so when the window is narrower than the toolbar's content a
        horizontal scrollbar appears instead of cutting controls off."""
        from PySide6.QtWidgets import QScrollArea, QFrame as _QFrame
        ui = self.ui
        idx = ui.main_layout.indexOf(ui.toolbar_frame)
        if idx < 0:
            return
        scroll = QScrollArea()
        scroll.setObjectName("toolbar_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(_QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Transparent so it inherits the toolbar's themed background.
        scroll.setStyleSheet("QScrollArea#toolbar_scroll{background:transparent;border:0;}")
        ui.main_layout.removeWidget(ui.toolbar_frame)
        scroll.setWidget(ui.toolbar_frame)
        ui.main_layout.insertWidget(idx, scroll)
        self._toolbar_scroll = scroll
        # Size once the toolbar has its real geometry (after first layout pass).
        QTimer.singleShot(0, self._sync_toolbar_scroll_metrics)

    def _sync_toolbar_scroll_metrics(self) -> None:
        scroll = getattr(self, "_toolbar_scroll", None)
        if scroll is None:
            return
        fr = self.ui.toolbar_frame
        # Floor the frame at its no-clip width so a narrow viewport scrolls.
        need_w = fr.minimumSizeHint().width()
        fr.setMinimumWidth(need_w)
        # Cap the scroll area's height to the toolbar + a thin scrollbar so it
        # never steals vertical space from the canvas.
        h = fr.sizeHint().height()
        sb = scroll.horizontalScrollBar().sizeHint().height()
        scroll.setMinimumHeight(h)
        scroll.setMaximumHeight(h + sb + 2)

    # ── Toolbar population ───────────────────────────────────────────────────

    def _setup_toolbar(self) -> None:
        """Wire up toolbar buttons and insert dynamic widgets into the .ui layout.

        Toolbar geometry model (where each size/position comes from):
        - The toolbar is two QHBoxLayout rows defined in the .ui form
          (``row1_layout`` = actions/toggles, ``row2_layout`` = numeric fields +
          optimisation controls). Static widget sizes (e.g. icon buttons, the
          opt/strategy combos) live in ``forms/ui_tab_nesting.py``; here we only
          set text, tooltips, the ``variant`` style property, signal wiring, and
          insert the widgets that can't be expressed in the .ui form.
        - Heights: icon buttons 30×30 (``variant="icon"`` QSS), combos 30 px tall
          (form minimum), toggles 22 px (``_CompactToggle``).
        - Positions: dynamic widgets are placed with ``insertWidget(index, …)``;
          the index is the slot in that row's layout (counting existing .ui
          widgets), so order changes if the .ui form changes.
        - Colours/fonts come from the theme QSS + the inline ``_lbl_ss`` below.
        """
        ui = self.ui

        # Shared style for the small field captions in row 2 (Kerf/Margin/…):
        # 10 px secondary-text colour, transparent background. Used via
        # setStyleSheet on each QLabel so it tracks the theme on rebuild.
        _lbl_ss = f"color:{_th.TEXT_SEC}; font-size:10px; background:transparent;"

        # Row 1 button texts and connections. save/clear are 30×30 icon buttons
        # (size + square shape from variant="icon" QSS, set below). The glyphs are
        # themed SVG icons (not emojis, which render inconsistently on Linux);
        # they are re-tinted on theme switch in refresh_theme via _refresh_icons.
        ui.save_btn.setIconSize(QSize(16, 16))
        ui.save_btn.setToolTip(t("tip_save"))
        ui.save_btn.clicked.connect(self._save_nesting)

        ui.clear_btn.setIconSize(QSize(16, 16))
        ui.clear_btn.setToolTip(t("tip_clear"))
        ui.clear_btn.clicked.connect(self._clear_nesting)

        # Export dropdown — PDF / DXF / PNG
        from PySide6.QtWidgets import QMenu
        ui.export_btn.setText(t("export"))
        ui.export_btn.setToolTip(t("export"))
        # Wide enough for "Export" + the dropdown arrow (was clipped at 72).
        ui.export_btn.setMinimumWidth(104)
        ui.export_btn.setMaximumWidth(124)
        export_menu = QMenu(ui.export_btn)
        export_menu.addAction(t("export_pdf"), self._export_nesting_pdf)
        export_menu.addAction(t("print_nesting"), self._print_nesting)
        export_menu.addSeparator()
        export_menu.addAction(t("export_dxf"), self._export_nesting_dxf)
        export_menu.addSeparator()
        export_menu.addAction(t("export_nesting_png"), self._export_nesting)
        ui.export_btn.setMenu(export_menu)
        self._export_menu = export_menu
        self._apply_export_menu_theme()
        self._refresh_icons()

        # Mode toggle (Simple↔Advanced): a 44×22 pill + 10px caption built by
        # _make_toggle. Inserted at row1 slot 4 — just after the
        # save/clear/export/sep group (the export button added one slot).
        _mode_ctr, self._mode_switch = _make_toggle(t("nest_mode_advanced"), True)
        self._mode_switch.toggled.connect(self._on_mode_change)
        self._mode_toggle_ctr = _mode_ctr
        ui.row1_layout.insertWidget(4, _mode_ctr)
        self._mode_switch.setToolTip(t("tip_advanced"))

        # Stock toggle — insert after mode toggle (index 5)
        _stock_ctr, self._stock_switch = _make_toggle(t("use_stock"), False)
        self._stock_toggle_ctr = _stock_ctr
        ui.row1_layout.insertWidget(5, _stock_ctr)
        self._stock_switch.setToolTip(t("tip_use_stock"))
        self._stock_switch.toggled.connect(self._on_stock_toggle)

        # Auto/manual stock-bar selection toggle (§16) — sits right of "use
        # stock". OFF (default) = pick bars manually via "Add bar"; ON = let
        # Auto-Nest pull bars from stock automatically. Only meaningful when
        # "use stock" is active, so it is disabled until then.
        _auto_stock_ctr, self._auto_stock_switch = _make_toggle(t("auto_stock"), False)
        self._auto_stock_toggle_ctr = _auto_stock_ctr
        ui.row1_layout.insertWidget(6, _auto_stock_ctr)
        self._auto_stock_switch.setToolTip(t("tip_auto_stock"))
        self._auto_stock_switch.toggled.connect(self._on_auto_stock_toggle)
        _auto_stock_ctr.setEnabled(False)

        # Compact chip that appears right after the toggle when a stock bar is
        # linked — shows "Stock: {bar name}" and dismisses the link on click.
        self._stock_bar_lbl = QLabel("")
        self._stock_bar_lbl.setStyleSheet(
            f"color:{_th.TEXT_DIM}; font-size:10px; background:transparent;"
            f" padding:0 6px; border:1px solid {_th.BORDER}; border-radius:3px;"
        )
        self._stock_bar_lbl.setVisible(False)
        self._stock_bar_lbl.setToolTip(t("use_stock_clear_tip"))
        self._stock_bar_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stock_bar_lbl.mousePressEvent = lambda _e: self._stock_switch.setChecked(False)
        ui.row1_layout.insertWidget(7, self._stock_bar_lbl)

        ui.add_bar_btn.setText(f"+ {t('add_bar')}")
        ui.add_bar_btn.setToolTip(t("tip_add_bar"))
        ui.add_bar_btn.clicked.connect(self._add_bar)

        ui.rem_toolbar_btn.setText(t("remnants"))
        ui.rem_toolbar_btn.setIcon(themed_icon("undo"))
        ui.rem_toolbar_btn.setIconSize(QSize(14, 14))
        ui.rem_toolbar_btn.setToolTip(t("tip_remnants"))
        ui.rem_toolbar_btn.clicked.connect(self._toggle_remnant_panel)

        ui.rotate_left_btn.setText("")
        ui.rotate_left_btn.setIcon(themed_icon("rotate-ccw"))
        ui.rotate_left_btn.setIconSize(QSize(16, 16))
        ui.rotate_left_btn.setToolTip(t("tip_rotate_left"))
        ui.rotate_left_btn.clicked.connect(lambda: self._cycle_orientation(-1))

        ui.flip_v_btn.setText("⇕")
        ui.flip_v_btn.setToolTip(t("tip_flip_v"))
        ui.flip_v_btn.clicked.connect(self._flip_vertical)

        ui.flip_h_btn.setText("⇄")
        ui.flip_h_btn.setToolTip(t("tip_flip_h"))
        ui.flip_h_btn.clicked.connect(self._flip_horizontal)

        ui.rotate_right_btn.setText("")
        ui.rotate_right_btn.setIcon(themed_icon("rotate-cw"))
        ui.rotate_right_btn.setIconSize(QSize(16, 16))
        ui.rotate_right_btn.setToolTip(t("tip_rotate_right"))
        ui.rotate_right_btn.clicked.connect(lambda: self._cycle_orientation(1))

        # Primary accent button (orange, taller). Its accent fill/size come from
        # the QSS variant="accent" rule applied via the .ui form; while a nest is
        # running its text/colour are swapped to the red "■ Stop" state in
        # _run_auto_nest and restored in _on_nest_finished.
        ui.auto_nest_btn.setText(t("auto_nest"))
        ui.auto_nest_btn.setIcon(themed_icon("gear", "#FFFFFF", 14))
        ui.auto_nest_btn.setIconSize(QSize(14, 14))
        ui.auto_nest_btn.setToolTip(t("tip_auto_nest"))
        ui.auto_nest_btn.clicked.connect(self._toggle_auto_nest)
        # Narrower than the .ui's 150px floor: hug the label ("Auto-anidar" +
        # gear icon needs ~130px) and never grow past it. The expanding
        # row1_spacer to its left keeps it pinned flush to the right edge at
        # every window width, so it no longer overflows/clips on narrow windows.
        ui.auto_nest_btn.setMinimumWidth(130)
        ui.auto_nest_btn.setSizePolicy(QSizePolicy.Policy.Maximum,
                                       QSizePolicy.Policy.Fixed)

        # Square icon buttons: crisp, clearly-bounded glyphs. variant="icon" in
        # the theme QSS gives the 30×30 box, centred glyph and hover-accent
        # border; style().polish() re-applies the QSS after the property is set.
        for _btn in (ui.save_btn, ui.clear_btn, ui.rotate_left_btn,
                     ui.flip_v_btn, ui.flip_h_btn, ui.rotate_right_btn):
            _btn.setProperty("variant", "icon")
            _btn.style().polish(_btn)

        # Zoom button (top bar): shows the current zoom as a % of the fit scale
        # and, on click, returns to 100% (fit) and centres the content between
        # the side panels. ghost variant, 28px tall. The label tracks the view's
        # zoom_changed signal; inserted just before the trailing Auto-nest button.
        self._zoom_btn = QPushButton("100%")
        self._zoom_btn.setFixedHeight(30)
        self._zoom_btn.setMinimumWidth(56)
        self._zoom_btn.setProperty("variant", "ghost")
        self._zoom_btn.style().polish(self._zoom_btn)
        self._zoom_btn.setToolTip(t("zoom_pct_tooltip"))
        self._zoom_btn.clicked.connect(self._view.fit_scene)
        self._view.zoom_changed.connect(lambda pct: self._zoom_btn.setText(f"{pct}%"))
        ui.row1_layout.insertWidget(ui.row1_layout.count() - 1, self._zoom_btn)

        # "Sel. Material" button — opens the stock/material search dialog and
        # shows the active subjob's material name when one is selected.
        self._sel_material_btn = QPushButton(t("sel_material"))
        self._sel_material_btn.setFixedHeight(30)
        self._sel_material_btn.setProperty("variant", "ghost")
        self._sel_material_btn.style().polish(self._sel_material_btn)
        self._sel_material_btn.setToolTip(t("tip_sel_material"))
        self._sel_material_btn.clicked.connect(self._open_material_search)
        # Inserted to the right of the auto-mode ("All") dropdown — see below,
        # after _auto_mode_combo is created.

        # Auto-nest mode combo (to the left of the Auto-nest button). Created in
        # code (not the .ui form) so its 30px height is set explicitly here; it is
        # inserted at the second-to-last row1 slot — i.e. just before the trailing
        # Auto-nest button (count()-1).
        #   all       → recompute every piece from scratch (default)
        #   remaining → keep manual placements, nest only pending pieces and
        #               append the result on new bars after the existing ones.
        self._auto_mode_combo = QComboBox()
        self._auto_mode_combo.setMinimumHeight(30)
        self._auto_mode_combo.addItem(t("auto_nest_mode_all"), userData="all")
        self._auto_mode_combo.addItem(t("auto_nest_mode_remaining"), userData="remaining")
        self._auto_mode_combo.setToolTip(t("auto_nest_mode_label"))
        ui.row1_layout.insertWidget(ui.row1_layout.count() - 1, self._auto_mode_combo)
        # The "Sel. material" button + its read-only material box live in ROW 2,
        # pinned to the far right (after row2_spacer) — i.e. directly below the
        # Auto-nest button and to the right of the strategy ("By length") combo.
        # Keeping them out of row1 stops the left cluster from overflowing and
        # clipping auto_nest_btn at normal window widths.
        self._sel_material_display = QLineEdit()
        self._sel_material_display.setReadOnly(True)
        self._sel_material_display.setFixedHeight(30)
        # Flexible width: prefers ~160px but shrinks down to 110px on narrow
        # windows so the row2 cluster never overflows/clips. The expanding
        # row2_spacer keeps the [btn][box] pair pinned to the right edge.
        self._sel_material_display.setMinimumWidth(110)
        self._sel_material_display.setMaximumWidth(160)
        self._sel_material_display.setSizePolicy(QSizePolicy.Policy.Expanding,
                                                 QSizePolicy.Policy.Fixed)
        self._sel_material_display.setPlaceholderText(t("sel_material_none"))
        ui.row2_layout.addWidget(self._sel_material_btn)
        ui.row2_layout.addWidget(self._sel_material_display)

        # Row 2 = numeric placement fields. Each is a [QLabel caption][QLineEdit]
        # pair from the .ui form. Captions use _lbl_ss (10px secondary); the edits
        # carry the "mono" property → monospaced DejaVu Sans Mono via QSS, and
        # commit on editingFinished (focus-out / Enter) into _on_toolbar_params_changed.
        # Field widths come from the .ui form. Label text is localised + unit-suffixed.
        ui.lbl_kerf.setText(f"{t('kerf_loss', u=units.u_len())}")
        ui.lbl_kerf.setStyleSheet(_lbl_ss)
        ui.tb_kerf.setProperty("mono", "true")
        ui.tb_kerf.editingFinished.connect(self._on_toolbar_params_changed)

        ui.lbl_margin.setText(f"{t('tube_margin', u=units.u_len())}")
        ui.lbl_margin.setStyleSheet(_lbl_ss)
        ui.tb_margin.setProperty("mono", "true")
        ui.tb_margin.editingFinished.connect(self._on_toolbar_params_changed)

        ui.lbl_bar_len.setText(f"{t('bar_length', u=units.u_len())}")
        ui.lbl_bar_len.setStyleSheet(_lbl_ss)
        ui.tb_bar_len.setProperty("mono", "true")
        ui.tb_bar_len.editingFinished.connect(self._on_toolbar_params_changed)

        ui.lbl_height.setText(f"{t('bar_height', u=units.u_len())}")
        ui.lbl_height.setStyleSheet(_lbl_ss)
        ui.tb_height.setProperty("mono", "true")
        ui.tb_height.editingFinished.connect(self._on_toolbar_params_changed)

        # Common-cut toggle (pill+caption, 22px). Inserted at row2 slot 8, right
        # after the four field pairs (kerf/margin/bar_len/height = indices 0-7).
        _common_ctr, self._cb_common = _make_toggle(t("common_cut"), False)
        self._common_toggle_ctr = _common_ctr
        ui.row2_layout.insertWidget(8, _common_ctr)
        self._cb_common.setToolTip(t("tip_common_cut"))

        # Snap toggle, default ON. Inserted at row2 slot 9 (just after common-cut).
        _snap_ctr, self._cb_snap = _make_toggle(t("snap_toggle"), True)
        self._snap_toggle_ctr = _snap_ctr
        ui.row2_layout.insertWidget(9, _snap_ctr)
        self._cb_snap.setToolTip(t("tip_snap"))

        # Optimization-level combo (advanced mode). Fixed 96×30 from the .ui form.
        # Labels are built from the user's configured time limits
        # (AppPreferences.opt_time_level_*), so the Optimization Times dialog can
        # refresh them via refresh_opt_menu_labels(). The selected index maps to a
        # time-limit in seconds in _run_auto_nest.
        ui.opt_combo.setToolTip(t("tip_opt_level"))
        self.refresh_opt_menu_labels()

        _STRATEGY_LABELS = {
            "length": "strat_length",
            "nfp_compact": "strat_nfp_compact",
            "remnants": "strat_remnants",
            "symmetry": "strat_symmetry",
            "min_length": "strat_min_length",
        }
        ui.strategy_combo.setToolTip(t("tip_strategy"))
        for s in STRATEGIES:
            ui.strategy_combo.addItem(t(_STRATEGY_LABELS.get(s, s)), userData=s)
        # Let the strategy combo grow to show full strategy names (was clipped).
        ui.strategy_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Keep the status lead in sync with the selected strategy (advanced mode).
        ui.strategy_combo.currentIndexChanged.connect(lambda _i: self._update_status())

        # Calculation-system combo for SIMPLE mode (1D best-fitting): FFD/BFD/NFD.
        # It sits right after the strategy combo and is shown only in simple mode
        # (advanced mode shows opt-time + strategy instead — see _update_mode_controls).
        self._calc_combo = QComboBox()
        self._calc_combo.setMinimumHeight(30)
        self._calc_combo.setToolTip(t("tip_calc_system"))
        for sysk in ("ffd", "bfd", "nfd"):
            self._calc_combo.addItem(t(f"calc_system_{sysk}"), userData=sysk)
        cur_sys = (getattr(self._state, "calc_system", "ffd") or "ffd").lower()
        ci = self._calc_combo.findData(cur_sys)
        if ci >= 0:
            self._calc_combo.setCurrentIndex(ci)
        self._calc_combo.currentIndexChanged.connect(self._on_calc_system_change)
        _sidx = ui.row2_layout.indexOf(ui.strategy_combo)
        ui.row2_layout.insertWidget(_sidx + 1, self._calc_combo)
        # Show the controls that match the initial mode.
        self._update_mode_controls()

        # Delete / Remove buttons in info bar
        ui.delete_btn.setText(t("delete_from_bar"))
        ui.delete_btn.setFixedHeight(30)
        ui.delete_btn.clicked.connect(self._delete_selected_placed)
        ui.remove_btn.setText(t("remove_permanently"))
        ui.remove_btn.setFixedHeight(30)
        ui.remove_btn.clicked.connect(self._remove_piece_permanently)

        # Filter buttons (All / Complete / Pending). Heights set here; colours are
        # driven by _update_filter_btn_styles so the ACTIVE filter is highlighted.
        ui.filter_all_btn.setText(t("sidebar_filter_all"))
        ui.filter_all_btn.setFixedHeight(40)
        ui.filter_all_btn.clicked.connect(lambda: self._set_sidebar_filter("all"))

        ui.filter_complete_btn.setText(t("sidebar_filter_complete"))
        ui.filter_complete_btn.setFixedHeight(40)
        ui.filter_complete_btn.clicked.connect(lambda: self._set_sidebar_filter("complete"))

        ui.filter_incomplete_btn.setText(t("sidebar_filter_incomplete"))
        ui.filter_incomplete_btn.setFixedHeight(40)
        ui.filter_incomplete_btn.clicked.connect(lambda: self._set_sidebar_filter("incomplete"))
        self._update_filter_btn_styles()

        # Bars panel header buttons
        ui.show_all_btn.setText(t("show_all_bars"))
        ui.show_all_btn.setStyleSheet("font-size:9px;")
        ui.show_all_btn.clicked.connect(self._show_all_bars)

        # Remnant panel widgets
        ui.rem_title.setText(t("generate_remnants_btn").upper())
        ui.rem_min_lbl.setText(t("min_length_label", u="mm"))
        ui.remnant_min_entry.setProperty("mono", "true")
        ui.remnant_min_entry.setToolTip(t("tip_rem_min"))
        ui.rem_margin_lbl.setText(t("tube_margin", u="mm"))
        ui.rem_margin_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        ui.rem_margin_entry.setProperty("mono", "true")
        ui.rem_margin_entry.setText("0")
        ui.rem_margin_entry.setToolTip(t("tip_rem_margin"))
        ui.rem_refresh_btn.setText("")
        ui.rem_refresh_btn.setIcon(themed_icon("rotate-cw"))
        ui.rem_refresh_btn.setIconSize(QSize(14, 14))
        ui.rem_refresh_btn.setToolTip(t("tip_rem_refresh"))
        ui.rem_refresh_btn.clicked.connect(self._refresh_remnants)
        ui.rem_apply_btn.setText(t("apply"))
        ui.rem_apply_btn.setIcon(themed_icon("check"))
        ui.rem_apply_btn.setIconSize(QSize(14, 14))
        ui.rem_apply_btn.setToolTip(t("tip_rem_apply"))
        ui.rem_apply_btn.clicked.connect(self._apply_remnants_to_stock)

        # Extra actions (not in the .ui form): clear the current generated
        # selection, and delete all remnants of this material from stock.
        _rem_actions = QWidget(ui.remnant_panel)
        _rem_actions_l = QVBoxLayout(_rem_actions)
        _rem_actions_l.setContentsMargins(0, 2, 0, 2)
        _rem_actions_l.setSpacing(4)
        self._rem_clear_btn = QPushButton(t("rem_clear_selection"))
        self._rem_clear_btn.setMinimumHeight(28)
        self._rem_clear_btn.setProperty("variant", "ghost")
        self._rem_clear_btn.setToolTip(t("tip_rem_clear_selection"))
        self._rem_clear_btn.clicked.connect(self._clear_remnant_selection)
        self._rem_delete_all_btn = QPushButton(t("rem_delete_all"))
        self._rem_delete_all_btn.setMinimumHeight(28)
        self._rem_delete_all_btn.setProperty("variant", "danger")
        self._rem_delete_all_btn.setToolTip(t("tip_rem_delete_all"))
        self._rem_delete_all_btn.clicked.connect(self._delete_all_remnants)
        _rem_actions_l.addWidget(self._rem_clear_btn)
        _rem_actions_l.addWidget(self._rem_delete_all_btn)
        ui.remnant_panel_layout.addWidget(_rem_actions)
        # The two extra buttons add ~68 px; override the .ui minimum so the panel
        # is tall enough and children don't spill outside / overlap.
        ui.remnant_panel.setMinimumHeight(220)

    # ── Initial styles ───────────────────────────────────────────────────────

    def _apply_initial_styles(self) -> None:
        # Per-widget colours/fonts applied in code (the layout/sizes live in the
        # .ui form). All colours read from _th.* so refresh_theme() can re-run this
        # on a dark↔light switch. Pattern: panel frames get BG_CARD with a hairline
        # BORDER edge; section titles are 10px bold ACCENT; captions are 9-10px
        # TEXT_SEC. Font sizes here set text height for each label.
        ui = self.ui
        # Toolbar frame: card background + 1px bottom border separating it from
        # the canvas. The two rows and the info bar are transparent (inherit it).
        ui.toolbar_frame.setStyleSheet(
            f"QFrame{{background:{_th.BG_CARD};border-bottom:1px solid {_th.BORDER};}}")
        # Scope to the widget (object-name selector) so the transparent rule
        # doesn't leak into tooltips shown over toolbar children (which would
        # make them dark in light mode).
        ui.toolbar_row1.setStyleSheet("#toolbar_row1{background:transparent;}")
        ui.toolbar_row2.setStyleSheet("#toolbar_row2{background:transparent;}")
        ui.info_bar.setStyleSheet("#info_bar{background:transparent;}")
        # Fixed height so the bar never grows when the Remove/Delete buttons
        # (24px) appear; 4px top/bottom keeps the buttons from being clipped.
        ui.info_bar.setFixedHeight(32)
        ui.info_bar_layout.setContentsMargins(8, 4, 8, 4)

        # Static ESC hint — added once, restyles on every theme refresh.
        if not hasattr(self, '_esc_hint_lbl'):
            self._esc_hint_lbl = QLabel("Esc: deselect")
            idx = ui.info_bar_layout.indexOf(ui.delete_btn)
            ui.info_bar_layout.insertWidget(idx, self._esc_hint_lbl)
        self._esc_hint_lbl.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:9px;")

        # Vertical separators between toolbar groups: BORDER-coloured 1px rules.
        for sep in (ui.sep1, ui.sep2, ui.sep3, ui.sep4):
            sep.setStyleSheet(f"color:{_th.BORDER};")

        # Auto-nest accent button: orange fill, 4px radius,
        # darker ACCENT_HVR on hover. (This is the idle state; _run_auto_nest
        # swaps it to the red Stop style while running.)
        ui.auto_nest_btn.setStyleSheet(
            f"QPushButton {{background:{_th.ACCENT}; color:#FFFFFF; border-radius:4px; font-weight:bold;}}"
            f"QPushButton:hover {{background:{_th.ACCENT_HVR};}}"
        )
        ui.qty_lbl.setStyleSheet(f"color:{_th.ACCENT}; font-size:11px;")     # accent count, 11px
        ui.status_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:10px;")  # status line, 10px secondary

        # Pieces panel (left): card-bg header, 10px bold ACCENT title.
        ui.pieces_hdr_frame.setStyleSheet(f"background:{_th.BG_CARD};")
        ui.sidebar_title.setText(t("pieces_remaining", n=0).upper())
        ui.sidebar_title.setStyleSheet(f"color:{_th.ACCENT}; font-size:10px; font-weight:bold;")

        # Bars panel (right): same header treatment as the pieces panel.
        ui.bars_hdr_frame.setStyleSheet(f"background:{_th.BG_CARD};")
        ui.bars_hdr_title.setText(t("bar_list_panel").upper())
        ui.bars_hdr_title.setStyleSheet(f"color:{_th.ACCENT}; font-size:10px; font-weight:bold;")

        # Remnant panel (bottom of the bars splitter): card bg + 1px TOP border to
        # separate it from the bar list above; 9px title/captions (compact panel).
        ui.remnant_panel.setStyleSheet(
            f"QFrame{{background:{_th.BG_CARD};border-top:1px solid {_th.BORDER};}}")
        ui.rem_title.setStyleSheet(f"color:{_th.ACCENT}; font-size:9px; font-weight:bold;")
        ui.rem_min_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        ui.remnant_list_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        ui.rem_apply_btn.setStyleSheet(
            f"QPushButton {{background:{_th.ACCENT}; color:#FFFFFF; border-radius:4px; font-size:10px;}}"
            f"QPushButton:hover {{background:{_th.ACCENT_HVR};}}"
        )

    # ── Sidebar refresh ───────────────────────────────────────────────────────

    def _refresh_sidebar(self) -> None:
        self._refresh_left_sidebar()
        self._refresh_right_sidebar()

    def _refresh_left_sidebar(self) -> None:
        while self.ui.sidebar_layout.count() > 1:
            item = self.ui.sidebar_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        remaining = sum(pi.remaining for pi in self._pieces)
        self.ui.sidebar_title.setText(f"{t('pieces_remaining', n=remaining).upper()}")

        filt = self._sidebar_filter
        visible = [pi for pi in self._pieces if (
            filt == "all"
            or (filt == "complete" and pi.remaining == 0)
            or (filt == "incomplete" and pi.remaining > 0)
        )]

        if not visible:
            hint = QLabel(t("select_piece_hint"))
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setWordWrap(True)
            hint.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:10px;")
            self.ui.sidebar_layout.insertWidget(0, hint)
            return

        for pi in visible:
            row = self._make_piece_row(pi)
            self.ui.sidebar_layout.insertWidget(self.ui.sidebar_layout.count() - 1, row)

    def _make_piece_row(self, pi: PieceInfo) -> QWidget:
        # One row in the left "pieces remaining" list. Layout: [swatch][name/qty].
        w = QWidget()
        w.setMinimumHeight(36)              # row height (two stacked text lines fit)
        done = (pi.remaining == 0)
        # Fully-placed rows get a green SUCCESS_BG wash (4px rounded); pending rows
        # are transparent. Colour is theme-driven (rebuilt on theme switch).
        w.setStyleSheet(
            f"QWidget{{background:{_th.SUCCESS_BG if done else 'transparent'};border-radius:4px;}}"
        )
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 2, 4, 2)   # tight padding inside the row
        layout.setSpacing(4)                     # gap between swatch and text

        # Colour swatch: a 14px-wide ■ glyph tinted with the piece's cut colour
        # (11px so it reads as a solid square next to 10px text).
        swatch = QLabel("■")
        swatch.setStyleSheet(f"color:{pi.color}; font-size:11px;")
        swatch.setFixedWidth(14)
        layout.addWidget(swatch)

        # Info block: two stacked labels (name above, qty below) with no spacing.
        info_w = QWidget()
        info_w.setObjectName("nest_info_w")
        info_w.setStyleSheet("#nest_info_w{background:transparent;}")
        info_l = QVBoxLayout(info_w)
        info_l.setContentsMargins(0, 0, 0, 0)
        info_l.setSpacing(0)

        # Line 1: description (or length fallback), 10px primary text.
        desc = pi.corte.descripcion or f"{pi.corte.largo:.0f} mm"
        lbl_name = QLabel(desc)
        lbl_name.setStyleSheet(f"color:{_th.TEXT_PRI}; font-size:10px;")
        info_l.addWidget(lbl_name)

        # Line 2: "<largo> mm ×<remaining>/<total>", 9px secondary text.
        total = pi.total_qty
        placed = pi.placed_qty
        rem = pi.remaining
        lbl_qty = QLabel(f"{pi.corte.largo:.0f} mm  ×{rem}/{total}")
        lbl_qty.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        info_l.addWidget(lbl_qty)

        layout.addWidget(info_w, 1)   # stretch=1 → info block fills the row width

        # Child labels would otherwise eat the click (QLabel accepts mouse press),
        # so a click on the swatch/text never reached the row's handler — only the
        # padding worked. Make the children transparent to mouse events so the
        # whole row is clickable.
        for _child in (swatch, info_w, lbl_name, lbl_qty):
            _child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        w.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        w.customContextMenuRequested.connect(lambda pos, p=pi: self._show_sidebar_context_menu(p, w.mapToGlobal(pos)))

        if not done:
            w.setCursor(Qt.CursorShape.PointingHandCursor)
            w.mousePressEvent = lambda e, p=pi: self._select_piece(p)
        else:
            w.setCursor(Qt.CursorShape.PointingHandCursor)
            w.mousePressEvent = lambda e, p=pi: self._highlight_all_instances(p)

        return w

    def _refresh_right_sidebar(self) -> None:
        while self.ui.bars_layout.count() > 1:
            item = self.ui.bars_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        for bar_idx, bar in enumerate(self._bars):
            if not bar:
                continue
            section = self._make_bar_section(bar_idx, bar)
            self.ui.bars_layout.insertWidget(self.ui.bars_layout.count() - 1, section)

    def _make_bar_section(self, bar_idx: int, pieces: List[PlacedPiece]) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(1)

        # Collapsible "Bar N (count)" header (tree-style). 24px tall, 3px rounded.
        # Background flips to ACCENT when this bar is the filtered/active one,
        # otherwise BG_MID. Clicking it toggles filter via _on_bar_header_click.
        is_filtered = (self._filtered_bar == bar_idx)
        hdr = QFrame()
        hdr.setFixedHeight(24)
        hdr.setStyleSheet(
            f"QFrame{{background:{_th.ACCENT if is_filtered else _th.BG_MID};border-radius:3px;}}"
        )
        hdr.setCursor(Qt.CursorShape.PointingHandCursor)
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(4, 0, 4, 0)
        # Chevron shows expand state (open / collapsed), then the bar label.
        expanded = bar_idx in self._expanded_bars
        chevron_icon = themed_icon("chevron-down" if expanded else "chevron-right",
                                   _th.TEXT_PRI, 12)
        chevron = QLabel()
        chevron.setPixmap(chevron_icon.pixmap(QSize(12, 12)))
        chevron.setFixedSize(14, 14)
        hdr_l.addWidget(chevron)
        hdr_l.addWidget(QLabel(f"Bar {bar_idx + 1}  ({len(pieces)})"))
        hdr_l.addStretch()   # push label group left, reorder buttons go right

        # Reorder buttons (§3.6): move this bar up/down in the visual order only.
        # Disabled at the ends.
        fg = _th.TEXT_PRI if not is_filtered else _text_color_for_bg(_th.ACCENT)
        fg_dim = _th.TEXT_DIM
        visible = self._visible_bar_indices()
        vpos = visible.index(bar_idx) if bar_idx in visible else -1
        for icon_name, direction, enabled in (
            ("arrow-up", -1, vpos > 0),
            ("arrow-down", +1, 0 <= vpos < len(visible) - 1),
        ):
            btn = QPushButton()
            btn.setIcon(themed_icon(icon_name, fg if enabled else fg_dim, 12))
            btn.setIconSize(QSize(12, 12))
            btn.setFixedSize(18, 18)
            btn.setEnabled(enabled)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(t("move_bar_up") if direction < 0 else t("move_bar_down"))
            btn.setStyleSheet(
                "QPushButton{background:transparent;border:none;padding:0;}"
                f"QPushButton:hover{{background:{_th.BG_HOVER};border-radius:3px;}}"
            )
            btn.clicked.connect(lambda _c=False, bi=bar_idx, d=direction: self._move_bar(bi, d))
            hdr_l.addWidget(btn)

        # Clicking the header background (not a button) toggles the filter view.
        hdr.mousePressEvent = lambda e, bi=bar_idx: self._on_bar_header_click(bi)
        vbox.addWidget(hdr)

        if expanded:
            from collections import Counter
            counts: Counter = Counter()
            for pp in pieces:
                counts[(pp.corte.descripcion, pp.corte.largo, pp.color)] += 1
            for (desc, largo, color), cnt in counts.items():
                row_w = QWidget()
                row_w.setObjectName("nest_legend_row")
                row_w.setStyleSheet("#nest_legend_row{background:transparent;}")
                row_l = QHBoxLayout(row_w)
                row_l.setContentsMargins(4, 1, 4, 1)
                row_l.setSpacing(4)
                swatch = QLabel("■")
                swatch.setStyleSheet(f"color:{color}; font-size:11px;")
                swatch.setFixedWidth(14)
                row_l.addWidget(swatch)
                lbl = QLabel(f"{desc or f'{largo:.0f}mm'}  ×{cnt}")
                lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
                row_l.addWidget(lbl, 1)
                row_w.setCursor(Qt.CursorShape.PointingHandCursor)
                row_w.mousePressEvent = lambda e, bi=bar_idx, d=desc, l=largo: self._highlight_in_bar(bi, d, l)
                vbox.addWidget(row_w)

        return w

    # ── Piece selection & floating ────────────────────────────────────────────

    def _select_piece(self, pi: PieceInfo) -> None:
        if pi.remaining <= 0:
            return
        self._selected_piece = pi
        self._floating = True
        self._float_flipped_h = False
        self._float_flipped_v = False
        self._snap_preview = None
        self._view.setCursor(Qt.CursorShape.CrossCursor)
        self.ui.qty_lbl.setText(
            f"{pi.corte.descripcion or ''} {pi.corte.largo:.0f} mm  {t('pieces_left', n=pi.remaining)}"
        )
        self.ui.qty_lbl.setVisible(True)
        self._update_left_pan()

    def _cancel_floating(self) -> None:
        if self._moving_original is not None:
            self._restore_moving_piece()
        self._floating = False
        self._selected_piece = None
        self._moving_original = None
        self._moving_original_pi = None
        self._snap_preview = None
        self._scene.hide_float_preview()
        self._view.setCursor(Qt.CursorShape.ArrowCursor)
        self.ui.qty_lbl.setVisible(False)
        self._update_left_pan()

    def _pick_up_placed(self, pp: PlacedPiece) -> None:
        pi = next((p for p in self._pieces if p.corte is pp.corte or (
            p.corte.descripcion == pp.corte.descripcion and p.corte.largo == pp.corte.largo
        )), None)
        if pi is None:
            return
        self._push_undo()
        self._bars[pp.bar_index] = [p for p in self._bars[pp.bar_index] if p is not pp]
        pi.placed_qty = max(0, pi.placed_qty - 1)
        self._moving_original = pp
        self._moving_original_pi = pi
        self._selected_piece = pi
        self._floating = True
        self._float_flipped_h = pp.flipped_h
        self._float_flipped_v = pp.flipped_v
        self._snap_preview = None
        self._selected_placed = None
        self._sel = []
        self._update_delete_btn_visibility()
        self._view.setCursor(Qt.CursorShape.CrossCursor)
        self.ui.qty_lbl.setText(
            f"{pi.corte.descripcion or ''} {pi.corte.largo:.0f} mm  {t('moving_piece')}"
        )
        self.ui.qty_lbl.setVisible(True)
        self._rebuild_scene()
        self._refresh_sidebar()

    def _restore_moving_piece(self) -> None:
        pp = self._moving_original
        pi = self._moving_original_pi
        if pp is None or pi is None:
            return
        while pp.bar_index >= len(self._bars):
            self._bars.append([])
        self._bars[pp.bar_index].append(pp)
        pi.placed_qty += 1

    # ── Scene event handlers ──────────────────────────────────────────────────

    def _on_scene_piece_pressed(self, item) -> None:
        # Pressing a placed piece arms a potential drag; whether it becomes a
        # move (drag past a threshold) or a selection (click without moving) is
        # decided in the move/release handlers. We do NOT pick it up here, so a
        # plain click selects instead of immediately detaching the piece.
        pp = item.pp_ref
        if pp is None or self._floating:
            return
        self._drag_candidate = pp
        self._drag_armed = True
        self._drag_move = False

    def _on_scene_piece_right_pressed(self, item) -> None:
        pp = item.pp_ref
        if pp is None:
            return
        self._selected_placed = pp
        if pp not in self._sel:
            self._sel = [pp]
            self._update_delete_btn_visibility()
            self._rebuild_scene()
        self._show_piece_context_menu(pp)

    def _on_scene_background_pressed(self, scene_pos: QPointF) -> None:
        if self._floating and self._selected_piece:
            self._place_floating_piece(scene_pos)

    def _on_view_pressed(self, scene_pos: QPointF) -> None:
        # While carrying a piece (from the sidebar or a drag), a click places it.
        if self._floating and self._selected_piece:
            self._place_floating_piece(scene_pos)
            return
        self._press_scene_pos = scene_pos
        # If a placed piece is under the cursor, its own press handler arms the
        # drag/selection — don't clear the selection or reset the zoom here.
        from PySide6.QtGui import QTransform
        hit = self._scene.itemAt(scene_pos, QTransform())
        if isinstance(hit, PlacedPieceItem):
            return
        # Empty space: begin a marquee (rubber-band) selection. The actual
        # select/clear happens on release, so a plain click still deselects
        # while a drag selects everything enclosed.
        self._rubber_active = True
        self._rubber_origin = scene_pos

    def _on_view_moved(self, scene_pos: QPointF) -> None:
        # Marquee selection: update the rubber-band rectangle as the cursor moves.
        if self._rubber_active and self._rubber_origin is not None:
            from PySide6.QtCore import QRectF
            self._scene.show_rubber_band(QRectF(self._rubber_origin, scene_pos))
            return
        # Promote an armed press into a move once the cursor travels past a
        # small threshold (≈5 px on screen, independent of zoom).
        if self._drag_armed and not self._floating and self._drag_candidate is not None:
            if self._press_scene_pos is not None:
                thr = 5.0 / max(self._view.zoom_level(), 0.01)
                dx = scene_pos.x() - self._press_scene_pos.x()
                dy = scene_pos.y() - self._press_scene_pos.y()
                if (dx * dx + dy * dy) ** 0.5 > thr:
                    pp = self._drag_candidate
                    self._drag_armed = False
                    self._drag_move = True
                    self._pick_up_placed(pp)
        if self._floating and self._selected_piece:
            self._update_float_preview(scene_pos)

    def _on_view_released(self, scene_pos: QPointF) -> None:
        # Finish a marquee selection started on empty space.
        if self._rubber_active:
            self._rubber_active = False
            self._scene.hide_rubber_band()
            origin = self._rubber_origin
            self._rubber_origin = None
            from PySide6.QtWidgets import QApplication
            additive = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)
            thr = 4.0 / max(self._view.zoom_level(), 0.01)
            if origin is not None and (
                abs(scene_pos.x() - origin.x()) > thr or abs(scene_pos.y() - origin.y()) > thr
            ):
                from PySide6.QtCore import QRectF
                hits = self._scene.pieces_in_rect(QRectF(origin, scene_pos))
                if not additive:
                    self._sel = []
                for pp in hits:
                    if pp not in self._sel:
                        self._sel.append(pp)
                self._selected_placed = self._sel[-1] if self._sel else None
                self._update_delete_btn_visibility()
                self._rebuild_scene()
            elif not additive and self._sel:
                # A plain click on empty space clears the selection.
                self._clear_placed_selection()
            return
        # End of a drag-move: drop the carried piece where it was released.
        if self._floating and self._selected_piece and self._drag_move:
            self._place_floating_piece(scene_pos)
            # Invalid drop (collision / outside any bar): revert to the original
            # placement instead of leaving the piece floating.
            if self._floating:
                self._cancel_floating()
            self._drag_move = False
            self._drag_armed = False
            self._drag_candidate = None
            return
        # Plain click on a placed piece:
        #   • Ctrl+click  → toggle multi-selection (block ops).
        #   • click on an already (solely) selected piece → grab it to move it
        #     (it floats and follows the cursor with a snap preview; the next
        #     click drops it). This is the click-to-move gesture (no holding).
        #   • otherwise   → select it (shows the Remove/Delete bar; Delete works).
        if self._drag_armed and not self._floating and self._drag_candidate is not None:
            from PySide6.QtWidgets import QApplication
            additive = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)
            cand = self._drag_candidate
            if additive:
                self._select_placed(cand, additive=True)
            elif self._sel == [cand]:
                self._pick_up_placed(cand)
            else:
                self._select_placed(cand)
        self._drag_armed = False
        self._drag_candidate = None

    def _on_view_right_pressed(self, scene_pos: QPointF) -> None:
        pass

    # ── Float preview update ──────────────────────────────────────────────────

    def _update_float_preview(self, scene_pos: QPointF) -> None:
        if not self._selected_piece:
            return
        corte = self._selected_piece.corte
        fh, fv = self._float_flipped_h, self._float_flipped_v
        sh = self._section_height_mm()

        x_mm = scene_pos.x()
        snap = None

        if self._cb_snap.isChecked():
            # Generous snap zone so the piece nests beside a neighbour when the
            # cursor is roughly where it would go (within ~its own length), not
            # only when within a few mm of the exact slot.
            snap = self._find_best_snap(scene_pos, corte, fh, fv,
                                        max_dx=self._snap_zone_mm(corte))

        if snap:
            bar_idx, snap_x = snap
            bar_y = self._scene.bar_y_for(bar_idx)
            poly_pts = self._compute_poly_local(corte, fh, fv)
            self._scene.set_float_preview(poly_pts, snap_x, bar_y, self._selected_piece.color, True)
            self._snap_preview = snap
        else:
            poly_pts = self._compute_poly_local(corte, fh, fv)
            bar_idx = self._scene.bar_idx_at_y(scene_pos.y())
            if bar_idx is not None and bar_idx < len(self._bars):
                bar_y = self._scene.bar_y_for(bar_idx)
                x_clamped = self._clamp_free_x(x_mm, bar_idx, corte, fh, fv)
                self._scene.set_float_preview(poly_pts, x_clamped, bar_y,
                                               self._selected_piece.color, False)
            else:
                # Not over a bar: keep the carried piece visible following the
                # cursor (never hide it), vertically centred on the pointer.
                free_y = scene_pos.y() - sh / 2.0
                self._scene.set_float_preview(poly_pts, x_mm, free_y,
                                               self._selected_piece.color, False)
            self._snap_preview = None

    # ── Placement ─────────────────────────────────────────────────────────────

    def _place_floating_piece(self, scene_pos: QPointF) -> None:
        pi = self._selected_piece
        if pi is None or not self._floating:
            return
        corte = pi.corte
        fh, fv = self._float_flipped_h, self._float_flipped_v

        if self._cb_snap.isChecked():
            # Snap ON → always nest at the nearest valid slot (flush beside a
            # neighbour or the bar start). Prefer the live preview's slot, then
            # the nearest within the snap zone, then the nearest anywhere.
            target = self._snap_preview
            if target is None:
                target = self._find_best_snap(scene_pos, corte, fh, fv,
                                              max_dx=self._snap_zone_mm(corte))
            if target is None:
                target = self._find_best_snap(scene_pos, corte, fh, fv, max_dx=float("inf"))
            if target is None:
                return
            bar_idx, x_mm = target
        else:
            # Snap OFF → free placement at the cursor (clamped to the bar).
            bar_idx = self._scene.bar_idx_at_y(scene_pos.y())
            if bar_idx is None or bar_idx >= len(self._bars):
                return
            x_mm = self._clamp_free_x(scene_pos.x(), bar_idx, corte, fh, fv)
            if not self._can_place(corte, bar_idx, x_mm, fh, fv):
                # Occupied spot: fall back to the nearest valid slot on any bar.
                fallback = self._find_best_snap(scene_pos, corte, fh, fv, max_dx=float("inf"))
                if fallback is None:
                    return
                bar_idx, x_mm = fallback

        is_move = self._moving_original is not None
        if not is_move:
            self._push_undo()

        poly = self._compute_poly_local(corte, fh, fv)
        pp = PlacedPiece(
            corte=corte,
            bar_index=bar_idx,
            x_offset=x_mm,
            flipped_h=fh,
            flipped_v=fv,
            color=pi.color,
            poly_local=poly,
        )
        self._bars[bar_idx].append(pp)
        pi.placed_qty += 1
        self._moving_original = None
        self._moving_original_pi = None

        # D6: auto-generate DXF contour on first placement (silently, no blocking)
        if not is_move:
            try:
                from nestify.dxf_cache import auto_generate_and_save, piece_dxf_path
                _profile = self._current_profile_name()
                _dxf_path = piece_dxf_path(_profile, corte, fh, fv)
                if not _dxf_path.exists():
                    _H = self._section_height_mm()
                    auto_generate_and_save(_profile, corte, fh, fv, _H)
                    _piece_desc = corte.descripcion or f"{corte.largo:.0f}mm"
                    self.ui.status_lbl.setText(
                        f"DXF contour generated for {_profile} {_piece_desc}"
                    )
            except Exception:
                pass

        if is_move or pi.remaining <= 0:
            self._cancel_floating()
        else:
            self._float_flipped_h = False
            self._float_flipped_v = False
            self._snap_preview = None
            self.ui.qty_lbl.setText(
                f"{pi.corte.descripcion or ''} {pi.corte.largo:.0f} mm  {t('pieces_left', n=pi.remaining)}"
            )

        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()

    # ── Can-place check (engine NFP) ──────────────────────────────────────────
    #
    # Manual placement collides on the EXACT same No-Fit-Polygon geometry the
    # auto-nest engine uses: each piece (moving and every neighbour) is the
    # engine's kerf/2-inflated *virtual* polygon, and a candidate position is
    # valid iff its reference point lies in the engine's *viable space*
    # (IFP minus the union of the neighbours' NFPs). Because this is byte-for-
    # byte the geometry auto-nest places with, manual drops land exactly where
    # auto-nest would — a picked-up piece re-drops in its own slot with no
    # phantom gap, and slanted bevels collide with the true perpendicular kerf
    # (the old midpoint X-shift gave kerf·cosθ and drifted on miters).
    #
    # The RENDERED contour (``_compute_poly_local``) stays the un-inflated shape
    # — kerf inflation lives only in the virtual used for collision, never in
    # what is drawn or exported.

    @staticmethod
    def _poly_x_bounds(local_pts) -> Tuple[float, float]:
        xs = [p[0] for p in local_pts]
        return (min(xs), max(xs)) if xs else (0.0, 0.0)

    @staticmethod
    def _shape_key(corte: Corte) -> tuple:
        """Identity of a cut's contour shape (length + both miters + dirs)."""
        return (round(corte.largo, 4),
                corte.inglete1, corte.inglete2,
                corte.inglete1_dir, corte.inglete2_dir,
                round(corte.inglete1_deg, 4), round(corte.inglete2_deg, 4))

    def _engine_piece(self, corte: Corte, eff_kerf: Optional[float] = None):
        """Cached engine NestingPiece (real + kerf/2-inflated virtual orientations).

        Same builder auto-nest uses; ``virtual_for(fh, fv)`` / ``polygon_for``
        are O(1) dict lookups afterward. Keyed by shape + section height + kerf
        so it stays correct across flips, profile-height and kerf changes.
        """
        sh = self._section_height_mm()
        if eff_kerf is None:
            _, _, eff_kerf, _, _, _ = self._placement_params()
        key = self._shape_key(corte) + (round(sh, 4), round(eff_kerf, 4))
        np = self._engine_piece_cache.get(key)
        if np is None:
            np = build_nesting_piece(corte, 0, sh, "", eff_kerf)
            if len(self._engine_piece_cache) > 512:
                self._engine_piece_cache.clear()
            self._engine_piece_cache[key] = np
        return np

    def _bar_free_intervals(self, bar_idx: int, corte: Corte, fh: bool, fv: bool,
                            exclude: Optional[PlacedPiece] = None):
        """Valid reference-x range and forbidden x-intervals for placing ``corte``
        at (fh,fv) on a bar, from the engine's exact NFP — cached per drag.

        Returns ``(ifp_lo, ifp_hi, forbidden, tol)`` where:
          • ``[ifp_lo, ifp_hi]`` is the inner-fit range (reference-x positions
            that keep the kerf/2-inflated virtual fully on the bar — identical to
            auto-nest's IFP, so the first piece sits at kerf/2, not at the raw
            bar edge);
          • ``forbidden`` is a list of ``(lo, hi)`` open intervals, one per
            neighbour, computed as that neighbour's NFP (vs the moving virtual)
            sliced at the bar baseline y=0. Slicing the 2D NFP captures bevel
            MATING exactly: complementary miters mate flush (a smaller forbidden
            interval than the X-extents alone would give). If the NFP cannot be
            computed for a neighbour, a conservative X-extent interval is used
            instead so collision fails SAFE (over-block), never on top of it.
          • ``tol`` is the per-query collision tolerance (see below).

        Computing each neighbour's forbidden interval directly (instead of one
        IFP−⋃NFP difference) is what makes exact re-placement robust: when a
        flush-packed piece is picked up, its slot is a measure-zero point that a
        shapely difference would drop — but here it survives as the shared
        boundary of two open intervals, so the piece re-drops in its exact spot.
        Returns ``None`` if the bar index is out of range.
        """
        if bar_idx < 0 or bar_idx >= len(self._bars):
            return None
        sh = self._section_height_mm()
        bar_len = self._bar_len_for(bar_idx)
        _, _, eff_kerf, _, _, _ = self._placement_params(bar_idx)
        fp = tuple(sorted(
            (round(pp.x_offset, 2), self._shape_key(pp.corte),
             bool(pp.flipped_h), bool(pp.flipped_v))
            for pp in self._bars[bar_idx] if pp is not exclude))
        key = (bar_idx, bool(fh), bool(fv), round(eff_kerf, 4), round(sh, 4),
               round(bar_len, 2), self._shape_key(corte), fp)
        cached = self._viable_cache.get(key)
        if cached is not None:
            return cached

        mv = self._engine_piece(corte, eff_kerf).virtual_for(fh, fv)
        mv_lo, _mvy0, mv_hi, _mvy1 = mv.bounds
        ifp_lo = 0.0 - mv_lo
        ifp_hi = bar_len - mv_hi
        # Collision tolerance: 0.25 mm normally, but never below the engine's own
        # 0.1 mm bottom-left-fill placement slack (so auto-nest positions stay
        # acceptable) — floored so that at a tiny/zero kerf the extra free-drop
        # overlap allowance shrinks toward that engine slack instead of a fixed
        # 0.25 mm. eff_kerf/2 is the per-side virtual inflation.
        tol = min(_COLLIDE_TOL_MM, max(eff_kerf / 2.0, 0.15))
        forbidden: List[Tuple[float, float]] = []
        for pp in self._bars[bar_idx]:
            if pp is exclude:
                continue
            try:
                nv = self._engine_piece(pp.corte, eff_kerf).virtual_for(
                    pp.flipped_h, pp.flipped_v)
                # UI pieces sit on the bar baseline; engine frame bottom is y=0.
                nv = _sh_affinity.translate(nv, pp.x_offset, 0.0)
                nv_lo, _nyl0, nv_hi, _nyh0 = nv.bounds
            except Exception:
                # Cannot even build the neighbour virtual — engine would fail too.
                continue
            try:
                nfps = _compute_nfp(nv, mv)
            except Exception:
                nfps = None
            if not nfps:
                # NFP failed/empty: fail SAFE (over-block) instead of dropping the
                # neighbour, which would let a piece be placed on top of it. The
                # conservative X-extent forbidden interval never under-blocks.
                forbidden.append((nv_lo - mv_hi, nv_hi - mv_lo))
                continue
            for nfp in nfps:
                nlo, nyl, nhi, nyh = nfp.bounds
                if nyl - 0.05 <= 0.0 <= nyh + 0.05:
                    # Slice the NFP at y=0 for the exact forbidden x-span.
                    try:
                        seg = nfp.intersection(
                            _ShLine([(nlo - 1.0, 0.0), (nhi + 1.0, 0.0)]))
                        xs = [c[0] for g in getattr(seg, "geoms", [seg])
                              for c in getattr(g, "coords", [])]
                    except Exception:
                        xs = []
                    if xs:
                        forbidden.append((min(xs), max(xs)))
                    else:
                        forbidden.append((nlo, nhi))
        result = (ifp_lo, ifp_hi, forbidden, tol)
        if len(self._viable_cache) > 256:
            self._viable_cache.clear()
        self._viable_cache[key] = result
        return result

    @staticmethod
    def _x_allowed(x_mm: float, fi) -> bool:
        """Is reference-x ``x_mm`` a valid placement given precomputed free
        intervals ``fi = (ifp_lo, ifp_hi, forbidden, tol)``? Shared by _can_place
        and the snap/preview paths so the forbidden set is built once per query."""
        ifp_lo, ifp_hi, forbidden, tol = fi
        if x_mm < ifp_lo - _PLACE_TOL_MM or x_mm > ifp_hi + _PLACE_TOL_MM:
            return False
        # Inside any forbidden interval by more than the collision tolerance →
        # blocked. Open intervals (shrunk by ``tol``) so a flush x — which lands on
        # an interval boundary, and which auto-nest itself may place up to 0.1 mm
        # inside — is accepted, matching the engine.
        for lo, hi in forbidden:
            if lo + tol < x_mm < hi - tol:
                return False
        return True

    def _can_place(self, corte: Corte, bar_idx: int, x_mm: float,
                   fh: bool, fv: bool, exclude: Optional[PlacedPiece] = None) -> bool:
        fi = self._bar_free_intervals(bar_idx, corte, fh, fv, exclude)
        if fi is None:
            return False
        return self._x_allowed(x_mm, fi)

    def _placement_params(self, bar_idx: int = 0):
        bar_len = self._bar_len_for(bar_idx)
        sh      = self._section_height_mm()
        kerf    = max(self._state.perdida_corte, 0.0)
        margin  = max(self._state.margen_tubo, 0.0)
        use_bevel = self._mode_switch.isChecked()
        common = self._cb_common.isChecked()
        # eff_kerf is the inter-piece gap (includes margin for non-common cuts).
        # margin is returned separately so bar-edge snap positions and collision
        # checks use the real end-margin, not the hardcoded 0.0 that caused ghost gaps.
        eff_kerf = kerf if common else kerf + margin
        return bar_len, margin, eff_kerf, sh, use_bevel, common

    def _bar_len_for(self, bar_idx: int) -> float:
        if bar_idx < len(self._bar_lengths):
            return self._bar_lengths[bar_idx]
        return self._state.longitud_barra or 6000.0

    def _auto_nest_bar_len(self) -> float:
        """Authoritative bar length for an auto-nest pass (2D engine or 1D packer).

        Fixes two ways the user-set / stock bar length was being ignored:
          • Commits the toolbar bar-length field first. Clicking Auto-nest does
            NOT fire that field's editingFinished, so a length the user just
            typed was silently dropped and the previous one used.
          • In a full ("all") recompute every bar is rebuilt, so the GLOBAL bar
            length from shared state is authoritative — and it already reflects
            a linked stock bar's length when Use-Stock is active (set in
            `_load_from_context` / the stock-link path). `_bar_len_for(0)` would
            instead return a STALE `_bar_lengths[0]` left over from a previous
            nest, overriding the new value and making the field look inert.

        In "remaining" mode existing bars keep their own per-bar lengths; new
        appended bars use this same global length.
        """
        self._on_toolbar_params_changed()
        mode = self._auto_mode_combo.currentData() or "all"
        if mode == "all":
            return self._state.longitud_barra or 6000.0
        return self._bar_len_for(0)

    def _section_height_mm(self) -> float:
        if self._height_override:
            return self._height_override
        return profile_section_height(self._state.perfil)

    # ── Snap ──────────────────────────────────────────────────────────────────

    def _find_best_snap(self, scene_pos: QPointF, corte: Corte,
                         fh: bool, fv: bool,
                         max_dx: Optional[float] = None) -> Optional[Tuple[int, float]]:
        """Nearest valid snap position for the floating piece, or None.

        max_dx limits how far (mm) a snap slot may be from the cursor: by default
        the configured snap zone (so snapping only kicks in near a slot); pass a
        large value (e.g. inf) to get the nearest valid slot regardless of
        distance — used as the drop fallback so a click never lands on top of
        another piece.

        This method only prepares user-selected parameters for the advanced
        engine. It must not alter the engine's internal algorithms.
        """
        sh   = self._section_height_mm()
        gap  = BAR_GAP_MM
        best_score = float("inf")
        best = None
        limit = (max(5.0, app_config.get().__dict__.get("nesting_snap_zone_mm", 5.0))
                 if max_dx is None else max_dx)

        for bar_idx in range(len(self._bars)):
            bar_len = self._bar_len_for(bar_idx)
            bar_y_top = bar_idx * (sh + gap)
            bar_y_bot = bar_y_top + sh
            dy_mm = max(0.0, scene_pos.y() - bar_y_bot) + max(0.0, bar_y_top - scene_pos.y())
            if dy_mm > sh + gap + 2:
                continue

            snaps = list(self._rendered_snaps(bar_idx, corte, fh, fv))  # pre-validated
            # Exact re-placement: when moving a piece, its EXACT original x on its
            # original bar is offered as a candidate (and slightly preferred on
            # ties). The NFP snaps are within ~0.1 mm of it, but auto-nest's own
            # 0.1 mm placement slack means the clean NFP boundary can differ from
            # where the piece actually sat — offering the remembered x guarantees a
            # picked-up piece drops back in its identical spot, with no gap.
            orig = self._moving_original
            prefer_x = None
            if (orig is not None and orig.bar_index == bar_idx
                    and orig.flipped_h == fh and orig.flipped_v == fv
                    and self._can_place(corte, bar_idx, orig.x_offset, fh, fv)):
                prefer_x = orig.x_offset
                snaps.append(orig.x_offset)

            for x_snap in snaps:
                dx = abs(scene_pos.x() - x_snap)
                # Tiny bias toward the exact original slot so re-placement is
                # pixel-perfect when the cursor is essentially on the old spot.
                score = dx + dy_mm * 0.25 - (0.05 if x_snap == prefer_x else 0.0)
                if dx <= limit and score < best_score:
                    best_score = score
                    best = (bar_idx, x_snap)

        return best

    def _rendered_snaps(self, bar_idx: int, corte: Corte,
                        fh: bool, fv: bool) -> List[float]:
        """Flush snap positions on a bar, from the engine NFP free intervals.

        Candidates: the bar-start and bar-end inner-fit positions, plus the two
        flush positions beside each neighbour (the endpoints of its forbidden
        interval — flush-left and flush-right of that piece). All are re-validated
        by _can_place and de-duplicated. Because every candidate is a forbidden-
        interval boundary derived from the same NFP auto-nest uses, the snaps are
        exactly auto-nest's contact positions, and a picked-up piece's original
        slot is always present (it is the boundary of its neighbours' intervals).
        """
        fi = self._bar_free_intervals(bar_idx, corte, fh, fv)
        if fi is None:
            return []
        ifp_lo, ifp_hi, forbidden, _tol = fi
        cands: List[float] = [ifp_lo, ifp_hi]
        for lo, hi in forbidden:
            cands.append(lo)
            cands.append(hi)
        # Validate inline against the single precomputed interval set (avoids
        # rebuilding the forbidden set per candidate — keeps the drag smooth on
        # densely packed bars).
        valid: List[float] = []
        for x in sorted(cands):
            if self._x_allowed(x, fi):
                if not valid or abs(x - valid[-1]) > 0.05:
                    valid.append(x)
        return valid

    def _snap_zone_mm(self, corte: Corte) -> float:
        """Snap pull distance (mm): the larger of the configured zone and ~75%
        of the piece length, so dropping a piece beside another nests it flush."""
        configured = float(getattr(app_config.get(), "nesting_snap_zone_mm", 25.0) or 0.0)
        return max(configured, corte.largo * 0.75)

    def _clamp_free_x(self, x_mm: float, bar_idx: int, corte: Corte, fh: bool, fv: bool) -> float:
        bar_len = self._bar_len_for(bar_idx)
        # Clamp by the engine VIRTUAL x-extent (kerf/2-inflated), so the valid
        # free-placement range matches the collision check exactly: the leftmost
        # reference point keeps kerf/2 clearance at the bar start, the rightmost
        # keeps the piece+kerf on the bar — identical to what _can_place accepts.
        try:
            mv = self._engine_piece(corte).virtual_for(fh, fv)
            v_min, _, v_max, _ = mv.bounds
        except Exception:
            v_min, v_max = self._poly_x_bounds(self._compute_poly_local(corte, fh, fv))
        lo = -v_min
        hi = bar_len - v_max
        if hi < lo:
            hi = lo
        return max(lo, min(hi, x_mm))

    # ── Polygon helpers ───────────────────────────────────────────────────────

    def _compute_poly_local(self, corte: Corte, fh: bool, fv: bool):
        sh = self._section_height_mm()
        # Cache key: only the fields that affect the contour (length, the two
        # miters, orientation and section height). descripcion/cantidad are
        # excluded so identical-shaped cuts share one entry. The returned list is
        # treated as immutable by every caller (collision offsets build new
        # tuples; placed pieces only ever reassign poly_local, never mutate it).
        key = (round(corte.largo, 4),
               corte.inglete1, corte.inglete2,
               corte.inglete1_dir, corte.inglete2_dir,
               round(corte.inglete1_deg, 4), round(corte.inglete2_deg, 4),
               bool(fh), bool(fv), round(sh, 4))
        cached = self._poly_cache.get(key)
        if cached is not None:
            return cached
        try:
            base = _build_base_polygon(corte, sh)
            orients = _build_all_orientations(base)
            poly = orients.get((fh, fv), base)
            pts = list(poly.exterior.coords[:-1])
        except Exception:
            pts = [(0, 0), (corte.largo, 0), (corte.largo, sh), (0, sh)]
        if len(self._poly_cache) > 4096:   # bound memory on long sessions
            self._poly_cache.clear()
        self._poly_cache[key] = pts
        return pts

    # ── Orientation controls ──────────────────────────────────────────────────

    def _refresh_float_preview(self) -> None:
        """Redraw the floating piece preview at the current cursor position.

        Called after any orientation change so the canvas shape and snap slot
        update immediately — before the next mouse-move event.
        """
        if not self._floating or not self._selected_piece:
            return
        from PySide6.QtGui import QCursor
        cursor_global = QCursor.pos()
        cursor_view = self._view.mapFromGlobal(cursor_global)
        scene_pos = self._view.mapToScene(cursor_view)
        self._snap_preview = None
        self._update_float_preview(scene_pos)

    def _cycle_orientation(self, direction: int) -> None:
        if not self._floating or not self._selected_piece:
            return
        fh, fv = self._float_flipped_h, self._float_flipped_v
        try:
            new_fh, new_fv = cycle_orientation(fh, fv, direction)
            self._float_flipped_h, self._float_flipped_v = new_fh, new_fv
        except Exception:
            pass
        self._refresh_float_preview()

    def _flip_horizontal(self) -> None:
        if self._floating:
            self._float_flipped_h = not self._float_flipped_h
            self._refresh_float_preview()
        elif self._selected_placed:
            self._transform_placed(lambda pp: setattr(pp, "flipped_h", not pp.flipped_h))

    def _flip_vertical(self) -> None:
        if self._floating:
            self._float_flipped_v = not self._float_flipped_v
            self._refresh_float_preview()
        elif self._selected_placed:
            self._transform_placed(lambda pp: setattr(pp, "flipped_v", not pp.flipped_v))

    def _transform_placed(self, fn: Callable) -> None:
        targets = self._selected_pps()
        if not targets:
            return
        self._push_undo()
        for pp in targets:
            fn(pp)
            pp.poly_local = self._compute_poly_local(pp.corte, pp.flipped_h, pp.flipped_v)
        self._rebuild_scene()

    # ── Delete ────────────────────────────────────────────────────────────────

    def _selected_pps(self) -> List[PlacedPiece]:
        """Pieces the Borrar/Eliminar actions operate on (the bar selection)."""
        if self._sel:
            return list(self._sel)
        if self._selected_placed is not None:
            return [self._selected_placed]
        return []

    def _select_placed(self, pp: PlacedPiece, additive: bool = False) -> None:
        """Select a placed piece (outline). Ctrl-click toggles multi-selection."""
        if additive:
            if pp in self._sel:
                self._sel.remove(pp)
            else:
                self._sel.append(pp)
        else:
            self._sel = [pp]
        self._selected_placed = pp if self._sel else None
        self._update_delete_btn_visibility()
        self._rebuild_scene()

    def _clear_placed_selection(self) -> None:
        self._sel = []
        self._selected_placed = None
        self._update_delete_btn_visibility()
        self._rebuild_scene()

    def _pi_for_corte(self, corte) -> Optional["PieceInfo"]:
        return next((p for p in self._pieces if p.corte is corte or (
            p.corte.descripcion == corte.descripcion and p.corte.largo == corte.largo
        )), None)

    def _delete_selected_placed(self) -> None:
        """Borrar: remove the selected pieces from their bars, keep pending qty."""
        targets = self._selected_pps()
        if not targets:
            return
        self._push_undo()
        for pp in targets:
            if 0 <= pp.bar_index < len(self._bars):
                self._bars[pp.bar_index] = [p for p in self._bars[pp.bar_index] if p is not pp]
            pi = self._pi_for_corte(pp.corte)
            if pi:
                pi.placed_qty = max(0, pi.placed_qty - 1)
        self._clear_placed_selection()
        self._refresh_sidebar()
        self._update_status()

    def _remove_piece_permanently(self) -> None:
        """Eliminar: delete the selected pieces from the project (with confirm)."""
        targets = self._selected_pps()
        if not targets:
            return
        reply = QMessageBox.question(
            self, t("remove_permanently"),
            t("confirm_remove_n", n=len(targets)) if len(targets) > 1 else t("confirm_remove"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._push_undo()
        for pp in targets:
            if 0 <= pp.bar_index < len(self._bars):
                self._bars[pp.bar_index] = [p for p in self._bars[pp.bar_index] if p is not pp]
            pi = self._pi_for_corte(pp.corte)
            if pi:
                pi.total_qty = max(0, pi.total_qty - 1)
                pi.placed_qty = max(0, pi.placed_qty - 1)
                pi.corte.cantidad = pi.total_qty
        self._clear_placed_selection()
        self._refresh_sidebar()
        self._update_status()

    def _update_delete_btn_visibility(self) -> None:
        n = len(self._selected_pps())
        self.ui.delete_btn.setVisible(n > 0)
        self.ui.remove_btn.setVisible(n > 0)
        if n > 0:
            self.ui.delete_btn.setText(t("delete_from_bar"))
            self.ui.remove_btn.setText(f"{t('remove_permanently')} ({n})" if n > 1
                                       else t("remove_permanently"))
        self._update_left_pan()

    def _update_left_pan(self) -> None:
        """Left-drag panning is allowed only while nothing is selected/floating,
        so it never collides with placing or moving a piece."""
        idle = not self._floating and not self._sel
        self._view.set_left_pan(idle)

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    def _push_undo(self) -> None:
        snapshot = self._serialize_bars()
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._UNDO_MAX:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._nesting_dirty = True

    def _undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._serialize_bars())
        self._restore_bars(self._undo_stack.pop())
        self._cancel_floating()
        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()

    def _redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._serialize_bars())
        self._restore_bars(self._redo_stack.pop())
        self._cancel_floating()
        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()

    def _serialize_bars(self) -> list:
        return [
            [{"descripcion": pp.corte.descripcion, "largo": pp.corte.largo,
              "x_offset": pp.x_offset, "rotation": pp.rotation,
              "flipped_h": pp.flipped_h, "flipped_v": pp.flipped_v,
              "color": pp.color, "bar_index": pp.bar_index}
             for pp in bar]
            for bar in self._bars
        ]

    def _restore_bars(self, snapshot: list) -> None:
        for pi in self._pieces:
            pi.placed_qty = 0
        self._bars = []
        for bar_snap in snapshot:
            bar: List[PlacedPiece] = []
            for item in bar_snap:
                if isinstance(item, dict):
                    desc = item.get("descripcion", "")
                    largo = item.get("largo", 0.0)
                    x_off = item.get("x_offset", 0.0)
                    rot = item.get("rotation", 0)
                    fh = item.get("flipped_h", False)
                    fv = item.get("flipped_v", False)
                    color = item.get("color", "")
                    bi = item.get("bar_index", 0)
                else:
                    (desc, largo, x_off, rot, fh, fv, color, bi) = item
                pi = next((p for p in self._pieces if p.corte.descripcion == desc
                           and p.corte.largo == largo), None)
                corte = pi.corte if pi else Corte(descripcion=desc, largo=largo, cantidad=1)
                poly = self._compute_poly_local(corte, fh, fv)
                pp = PlacedPiece(corte, bi, x_off, rot, fh, fv, color, poly)
                bar.append(pp)
                if pi:
                    pi.placed_qty += 1
            self._bars.append(bar)

    # ── Auto-nest ─────────────────────────────────────────────────────────────

    def refresh_opt_menu_labels(self) -> None:
        """Rebuild the optimization-level combo labels from the saved times."""
        limits = app_config.get_opt_time_limits()  # {1..6: seconds}; 6 == 0 → ∞
        prev = self.ui.opt_combo.currentIndex()
        self.ui.opt_combo.blockSignals(True)
        self.ui.opt_combo.clear()
        for level in range(1, 7):
            secs = limits.get(level, 0.0)
            if level >= 6 or secs <= 0:
                self.ui.opt_combo.addItem(t("opt_level_unlimited"))
            else:
                self.ui.opt_combo.addItem(f"{level} ({secs:g}s)")
        self.ui.opt_combo.setCurrentIndex(prev if 0 <= prev < 6 else 0)
        self.ui.opt_combo.blockSignals(False)

    def _toggle_auto_nest(self) -> None:
        if self._auto_nesting:
            self._cancel_auto_nest()
        else:
            self._run_auto_nest()

    def _run_auto_nest(self, *, skip_clear_warning: bool = False) -> None:
        # This method only prepares user-selected parameters for the advanced
        # engine. It must not alter the engine's internal algorithms.
        if not self._pieces:
            return
        # Prompt to pick a material if none is assigned yet (§3.4).
        ensure_material_contexts(self._state)
        _ctx = self._state.material_contexts[self._state.active_material_index]
        if not _ctx.profile_name and not _ctx.material and not getattr(_ctx, "use_stock", False):
            msg = QMessageBox(self)
            msg.setWindowTitle(t("auto_nest"))
            msg.setText(t("no_material_selected_msg"))
            btn_pick = msg.addButton(t("select_material"), QMessageBox.ButtonRole.ActionRole)
            btn_cont = msg.addButton(t("continue_without_material"), QMessageBox.ButtonRole.AcceptRole)
            btn_cancel = msg.addButton(t("cancel"), QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(btn_pick)
            msg.setMinimumWidth(520)
            for _b in (btn_pick, btn_cont, btn_cancel):
                _b.setMinimumWidth(160)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked is btn_cancel:
                return
            if clicked is btn_pick:
                from nestify.ui_qt.dialogs.stock_material_search_dialog import StockMaterialSearchDialog
                dlg = StockMaterialSearchDialog(self)
                if dlg.exec() == StockMaterialSearchDialog.DialogCode.Accepted and dlg.result_selection:
                    sel = dlg.result_selection
                    _ctx.profile_name = sel.profile_name
                    _ctx.material = sel.material
                    _ctx.quality = sel.quality
                else:
                    return  # user cancelled material picker → abort auto-nest
        # Manual stock mode (§16): when stock is in use but the Auto toggle is
        # off, bars must be added by hand. If the layout has none, prompt the
        # user to add one (offering the picker) instead of auto-creating bars.
        if (getattr(_ctx, "use_stock", False)
                and not getattr(_ctx, "auto_stock", False)
                and not any(self._bars)):
            _msg = QMessageBox(self)
            _msg.setWindowTitle(t("auto_nest_no_bars_title"))
            _msg.setText(t("auto_nest_no_bars_msg"))
            _btn_add = _msg.addButton(t("auto_nest_add_bars"), QMessageBox.ButtonRole.AcceptRole)
            _msg.addButton(t("cancel"), QMessageBox.ButtonRole.RejectRole)
            _msg.setDefaultButton(_btn_add)
            _msg.exec()
            if _msg.clickedButton() is _btn_add:
                self._add_bar()
            return
        # Warn before "Nest All" wipes existing placements (§16).
        if not skip_clear_warning:
            _mode_peek = self._auto_mode_combo.currentData() or "all"
            if _mode_peek == "all" and any(self._bars):
                _n_placed = sum(len(bar) for bar in self._bars)
                _reply = QMessageBox.question(
                    self,
                    t("auto_nest_clear_title"),
                    t("auto_nest_clear_msg", n=_n_placed),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if _reply != QMessageBox.StandardButton.Yes:
                    return

        # Simple mode uses the 1D best-fitting packer (FFD/BFD/NFD), not the 2D
        # NFP engine. It is instant, so no worker thread is needed.
        if not self._mode_switch.isChecked():
            self._run_simple_nest()
            return
        bar_len = self._auto_nest_bar_len()
        sh      = self._section_height_mm()
        _, _, eff_kerf, _, use_bevel, common = self._placement_params()

        # Mode: "all" recomputes everything; "remaining" keeps manual placements
        # and nests only pending pieces (appended on new bars afterwards).
        self._auto_mode = self._auto_mode_combo.currentData() or "all"
        self._remaining_base_bars = len(self._bars) if self._auto_mode == "remaining" else 0

        import copy as _copy
        eng_pieces = []
        for i, pi in enumerate(self._pieces):
            qty = pi.remaining if self._auto_mode == "remaining" else pi.total_qty
            if qty <= 0:
                continue
            corte = pi.corte
            if qty != corte.cantidad:
                corte = _copy.copy(corte)
                corte.cantidad = qty
            try:
                np = build_nesting_piece(corte, i, sh, pi.color, eff_kerf)
                eng_pieces.append(np)
            except Exception:
                pass

        if not eng_pieces:
            return

        params = NestingParams(
            bar_length=bar_len,
            profile_height=sh,
            kerf=eff_kerf,
            margin=0.0,
            common_cut=common,
            priority=self.ui.strategy_combo.currentData() or "length",
        )

        # Time limit comes from the user's configured optimization levels.
        opt_idx = self.ui.opt_combo.currentIndex()
        limits = app_config.get_opt_time_limits()  # {1..6: seconds}; 6/0 → unlimited
        secs = limits.get(opt_idx + 1, 0.0)
        time_limit = None if secs <= 0 else secs

        self._push_undo()
        self._auto_nesting = True
        self._auto_nest_cancel = threading.Event()
        self.ui.auto_nest_btn.setText(f"■ {t('stop')}")
        self.ui.auto_nest_btn.setToolTip(t("tip_auto_nest_stop"))
        self.ui.auto_nest_btn.setStyleSheet(
            f"QPushButton {{background:{_th.DANGER}; color:#FFFFFF; border-radius:4px; font-weight:bold;}}"
        )

        worker = _AutoNestWorker(eng_pieces, params, time_limit, self._auto_nest_cancel, bar_len)
        worker.signals.live_result.connect(self._on_live_result)
        worker.signals.finished.connect(self._on_nest_finished)
        worker.signals.progress_pct.connect(self._on_nest_progress)
        QThreadPool.globalInstance().start(worker)

    def _run_simple_nest(self) -> None:
        """1D best-fitting auto-nest (FFD/BFD/NFD) preserving piece identity.

        Mirrors the systems in logic.calcular_barras but keeps each unit tied to
        its PieceInfo (so colours/labels are correct). The 2D NFP engine is not
        touched. Pieces are placed by nominal length with the inter-piece gap
        from _placement_params (kerf, plus margin unless common-cut).
        """
        bar_len = self._auto_nest_bar_len()
        sh = self._section_height_mm()
        _, _, gap, _, _, _ = self._placement_params()
        system = (self._calc_combo.currentData() or "ffd").lower()

        self._auto_mode = self._auto_mode_combo.currentData() or "all"
        offset = len(self._bars) if self._auto_mode == "remaining" else 0
        self._remaining_base_bars = offset

        # Expand to individual units (largest first), keeping the PieceInfo link.
        units: List[PieceInfo] = []
        for pi in self._pieces:
            qty = pi.remaining if self._auto_mode == "remaining" else pi.total_qty
            units.extend([pi] * max(0, int(qty)))
        units.sort(key=lambda p: p.corte.largo, reverse=True)
        if not units:
            return

        self._push_undo()

        # Each new bar is a list of (PieceInfo, x_offset); cursor = used end (mm).
        bins: List[List[Tuple[PieceInfo, float]]] = []
        cursors: List[float] = []

        # Reserve each piece's TRUE drawn X-footprint (rendered polygon bounds),
        # not its nominal length. A 45° bevel on an H-tall section sticks out by
        # ~H beyond the cut length; placing by nominal length packs the next
        # piece inside that overhang and the two visibly overlap. Using the
        # rendered footprint (the exact shape on screen) guarantees no overlap.
        def _extent(corte) -> Tuple[float, float]:
            pl = self._compute_poly_local(corte, False, False)
            return self._poly_x_bounds(pl)

        def _fits(idx: int, width: float) -> bool:
            start = cursors[idx] + (gap if bins[idx] else 0.0)
            return start + width <= bar_len + _PLACE_TOL_MM

        for pi in units:
            p_min, p_max = _extent(pi.corte)
            width = p_max - p_min
            if width <= 0 or width > bar_len:
                continue
            target = None
            if system == "nfd":
                # Next-fit: only consider the most recently opened bar.
                if bins and _fits(len(bins) - 1, width):
                    target = len(bins) - 1
            elif system == "bfd":
                # Best-fit: the feasible bar with the least remaining space.
                feasible = [i for i in range(len(bins)) if _fits(i, width)]
                if feasible:
                    target = min(feasible, key=lambda i: bar_len - cursors[i])
            else:  # ffd
                target = next((i for i in range(len(bins)) if _fits(i, width)), None)

            if target is None:
                bins.append([])
                cursors.append(0.0)
                target = len(bins) - 1
            start = cursors[target] + (gap if bins[target] else 0.0)
            # Anchor so the polygon's left edge sits at `start` (p_min may be
            # negative for a left-leaning bevel that overhangs the anchor).
            bins[target].append((pi, start - p_min))
            cursors[target] = start + width

        # Build PlacedPieces. In "remaining" mode keep existing bars and append.
        if self._auto_mode != "remaining":
            for pi in self._pieces:
                pi.placed_qty = 0
            self._bars = []
            self._bar_lengths = []
        for b_local, contents in enumerate(bins):
            bar_idx = offset + b_local
            while bar_idx >= len(self._bars):
                self._bars.append([])
                self._bar_lengths.append(bar_len)
            for pi, x_off in contents:
                poly = self._compute_poly_local(pi.corte, False, False)
                self._bars[bar_idx].append(PlacedPiece(
                    corte=pi.corte, bar_index=bar_idx, x_offset=x_off,
                    color=pi.color, poly_local=poly,
                ))
                pi.placed_qty += 1

        self._state.calc_system = system
        self._rebuild_scene(refit=True)
        self._refresh_sidebar()
        self._update_status()
        if self._on_state_change:
            self._on_state_change()

    def _cancel_auto_nest(self) -> None:
        self._auto_nest_cancel.set()

    @Slot(object, float)
    def _on_live_result(self, result: NestingResult, bar_len: float) -> None:
        # In "remaining" mode we only apply the final result (live updates would
        # repeatedly append the pending pieces onto new bars).
        if getattr(self, "_auto_mode", "all") == "remaining":
            return
        if result is not None:
            # Live ticks must NOT refit the view — otherwise the canvas re-centres
            # ~4x/second during a long optimization, fighting any zoom/pan the
            # user does while watching. Only the final result refits.
            self._apply_nest_result(result, bar_len, refit=False)

    @Slot(object, float)
    def _on_nest_finished(self, result, bar_len: float) -> None:
        self._auto_nesting = False
        self.ui.auto_nest_btn.setText(t("auto_nest"))
        self.ui.auto_nest_btn.setToolTip(t("tip_auto_nest"))
        self.ui.auto_nest_btn.setIcon(themed_icon("gear", "#FFFFFF", 14))
        self.ui.auto_nest_btn.setStyleSheet(
            f"QPushButton {{background:{_th.ACCENT}; color:#FFFFFF; border-radius:4px; font-weight:bold;}}"
            f"QPushButton:hover {{background:{_th.ACCENT_HVR};}}"
        )
        if result is not None:
            self._apply_nest_result(result, bar_len)

    @Slot(int)
    def _on_nest_progress(self, pct: int) -> None:
        self._auto_nest_pct = pct
        self.ui.auto_nest_btn.setText(f"■ {t('stop')} {pct}%")

    def _apply_nest_result(self, result: NestingResult, bar_len: float,
                           refit: bool = True) -> None:
        # Bars are being rebuilt — stale remnant markers would point to wrong bars.
        self._show_remnants = False
        self._remnant_names.clear()

        append = getattr(self, "_auto_mode", "all") == "remaining"
        offset = self._remaining_base_bars if append else 0

        max_bar = max((pp.bar_index for pp in result.placed), default=-1) + 1
        if append:
            # Keep manual placements; append the freshly nested pending pieces on
            # new bars after the existing ones (do NOT reset placed_qty).
            need = offset + max_bar
            while len(self._bars) < need:
                self._bars.append([])
                self._bar_lengths.append(bar_len)
        else:
            for pi in self._pieces:
                pi.placed_qty = 0
            self._bars = [[] for _ in range(max_bar)]
            self._bar_lengths = [bar_len] * max_bar

        for eng_pp in result.placed:
            np = eng_pp.piece
            pi = next((p for p in self._pieces if (
                p.corte.descripcion == np.corte.descripcion
                and p.corte.largo == np.corte.largo
            )), None)
            if pi is None:
                continue
            fh, fv = eng_pp.flipped_h, eng_pp.flipped_v
            poly = self._compute_poly_local(np.corte, fh, fv)
            bar_idx = eng_pp.bar_index + offset
            pp = PlacedPiece(
                corte=np.corte,
                bar_index=bar_idx,
                x_offset=eng_pp.x_offset,
                flipped_h=fh, flipped_v=fv,
                color=pi.color,
                poly_local=poly,
            )
            while bar_idx >= len(self._bars):
                self._bars.append([])
                self._bar_lengths.append(bar_len)
            self._bars[bar_idx].append(pp)
            pi.placed_qty += 1

        self._rebuild_scene(refit=refit)
        self._refresh_sidebar()
        self._update_status()
        if self._on_state_change:
            self._on_state_change()

    # ── Scene rebuild ─────────────────────────────────────────────────────────

    def _rebuild_scene(self, refit: bool = False) -> None:
        # The bar layout is about to change (or already has): invalidate the
        # cached per-bar viable spaces so the next collision/snap query rebuilds
        # them from the new neighbour set. The viable cache is keyed by neighbour
        # fingerprint, but clearing here is the single, cheap choke point that
        # guarantees correctness after any place/pick-up/delete/flip/auto-nest.
        self._viable_cache.clear()
        # Keep the per-bar stock-id list aligned with the bars list: pad with
        # None where bars were added by auto-nest, truncate if bars shrank.
        n = len(self._bars)
        if len(self._bar_stock_ids) < n:
            self._bar_stock_ids += [None] * (n - len(self._bar_stock_ids))
        elif len(self._bar_stock_ids) > n:
            self._bar_stock_ids = self._bar_stock_ids[:n]
        sh = self._section_height_mm()
        show_rem = getattr(self, "_show_remnants", False)
        fb = self._filtered_bar
        if fb is not None and 0 <= fb < len(self._bars):
            bars = [self._bars[fb]]
            lengths = [self._bar_lengths[fb] if fb < len(self._bar_lengths) else 6000.0]
        else:
            bars = self._bars
            lengths = self._bar_lengths
        rem_margin = 0.0
        if show_rem:
            try:
                rem_margin = float(self.ui.rem_margin_entry.text() or "0")
            except ValueError:
                rem_margin = 0.0
        self._scene.rebuild(
            bars, lengths, sh,
            selected_pp=(self._sel if self._sel else self._selected_placed),
            highlighted_pps=self._highlighted_pps,
            show_remnants=show_rem,
            filtered_bar_offset=fb if fb is not None else None,
            remnant_margin=rem_margin,
        )
        # Only fit the view on the first populate or on structural changes
        # (auto-nest, filter, show-all). Selection/move/rotate rebuilds keep
        # the user's current zoom so interacting doesn't reset the view.
        if refit or not self._has_fitted:
            self._has_fitted = True
            QTimer.singleShot(0, self._view.fit_scene)

    # ── Status update ─────────────────────────────────────────────────────────

    def _update_status(self) -> None:
        n_bars = len(self._bars)
        n_placed = sum(pi.placed_qty for pi in self._pieces)
        n_total  = sum(pi.total_qty  for pi in self._pieces)
        eff = 0.0
        if self._bars:
            bar_lengths_as_floats = [
                [pp.corte.largo for pp in b] for b in self._bars if b
            ]
            if bar_lengths_as_floats:
                bar_len = self._bar_len_for(0)
                try:
                    eff = eficiencia_barras(bar_lengths_as_floats, bar_len)
                except Exception:
                    pass
        # Lead the status with the ACTIVE engine's setting: the strategy name in
        # advanced (2D) mode, the FFD/BFD/NFD system in simple (1D) mode — so the
        # label matches whichever control the toolbar is currently showing.
        if self._mode_switch.isChecked():
            engine_lbl = self.ui.strategy_combo.currentText() or t("strat_length")
        else:
            engine_lbl = (getattr(self._state, "calc_system", "ffd") or "ffd").upper()
        self.ui.status_lbl.setText(f"{engine_lbl} · {n_bars} bars · {n_placed}/{n_total} placed · {eff:.1f}%")

    # ── Context menu ──────────────────────────────────────────────────────────

    def _piece_info_for(self, pp: PlacedPiece) -> Optional[PieceInfo]:
        """Find the sidebar PieceInfo that owns a placed piece (by cut identity)."""
        return next((p for p in self._pieces if p.corte is pp.corte or (
            p.corte.descripcion == pp.corte.descripcion and p.corte.largo == pp.corte.largo
        )), None)

    def _show_piece_context_menu(self, pp: PlacedPiece) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        # Move / Edit / flips / Delete from bar / Remove permanently — the full
        # set of piece actions, now reachable directly from the canvas.
        menu.addAction(t("move_piece"), lambda: self._pick_up_placed(pp))
        pi = self._piece_info_for(pp)
        if pi is not None:
            menu.addAction(t("change_values"), lambda: self._change_piece_values(pi))
        menu.addSeparator()
        menu.addAction(t("flip_horizontal"), self._flip_horizontal)
        menu.addAction(t("flip_vertical"), self._flip_vertical)
        menu.addSeparator()
        menu.addAction(t("edit_drawing"), lambda: self._edit_piece_drawing(pp))
        menu.addAction(t("export_piece_dxf"), lambda: self._export_piece_dxf(pp))
        menu.addSeparator()
        menu.addAction(t("delete_from_bar"), self._delete_selected_placed)
        menu.addAction(t("remove_permanently"), self._remove_piece_permanently)
        menu.exec(self._view.cursor().pos())

    def _export_piece_dxf(self, pp: PlacedPiece) -> None:
        """Export the contour of a placed piece as a DXF file (D5)."""
        from PySide6.QtWidgets import QFileDialog
        import shutil
        from nestify.dxf_cache import (
            auto_generate_and_save, piece_dxf_path, save_piece_contour,
        )
        profile_name = self._current_profile_name()
        corte = pp.corte
        fh, fv = pp.flipped_h, pp.flipped_v
        H = self._section_height_mm()
        path = piece_dxf_path(profile_name, corte, fh, fv)
        if path.exists():
            dest, _ = QFileDialog.getSaveFileName(
                self, "Export DXF", str(path.name), "DXF (*.dxf)")
            if dest:
                shutil.copy2(str(path), dest)
        else:
            dest, _ = QFileDialog.getSaveFileName(
                self, "Export DXF", path.name, "DXF (*.dxf)")
            if dest:
                try:
                    coords = auto_generate_and_save(profile_name, corte, fh, fv, H)
                    save_piece_contour(coords, profile_name, corte, fh, fv)
                    shutil.copy2(
                        str(piece_dxf_path(profile_name, corte, fh, fv)), dest)
                except Exception:
                    pass

    def _edit_piece_drawing(self, pp: PlacedPiece) -> None:
        """Open the profile drawing module pre-loaded with the cut piece polygon."""
        self._open_cut_piece_in_profile_creator(pp.corte)

    def _edit_sidebar_piece_drawing(self, pi: PieceInfo) -> None:
        """Open the profile drawing module pre-loaded with the sidebar piece polygon."""
        self._open_cut_piece_in_profile_creator(pi.corte)

    def _open_cut_piece_in_profile_creator(self, corte: Corte) -> None:
        """Edit a CUT piece's drawing in the lightweight CutPieceDialog (§27): a
        live 2D preview + a top File menu (Export/Import DXF, Save As, Save), not
        the heavy profile-creator right panel. On Save the edited length/miters are
        written back to the shared Corte and the user is asked whether to re-run
        the nesting with the new shape."""
        from nestify.ui_qt.dialogs.cut_piece_dialog import CutPieceDialog
        H = self._section_height_mm()
        pi = next((p for p in self._pieces if p.corte is corte), None)
        color = pi.color if pi else None
        # Snapshot the shape so we can tell whether the user actually changed it.
        before = self._shape_key(corte)
        dlg = CutPieceDialog(corte, H, color=color, parent=self.window())
        if dlg.exec() != CutPieceDialog.DialogCode.Accepted:
            return
        vals = dlg.result_values()
        corte.largo = vals["largo"]
        corte.inglete1 = vals["inglete1"]
        corte.inglete2 = vals["inglete2"]
        corte.inglete1_dir = vals["inglete1_dir"]
        corte.inglete2_dir = vals["inglete2_dir"]
        corte.inglete1_deg = vals["inglete1_deg"]
        corte.inglete2_deg = vals["inglete2_deg"]
        if self._shape_key(corte) == before:
            return   # nothing changed → leave the layout untouched
        self._on_cut_shape_changed(corte)

    def _on_cut_shape_changed(self, corte: Corte) -> None:
        """A cut's contour changed: invalidate cached polygons and ask the user how
        to reconcile the existing nesting with the new shape (§27)."""
        # The drawn contour is cached by shape key — drop stale entries so the
        # scene, collision and snaps all use the new shape.
        self._poly_cache.clear()
        self._engine_piece_cache.clear()
        self._viable_cache.clear()
        # Refresh stored polygons of any placed copies of this cut.
        for bar in self._bars:
            for pp in bar:
                if pp.corte is corte:
                    pp.poly_local = self._compute_poly_local(
                        pp.corte, pp.flipped_h, pp.flipped_v)
        has_layout = any(self._bars)
        if not has_layout:
            self._rebuild_scene(refit=True)
            self._refresh_sidebar()
            self._update_status()
            return
        # Ask: repeat the nesting, keep the current layout with the new shape, or
        # leave everything as-is for this nesting only.
        box = QMessageBox(self)
        box.setWindowTitle(t("shape_changed_title"))
        box.setText(t("shape_changed_msg"))
        b_repeat = box.addButton(t("shape_changed_repeat"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(t("shape_changed_keep"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is b_repeat:
            self._run_auto_nest(skip_clear_warning=True)
        else:
            self._rebuild_scene(refit=True)
            self._refresh_sidebar()
            self._update_status()

    def _synth_profile_meta(self, profile_name: str) -> dict:
        """Build a geometry meta dict for a built-in profile so its 2D cut can be
        edited in ProfileCreator (which derives shapes from meta.geometry_type).

        Catalogue profiles (IPE, etc.) already live in custom_profiles, so this
        path only handles the basic built-in shapes (Round/Rect/L/U/H); the meta
        is derived from the active profile's cross-section dimensions.
        """
        from nestify.models import TipoPerfil
        perfil = self._state.perfil
        d = perfil.dimensiones if perfil else None
        tipo = d.tipo if d else None
        geom_map = {
            TipoPerfil.REDONDO: "redondo",
            TipoPerfil.RECTANGULAR: "cuadrado",
            TipoPerfil.L: "angular",
            TipoPerfil.U: "viga u",
            TipoPerfil.H: "viga h",
        }
        geometry_type = geom_map.get(tipo, "cuadrado")
        if d is None:
            return {"geometry_type": geometry_type, "h": 100, "b": 100, "tw": 5, "tf": 5}
        h = d.diametro if tipo == TipoPerfil.REDONDO else (d.lado_a or d.lado_b or 100)
        b = d.lado_b or d.lado_a or h
        tw = d.espesor_int_H or d.espesor or 5
        tf = d.lado_c or d.espesor or 5
        return {
            "geometry_type": geometry_type,
            "h": h or 100, "b": b or 100,
            "tw": tw or 5, "tf": tf or 5,
            "macizo": bool(getattr(d, "macizo", False)),
        }

    def _open_profile_creator_for_editing(self) -> None:
        """Look up the current profile entry and open it in ProfileCreator.

        The 2D cut drawing is always editable: for built-in profiles we
        synthesise an editable entry from their geometry (see _synth_profile_meta)
        rather than blocking the user.
        """
        import os as _os_mod
        import shutil as _shutil
        from nestify.ui_qt.dialogs.profile_creator import ProfileCreator
        from nestify.ui_qt.dialogs.profile_save_dialog import ProfileSaveDialog

        profile_name = self._current_profile_name()
        prefs = app_config.get()
        entry = next(
            (cp for cp in getattr(prefs, "custom_profiles", [])
             if cp.name.lower() == profile_name.lower()),
            None,
        )

        _is_new_entry = False
        if entry is None:
            # Built-in profile (basic shape or catalogue): synthesise an editable
            # entry from its geometry so the 2D cut drawing is ALWAYS editable.
            from nestify.app_config import CustomProfileEntry
            meta = self._synth_profile_meta(profile_name)
            entry = CustomProfileEntry(
                id=f"edit-{profile_name.lower().replace(' ', '_')}",
                name=profile_name,
                image="",
                drawing_shapes=[],
                meta=meta,
                manual_sides=[],
                field_defaults={},
            )
            _is_new_entry = True

        def on_save(data):
            thumbnail_path = data.get("thumbnail_path", "")
            drawing_shapes = data.get("shapes", [])
            wkt_str = data.get("wkt", "")
            meta = dict(data.get("meta", {}))
            manual_sides = list(data.get("manual_sides", []))
            field_defaults = data.get("field_defaults", {})

            def on_confirm(result):
                nonlocal _is_new_entry
                entry.name = result["name"]
                entry.quality = result.get("quality", "")
                entry.notes = result.get("notes", "")
                merged = dict(entry.field_defaults)
                merged.update(field_defaults)
                entry.field_defaults = merged
                entry.drawing_shapes = drawing_shapes
                entry.meta = meta
                entry.manual_sides = manual_sides
                if wkt_str:
                    entry.wkt = wkt_str
                if result.get("material"):
                    entry.meta["material"] = result["material"]
                    entry.meta["specific_weight"] = result.get("specific_weight", 7.85)
                if thumbnail_path and _os_mod.path.isfile(thumbnail_path):
                    _os_mod.makedirs(app_config.PROFILES_DIR, exist_ok=True)
                    safe = "".join(
                        c if c.isalnum() or c in "_-" else "_"
                        for c in entry.name
                    )
                    image_name = f"{safe}.png"
                    dest = _os_mod.path.join(app_config.PROFILES_DIR, image_name)
                    _shutil.copy2(thumbnail_path, dest)
                    try:
                        _os_mod.remove(thumbnail_path)
                    except OSError:
                        pass
                    entry.image = image_name
                if _is_new_entry and entry not in prefs.custom_profiles:
                    prefs.custom_profiles.append(entry)
                    _is_new_entry = False
                app_config.save_profile_file(entry)
                app_config.save(prefs)

            ProfileSaveDialog(
                self, fields=list(entry.fields),
                on_confirm=on_confirm,
                initial_name=entry.name,
                initial_quality=entry.quality,
                initial_notes=getattr(entry, "notes", ""),
                initial_material=entry.meta.get("material", ""),
            ).exec()

        ProfileCreator(
            self, on_save=on_save,
            initial_shapes=entry.drawing_shapes,
            initial_meta=getattr(entry, "meta", {}),
            initial_manual_sides=getattr(entry, "manual_sides", []),
        ).exec()

    def _export_sidebar_piece_dxf(self, pi: PieceInfo) -> None:
        """Export the default (unflipped) contour of a sidebar piece as DXF."""
        from PySide6.QtWidgets import QFileDialog
        import shutil
        from nestify.dxf_cache import auto_generate_and_save, piece_dxf_path, save_piece_contour
        profile_name = self._current_profile_name()
        corte = pi.corte
        H = self._section_height_mm()
        path = piece_dxf_path(profile_name, corte, False, False)
        if path.exists():
            dest, _ = QFileDialog.getSaveFileName(
                self, t("export_piece_dxf"), str(path.name), "DXF (*.dxf)")
            if dest:
                shutil.copy2(str(path), dest)
        else:
            dest, _ = QFileDialog.getSaveFileName(
                self, t("export_piece_dxf"), path.name, "DXF (*.dxf)")
            if dest:
                try:
                    coords = auto_generate_and_save(profile_name, corte, False, False, H)
                    save_piece_contour(coords, profile_name, corte, False, False)
                    shutil.copy2(str(piece_dxf_path(profile_name, corte, False, False)), dest)
                except Exception:
                    pass

    def _show_sidebar_context_menu(self, pi: PieceInfo, global_pos) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction(t("change_values"), lambda: self._change_piece_values(pi))
        menu.addSeparator()
        menu.addAction(t("edit_drawing"), lambda: self._edit_sidebar_piece_drawing(pi))
        menu.addAction(t("export_piece_dxf"), lambda: self._export_sidebar_piece_dxf(pi))
        menu.addSeparator()
        menu.addAction(t("remove_permanently"), lambda: self._remove_sidebar_piece(pi))
        menu.exec(global_pos)

    def _remove_sidebar_piece(self, pi: PieceInfo) -> None:
        reply = QMessageBox.question(
            self, t("remove_permanently"), t("confirm_remove"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._push_undo()
        for bar in self._bars:
            bar[:] = [pp for pp in bar if not (
                pp.corte.descripcion == pi.corte.descripcion and pp.corte.largo == pi.corte.largo
            )]
        pi.total_qty = 0
        pi.placed_qty = 0
        pi.corte.cantidad = 0
        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()

    def _change_piece_values(self, pi: PieceInfo) -> None:
        """Edit a cut's values (with bevels + large 2D preview) and sync to Cuts."""
        from nestify.ui_qt.dialogs.change_values_dialog import ChangeValuesDialog
        dlg = ChangeValuesDialog(
            pi.corte, pi.total_qty,
            color=pi.color,
            height_mm=self._section_height_mm(),
            parent=self,
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        vals = dlg.result_values()
        self._push_undo()
        old_desc = pi.corte.descripcion
        old_largo = pi.corte.largo
        # Apply edited values onto the shared Corte (same object the Cuts tab
        # reads through the material context, so the change propagates there).
        pi.corte.descripcion = vals["descripcion"]
        pi.corte.largo = vals["largo"]
        pi.corte.cantidad = max(0, vals["cantidad"])
        pi.corte.inglete1 = vals["inglete1"]
        pi.corte.inglete2 = vals["inglete2"]
        pi.corte.inglete1_dir = vals["inglete1_dir"]
        pi.corte.inglete2_dir = vals["inglete2_dir"]
        pi.corte.inglete1_deg = vals["inglete1_deg"]
        pi.corte.inglete2_deg = vals["inglete2_deg"]
        pi.total_qty = max(0, vals["cantidad"])
        for bar in self._bars:
            for pp in bar:
                if pp.corte.descripcion == old_desc and pp.corte.largo == old_largo:
                    pp.corte = pi.corte
                    pp.poly_local = self._compute_poly_local(pp.corte, pp.flipped_h, pp.flipped_v)
        self._recount_placed()
        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()
        # Persist into the shared state so the Cuts tab reflects the edit.
        self.sync_to_state()
        if self._on_state_change:
            self._on_state_change()
        # Geometry may have changed (bevels/length) — offer to re-run nesting.
        reply = QMessageBox.question(
            self, t("change_values"), t("renest_prompt"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_auto_nest(skip_clear_warning=True)

    # ── Bar management ────────────────────────────────────────────────────────

    def _highlight_all_instances(self, pi: PieceInfo) -> None:
        """Highlight all placed pieces matching this PieceInfo in the scene."""
        self._highlighted_pps = [
            pp for bar in self._bars for pp in bar
            if pp.corte.descripcion == pi.corte.descripcion and pp.corte.largo == pi.corte.largo
        ]
        self._rebuild_scene()

    def _highlight_in_bar(self, bar_idx: int, desc: str, largo: float) -> None:
        """Highlight placed pieces with matching desc/largo within a specific bar."""
        if bar_idx >= len(self._bars):
            return
        self._highlighted_pps = [
            pp for pp in self._bars[bar_idx]
            if pp.corte.descripcion == desc and pp.corte.largo == largo
        ]
        self._rebuild_scene()

    def _toggle_remnant_panel(self) -> None:
        visible = self.ui.remnant_panel.isVisible()
        self.ui.remnant_panel.setVisible(not visible)
        if not visible:
            # Open at half the height of the bars panel (resizable afterwards).
            total = max(self._bars_splitter.height(), 200)
            self._bars_splitter.setSizes([total // 2, total // 2])
            self._refresh_remnants()

    def _active_uses_stock(self) -> bool:
        """True when the active subjob is backed by real stock, so generating a
        remnant won't create stock for a non-existent material."""
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        if getattr(ctx, "use_stock", False):
            return True
        return bool(getattr(self, "_stock_switch", None) and self._stock_switch.isChecked())

    def _rem_min_margin(self):
        try:
            min_len = float(self.ui.remnant_min_entry.text() or "1000")
        except ValueError:
            min_len = 1000.0
        try:
            rem_margin = float(self.ui.rem_margin_entry.text() or "0")
        except ValueError:
            rem_margin = 0.0
        return min_len, rem_margin

    def _refresh_remnants(self) -> None:
        # A remnant becomes new stock, so only allow it when this subjob already
        # uses stock — otherwise we'd invent stock for a non-existent material.
        if not self._active_uses_stock():
            self._show_remnants = False
            self._remnant_names.clear()
            self.ui.remnant_list_lbl.setText(t("remnants_only_with_stock"))
            self._rem_apply_btn_set_enabled(False)
            self._rebuild_scene()
            return
        self._rem_apply_btn_set_enabled(True)
        min_len, rem_margin = self._rem_min_margin()
        self._show_remnants = True
        self._remnant_names.clear()
        seq = 1
        lines = []
        for i, bar in enumerate(self._bars):
            if not bar:
                continue
            bar_len = self._bar_len_for(i)
            used = max((pp.x_offset + pp.corte.largo for pp in bar), default=0.0)
            retal = bar_len - used - rem_margin
            if retal >= min_len:
                mat = (getattr(self._state, "descripcion", "") or "").upper()
                qual = (getattr(self._state, "calidad", "") or "").upper()
                name = f"RET-{mat or 'BAR'}-{qual}-{seq:04d}" if mat else f"RET-{seq:04d}"
                self._remnant_names[i] = name
                lines.append(f"Bar {i + 1}: {retal:.0f} mm → {name}")
                seq += 1
        self.ui.remnant_list_lbl.setText("\n".join(lines) if lines else t("remnants_none"))
        self._rebuild_scene()

    def _rem_apply_btn_set_enabled(self, on: bool) -> None:
        if hasattr(self.ui, "rem_apply_btn"):
            self.ui.rem_apply_btn.setEnabled(on)

    def _apply_remnants_to_stock(self) -> None:
        from nestify import stock_db
        if not self._active_uses_stock():
            QMessageBox.information(
                self, t("generate_remnants_btn"), t("remnants_only_with_stock"))
            return
        if not self._remnant_names:
            QMessageBox.information(self, t("generate_remnants_btn"), t("remnants_none"))
            return
        # Use the SAME min/margin formula as the preview so what you see is what
        # gets written (the old apply ignored the tube margin).
        min_len, rem_margin = self._rem_min_margin()
        ensure_material_contexts(self._state)
        _ctx = self._state.material_contexts[self._state.active_material_index]
        mat = (getattr(self._state, "descripcion", "") or "").strip()
        qual = (getattr(self._state, "calidad", "") or "").strip()
        prof = (getattr(_ctx, "profile_name", "") or "").strip()
        for i in self._remnant_names:
            if i >= len(self._bars):
                continue
            bar_len = self._bar_len_for(i)
            used = max((pp.x_offset + pp.corte.largo for pp in self._bars[i]), default=0.0)
            retal_len = bar_len - used - rem_margin
            if retal_len >= min_len:
                stock_db.add_retal(prof, mat, retal_len, quality=qual)
        self._show_remnants = False
        self._remnant_names.clear()
        self.ui.remnant_panel.setVisible(False)
        self.ui.remnant_list_lbl.setText("")
        QMessageBox.information(self, t("generate_remnants_btn"), t("remnants_applied"))

    def _clear_remnant_selection(self) -> None:
        """Clear the currently generated remnant preview (no stock change)."""
        self._show_remnants = False
        self._remnant_names.clear()
        self.ui.remnant_list_lbl.setText("")
        self._rebuild_scene()

    def _delete_all_remnants(self) -> None:
        """Delete every remnant of this material from stock (with confirmation)."""
        from nestify import stock_db
        mat = (getattr(self._state, "descripcion", "") or "").strip()
        qual = (getattr(self._state, "calidad", "") or "").strip()
        reply = QMessageBox.question(
            self, t("rem_delete_all"), t("rem_delete_all_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        removed = stock_db.delete_retales(mat, qual)
        self._clear_remnant_selection()
        QMessageBox.information(
            self, t("rem_delete_all"), t("rem_deleted_n", n=removed))

    def _show_all_bars(self) -> None:
        self._filtered_bar = None
        self._rebuild_scene(refit=True)
        self._refresh_right_sidebar()

    def _on_bar_header_click(self, bar_idx: int) -> None:
        if self._filtered_bar == bar_idx:
            self._filtered_bar = None
        else:
            self._filtered_bar = bar_idx
        self._expanded_bars.add(bar_idx)
        self._rebuild_scene(refit=True)
        self._refresh_right_sidebar()

    # ── Bar reorder (§3.6) ──────────────────────────────────────────────────────
    # Reordering bars is a PURELY VISUAL operation on the bars panel: it changes
    # the order in which bars are drawn/listed and nothing else. Per §3.6 it must
    # never change a bar's side/orientation, never let bars stack/merge, and never
    # touch nesting data — so we only swap whole bar entries (with their lengths
    # and stock ids) and refresh each piece's bar_index to its new slot. Piece
    # x_offsets, flips, polygons, contents and stock links are left untouched.

    def _swap_bars(self, i: int, j: int) -> None:
        """Swap two whole bars (and their parallel metadata) in place."""
        # Keep the parallel lists padded so the swap can never index past their
        # end (auto-created bars may not have populated lengths/stock ids yet).
        n = len(self._bars)
        bar_len = self._bar_len_for(0)
        while len(self._bar_lengths) < n:
            self._bar_lengths.append(bar_len)
        while len(self._bar_stock_ids) < n:
            self._bar_stock_ids.append(None)

        self._bars[i], self._bars[j] = self._bars[j], self._bars[i]
        self._bar_lengths[i], self._bar_lengths[j] = self._bar_lengths[j], self._bar_lengths[i]
        self._bar_stock_ids[i], self._bar_stock_ids[j] = self._bar_stock_ids[j], self._bar_stock_ids[i]

        # Re-stamp bar_index on the pieces now living in each slot. This is the
        # only piece-level field touched, and it just records which bar a piece
        # belongs to — its position (x_offset), orientation and shape are intact.
        for pp in self._bars[i]:
            pp.bar_index = i
        for pp in self._bars[j]:
            pp.bar_index = j

        # The filter/expand sets reference bar indices: swap their membership so
        # the same physical bars stay filtered/expanded after the reorder.
        if self._filtered_bar == i:
            self._filtered_bar = j
        elif self._filtered_bar == j:
            self._filtered_bar = i
        ei, ej = i in self._expanded_bars, j in self._expanded_bars
        self._expanded_bars.discard(i)
        self._expanded_bars.discard(j)
        if ej:
            self._expanded_bars.add(i)
        if ei:
            self._expanded_bars.add(j)

    def _visible_bar_indices(self) -> List[int]:
        """Real indices of the bars shown in the panel (non-empty), in order."""
        return [idx for idx, bar in enumerate(self._bars) if bar]

    def _move_bar(self, bar_idx: int, direction: int) -> None:
        """Move a visible bar up (direction=-1) or down (direction=+1) among the
        other visible bars. No-op at the ends."""
        visible = self._visible_bar_indices()
        if bar_idx not in visible:
            return
        pos = visible.index(bar_idx)
        target_pos = pos + direction
        if target_pos < 0 or target_pos >= len(visible):
            return
        self._push_undo()
        self._swap_bars(bar_idx, visible[target_pos])
        self._nesting_dirty = True
        self._rebuild_scene(refit=True)
        self._refresh_right_sidebar()

    def _add_bar(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        # When stock is in use, "Add bar" picks a specific physical bar so the
        # layout uses its real (possibly remnant) length and links it for the
        # stock deduction on save (§16). Otherwise add a default-length bar.
        if getattr(ctx, "use_stock", False):
            # If a material is already chosen for this nesting, the picker is
            # locked to it; otherwise it shows all bars and the pick will define
            # the material for the whole app (see below).
            had_material = bool((ctx.profile_name or "").strip()
                                or (ctx.material or "").strip())
            bar = self._pick_stock_bar_for_add(ctx)
            if bar is None:
                return  # user cancelled the picker
            if not had_material:
                self._adopt_material_from_bar(ctx, bar)
            bar_len = bar.retal_length if bar.is_retal else bar.length
            self._bars.append([])
            self._bar_lengths.append(bar_len)
            self._bar_stock_ids.append(bar.id)
            # Keep the context's linked bar pointing at the most recent pick so
            # the single-bar deduction path and the chip stay consistent.
            ctx.linked_stock_bar_id = bar.id
            ctx.linked_stock_bar_name = bar.full_name
            self._stock_bar_lbl.setText(t("use_stock_linked", name=bar.full_name))
            self._stock_bar_lbl.setVisible(True)
        else:
            bar_len = self._bar_len_for(0)
            self._bars.append([])
            self._bar_lengths.append(bar_len)
            self._bar_stock_ids.append(None)
        self._nesting_dirty = True
        self._rebuild_scene()
        self._refresh_right_sidebar()
        self._update_status()

    def _pick_stock_bar_for_add(self, ctx=None):
        """Open the stock-bar picker and return the chosen StockBar (or None).

        When the active context already has a material, the picker is locked to
        that profile/material/quality so only matching bars are offered.
        """
        from nestify.ui_qt.dialogs.stock_bar_picker_dialog import StockBarPickerDialog
        if ctx is None:
            ensure_material_contexts(self._state)
            ctx = self._state.material_contexts[self._state.active_material_index]
        dlg = StockBarPickerDialog(
            self,
            profile_name=ctx.profile_name or "",
            material=ctx.material or "",
            quality=ctx.quality or "",
        )
        if dlg.exec() != StockBarPickerDialog.DialogCode.Accepted:
            return None
        return dlg.result_bar

    def _adopt_material_from_bar(self, ctx, bar) -> None:
        """Set the nesting's material from a stock bar when none was selected yet.

        Mirrors the Cuts-tab material selection so the choice propagates app-wide:
        profile/material/quality on the context and shared state, a full cost/
        weight prefill from the bar, the bar length, and a state-change signal so
        Cuts/Costs refresh. Also renames the sub-tab to the material (§16)."""
        ctx.profile_name = bar.profile_name or ""
        ctx.material = bar.material or ""
        ctx.quality = bar.quality or ""
        self._state.descripcion = ctx.material
        self._state.calidad = ctx.quality
        try:
            from nestify.stock_prefill import apply_stock_bar_to_perfil
            from nestify.models import ConfigPerfil
            apply_stock_bar_to_perfil(ctx.perfil, bar)
            self._state.perfil = ConfigPerfil.from_dict(ctx.perfil.to_dict())
        except Exception:
            pass
        # Rename the active sub-tab to profile · material.
        _pn = (getattr(ctx, "profile_name", "") or "").strip()
        _mat = (ctx.material or "").strip()
        _label = " · ".join(filter(None, [_pn, _mat]))
        if _label:
            idx = self._state.active_material_index
            ctx.name = _label
            self._subtabs.rename_tab(idx, _label)
        if self._on_state_change:
            self._on_state_change()

    # ── Subtab callbacks ──────────────────────────────────────────────────────

    def _on_before_subtab(self, from_idx: int, to_idx: int) -> None:
        # Flush the live bar layout (manual placements, auto-nest results) into
        # state.nesting_layout BEFORE snapshotting the context. Without this the
        # context keeps the stale layout from the last save/load and any
        # placements made since — manual or "Only Remaining" — are lost when the
        # user switches material sub-tabs without pressing Ctrl+S first.
        self.sync_to_state()
        save_state_to_context(self._state, from_idx)

    def _on_subtab_change(self, idx: int) -> None:
        # Belt-and-suspenders save before loading the new context.
        from_idx = self._state.active_material_index
        if from_idx != idx:
            self.sync_to_state()
            save_state_to_context(self._state, from_idx)
        load_context_to_state(self._state, idx)
        self._load_from_context()

    def _on_tab_added(self, idx: int) -> None:
        # A new sub-tab ("+") = a new independent subjob. Ensure a matching
        # MaterialContext exists so load_context_to_state(idx) succeeds.
        from nestify import app_config as _ac
        while len(self._state.material_contexts) <= idx:
            ctx = MaterialContext()
            _ac.apply_cost_defaults(ctx.perfil)   # §27 seed cost defaults
            self._state.material_contexts.append(ctx)
        ensure_material_contexts(self._state)

    def _on_tab_removed(self, idx: int) -> None:
        # Flush the active tab's live layout into its context BEFORE the pop, so a
        # surviving tab's unsaved placements aren't wiped by the reload below (§27).
        old_active = self._state.active_material_index
        if 0 <= old_active < len(self._state.material_contexts) and old_active != idx:
            self.sync_to_state()
            save_state_to_context(self._state, old_active)
        if idx < len(self._state.material_contexts):
            self._state.material_contexts.pop(idx)
        ensure_material_contexts(self._state)
        # Widget active_index() already shifted with the list; load that context.
        self._state.active_material_index = self._subtabs.active_index()
        load_context_to_state(self._state, self._state.active_material_index)
        self._load_from_context()

    def _on_tab_renamed(self, idx: int, name: str) -> None:
        ensure_material_contexts(self._state)
        if idx < len(self._state.material_contexts):
            # custom_display_name is the field context_tab_label() honours so the
            # rename survives rebuilds; ctx.name alone was ignored once a profile
            # was set.
            self._state.material_contexts[idx].custom_display_name = name
            self._state.material_contexts[idx].name = name

    def _load_from_context(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        self._state.perdida_corte  = ctx.perdida_corte
        self._state.margen_tubo    = ctx.margen_tubo
        self._state.longitud_barra = ctx.longitud_barra
        self._state.nesting_height_override = getattr(ctx, "nesting_height_override", None)
        self._state.cortes         = list(ctx.cortes)
        # Load THIS context's saved layout into the shared state before rebuilding
        # the scene, otherwise _restore_from_state would replay the previously
        # active context's (stale) nesting_layout into the newly selected sub-tab.
        self._state.nesting_layout = list(getattr(ctx, "nesting_layout", []) or [])
        self._state.nesting_bar_lengths = list(getattr(ctx, "nesting_bar_lengths", []) or [])
        # Auto-fill height from the profile cross-section when derivable and the
        # user hasn't entered an explicit override.
        h_auto = profile_section_height(self._state.perfil) if self._state.perfil else 0
        h_override = getattr(self._state, "nesting_height_override", None) or 0
        if h_auto and h_auto > 0 and not h_override:
            self._state.nesting_height_override = h_auto
        self.refresh_kerf_margin_fields()
        self._rebuild_pieces()
        self._restore_from_state()
        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()
        self._refresh_stock_ui()
        self._nesting_dirty = False
        self._update_sel_material_btn()

    def has_unsaved_nesting_changes(self) -> bool:
        return self._nesting_dirty

    def _update_sel_material_btn(self) -> None:
        """Show the active subjob's full selection (profile · material · quality)
        in the read-only box next to the 'Sel. material' button."""
        if not hasattr(self, "_sel_material_btn"):
            return
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        from nestify.naming import format_full_name
        label = format_full_name(
            ctx.profile_name or "", ctx.material or "", ctx.quality or "",
        ).strip()
        # The button is the action ("Sel. material"); the box shows the value.
        self._sel_material_btn.setText(t("sel_material"))
        if hasattr(self, "_sel_material_display"):
            self._sel_material_display.setText(label)
            # Show the START of a long name ("IPE 200 · Acer…"), not its tail —
            # setText leaves the cursor at the end, scrolling the box past the
            # profile. The full value is always in the tooltip.
            self._sel_material_display.setCursorPosition(0)
            self._sel_material_display.setToolTip(label)

    def _open_material_search(self) -> None:
        """Open the stock/material search dialog for the Nesting tab."""
        from nestify.ui_qt.dialogs.stock_material_search_dialog import (
            StockMaterialSearchDialog, SRC_STOCK,
        )
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        dlg = StockMaterialSearchDialog(
            parent=self.window(),
            initial_query=(ctx.profile_name or ctx.material or ""),
        )
        if not (dlg.exec() and dlg.result_selection is not None):
            return
        sel = dlg.result_selection
        set_material_selection(
            self._state, sel.profile_name or "", sel.material or "", sel.quality or "",
        )
        if sel.source == SRC_STOCK and sel.stock_bar is not None:
            from nestify.stock_prefill import apply_stock_bar_to_perfil
            from nestify.models import ConfigPerfil
            bar = sel.stock_bar
            apply_stock_bar_to_perfil(ctx.perfil, bar)
            if getattr(bar, "length", 0) and bar.length > 0:
                ctx.longitud_barra = bar.length
                self._state.longitud_barra = bar.length
            self._state.perfil = ConfigPerfil.from_dict(ctx.perfil.to_dict())
        # Ask (once per profile) which face is the cutting height, then auto-fill
        # the read-only bar-height field from the chosen value.
        from nestify.ui_qt.cutting_height import resolve_cutting_height
        resolve_cutting_height(self.window(), self._state)
        # Rename the active sub-tab to profile · material.
        mat_label = " · ".join(filter(None, [
            (sel.profile_name or "").strip(),
            (sel.material or "").strip(),
        ]))
        if mat_label:
            idx = self._state.active_material_index
            ctx.name = mat_label
            self._subtabs.rename_tab(idx, mat_label)
        self.refresh_kerf_margin_fields()
        self._update_sel_material_btn()
        self.sync_to_state()
        if self._on_state_change:
            self._on_state_change()

    # ── Piece list rebuild ────────────────────────────────────────────────────

    def _rebuild_pieces(self) -> None:
        _clear_colors()
        self._pieces = []
        for c in (self._state.cortes or []):
            color = _get_color((c.descripcion, c.largo))
            self._pieces.append(PieceInfo(corte=c, total_qty=c.cantidad, color=color))

    def _recount_placed(self) -> None:
        for pi in self._pieces:
            pi.placed_qty = sum(
                1 for bar in self._bars for pp in bar
                if pp.corte.descripcion == pi.corte.descripcion
                and pp.corte.largo == pi.corte.largo
            )

    # ── Toolbar param changes ─────────────────────────────────────────────────

    def _on_toolbar_params_changed(self) -> None:
        try:
            self._state.perdida_corte = float(self.ui.tb_kerf.text() or "0")
            self._state.margen_tubo   = float(self.ui.tb_margin.text() or "0")
        except ValueError:
            pass
        try:
            bl = self.ui.tb_bar_len.text().strip()
            if bl:
                self._state.longitud_barra = float(bl)
        except ValueError:
            pass
        try:
            txt = self.ui.tb_height.text().strip()
            self._height_override = float(txt) if txt else None
            self._state.nesting_height_override = self._height_override
        except ValueError:
            self._height_override = None
            self._state.nesting_height_override = None
        if self._on_kerf_margin_change:
            self._on_kerf_margin_change()

    def _on_mode_change(self, checked: bool) -> None:
        # Swap the engine-specific controls so each mode only shows its own
        # settings: advanced → optimisation time + strategy; simple → FFD/BFD/NFD.
        self._update_mode_controls()
        # Refresh the status lead so it reflects the now-active engine's setting.
        self._update_status()

    def _update_mode_controls(self) -> None:
        """Show only the controls relevant to the active engine.

        Advanced (2D NFP): optimisation-time combo + strategy combo.
        Simple   (1D best-fit): the FFD/BFD/NFD calculation-system combo.
        """
        advanced = self._mode_switch.isChecked()
        self.ui.opt_combo.setVisible(advanced)
        self.ui.strategy_combo.setVisible(advanced)
        self._calc_combo.setVisible(not advanced)

    def _on_calc_system_change(self, _idx: int) -> None:
        # Keep AppState in sync so the status label and persistence reflect the
        # chosen 1D system (FFD/BFD/NFD).
        self._state.calc_system = self._calc_combo.currentData() or "ffd"
        self._update_status()

    # ── Shortcuts ────────────────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        for seq, fn in [
            ("Ctrl+Z", self._undo),
            ("Ctrl+Y", self._redo),
            ("Ctrl+Q", lambda: self._cycle_orientation(-1)),
            ("Ctrl+E", lambda: self._cycle_orientation(1)),
            ("Ctrl+S", self._save_nesting),
            ("Ctrl+H", self._flip_horizontal),
            ("Ctrl+A", self._flip_vertical),
            ("Delete", self._delete_selected_placed),
            ("Escape", self._on_escape),
        ]:
            sc = QShortcut(QKeySequence(seq), self)
            # Scope to this tab (and its children) so the shortcuts only fire
            # while the user is on Nesting. With the default WindowShortcut they
            # leak across the whole window — e.g. Delete/Ctrl+Z would trigger
            # here even while editing fields on the Cuts or Stock tab.
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Give the canvas focus when the tab is shown so the keyboard shortcuts
        # (now WidgetWithChildren-scoped) are active without a prior click.
        super().showEvent(event)
        self._view.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_escape(self) -> None:
        if self._auto_nesting:
            self._cancel_auto_nest()
        elif self._floating:
            self._cancel_floating()
        else:
            self._clear_placed_selection()

    # ── Sidebar filter ────────────────────────────────────────────────────────

    def _set_sidebar_filter(self, val: str) -> None:
        self._sidebar_filter = val
        self._update_filter_btn_styles()
        self._refresh_left_sidebar()

    def _update_filter_btn_styles(self) -> None:
        """Highlight the active piece filter (All / Complete / Pending): the
        selected button gets the accent fill + contrast text, the others stay as
        quiet ghost buttons. WCAG-correct text colour via _text_color_for_bg."""
        active_fg = _text_color_for_bg(_th.ACCENT)
        active = (
            f"font-size:9px; font-weight:bold; color:{active_fg};"
            f"background:{_th.ACCENT}; border:1px solid {_th.ACCENT}; border-radius:4px;"
        )
        idle = (
            f"font-size:9px; color:{_th.TEXT_SEC};"
            f"background:transparent; border:1px solid {_th.BORDER}; border-radius:4px;"
        )
        cur = getattr(self, "_sidebar_filter", "all")
        for key, btn in (("all", self.ui.filter_all_btn),
                         ("complete", self.ui.filter_complete_btn),
                         ("incomplete", self.ui.filter_incomplete_btn)):
            btn.setStyleSheet(active if key == cur else idle)

    # ── Nesting actions ───────────────────────────────────────────────────────

    def _save_nesting(self) -> None:
        self.sync_to_state()
        self._nesting_dirty = False
        self._deduct_stock_bars()
        self.save_requested.emit()
        # Brief status feedback instead of a blocking dialog
        self.ui.info_bar.setToolTip(t("save_nesting"))

    def _bar_used_length(self, bar_idx: int) -> float:
        """Approximate rightmost extent of placed pieces on bar bar_idx (mm)."""
        pieces = self._bars[bar_idx] if bar_idx < len(self._bars) else []
        if not pieces:
            return 0.0
        margin = self._state.margen_tubo
        return max(pp.x_offset + pp.corte.largo for pp in pieces) + margin

    def _deduct_stock_bars(self) -> None:
        """Reconcile stock bar quantities against how many nesting bars are live."""
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        if not getattr(ctx, "use_stock", False) or not ctx.linked_stock_bar_id:
            return

        from nestify.stock_db import deduct_bar, restore_bar
        active_bar_indices = [i for i, b in enumerate(self._bars) if b]
        n_now = len(active_bar_indices)
        n_prev = getattr(ctx, "nesting_bars_deducted", 0)

        job_name = (self._state.descripcion or "").strip()
        if n_now > n_prev:
            for i in active_bar_indices[n_prev:]:
                # Prefer the bar's own stock id (set when added manually from the
                # picker — important for unique remnants); fall back to the
                # context's single linked bar for the auto path.
                bar_id = None
                if i < len(self._bar_stock_ids):
                    bar_id = self._bar_stock_ids[i]
                bar_id = bar_id or ctx.linked_stock_bar_id
                deduct_bar(bar_id, self._bar_used_length(i), job_name=job_name)
        elif n_now < n_prev:
            restore_bar(ctx.linked_stock_bar_id, n_prev - n_now)

        ctx.nesting_bars_deducted = n_now

    def _current_profile_name(self) -> str:
        """Best-effort canonical profile/material name for export labels."""
        try:
            ctxs = self._state.material_contexts
            idx = self._state.active_material_index
            if ctxs and 0 <= idx < len(ctxs):
                name = ctxs[idx].display_name
                if name:
                    return name
        except Exception:
            pass
        return self._state.descripcion or ""

    def _show_nesting_selector(self):
        """Open the nesting selector dialog; return selected nestings list or None if cancelled."""
        from nestify.ui_qt.dialogs.nesting_selector_dialog import NestingSelectorDialog
        dlg = NestingSelectorDialog(
            self._state,
            self._state.active_material_index,
            self._bars,
            self._bar_lengths,
            self._section_height_mm(),
            parent=self,
        )
        if dlg.exec() != NestingSelectorDialog.DialogCode.Accepted:
            return None
        nestings = dlg.selected_nestings()
        if not nestings:
            QMessageBox.information(self, t("export"), t("no_nestings_available"))
            return None
        return nestings

    def _export_nesting_pdf(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        nestings = self._show_nesting_selector()
        if nestings is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_pdf"), "nestify_nesting.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            from nestify.nesting_pdf import export_multi_nesting_pdf
            export_multi_nesting_pdf(path, nestings, self._state)
        except ValueError as exc:
            QMessageBox.warning(self, t("export_pdf"), str(exc))
            self._rebuild_scene()
            return
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))
            self._rebuild_scene()
            return
        QMessageBox.information(self, t("export_pdf"),
                               t("nesting_png_saved", path=path))
        self._open_file(path)

    def _export_nesting_dxf(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        nestings = self._show_nesting_selector()
        if nestings is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_dxf"), "nestify_nesting.dxf", "DXF (*.dxf)")
        if not path:
            return
        try:
            from nestify.nesting_dxf import export_multi_nesting_dxf
            export_multi_nesting_dxf(path, nestings)
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))
            return
        QMessageBox.information(self, t("export_dxf"),
                               t("nesting_png_saved", path=path))
        self._open_file(path)

    def _print_nesting(self) -> None:
        """Generate a temporary PDF from the selected nestings and send to system printer."""
        nestings = self._show_nesting_selector()
        if nestings is None:
            return
        import os
        import sys
        import subprocess
        import tempfile
        try:
            from nestify.nesting_pdf import export_multi_nesting_pdf
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            try:
                export_multi_nesting_pdf(tmp_path, nestings, self._state)
                if sys.platform == "win32":
                    os.startfile(tmp_path, "print")
                elif sys.platform == "darwin":
                    subprocess.Popen(["lpr", tmp_path])
                else:
                    subprocess.Popen(["lp", tmp_path])
            finally:
                # Give the print spooler a moment before deleting the temp file.
                from PySide6.QtCore import QTimer
                QTimer.singleShot(5000, lambda: _safe_unlink(tmp_path))
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))

    # ── Use-Stock wiring ──────────────────────────────────────────────────────

    def _on_stock_toggle(self, on: bool) -> None:
        # The Auto/manual toggle only makes sense while stock is in use.
        self._auto_stock_toggle_ctr.setEnabled(on)
        if on:
            self._pick_stock_bar()
        else:
            self._clear_stock_link()

    def _on_auto_stock_toggle(self, on: bool) -> None:
        """Persist the manual/auto stock-bar selection mode to the context (§16)."""
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.auto_stock = on

    def _pick_stock_bar(self) -> None:
        from nestify.ui_qt.dialogs.stock_material_search_dialog import (
            StockMaterialSearchDialog, SRC_STOCK)
        dlg = StockMaterialSearchDialog(self, default_mode=SRC_STOCK)
        if dlg.exec() != StockMaterialSearchDialog.DialogCode.Accepted or not dlg.result_selection:
            # User cancelled — revert toggle without re-triggering the signal
            self._stock_switch.toggled.disconnect(self._on_stock_toggle)
            self._stock_switch.setChecked(False)
            self._stock_switch.toggled.connect(self._on_stock_toggle)
            return
        sel = dlg.result_selection
        if sel.stock_bar is None:
            QMessageBox.information(self, t("use_stock"), t("no_stock_bars"))
            self._stock_switch.toggled.disconnect(self._on_stock_toggle)
            self._stock_switch.setChecked(False)
            self._stock_switch.toggled.connect(self._on_stock_toggle)
            return
        bar = sel.stock_bar
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.use_stock = True
        ctx.linked_stock_bar_id = bar.id
        ctx.linked_stock_bar_name = bar.full_name or sel.full_name
        self._stock_bar_lbl.setText(t("use_stock_linked", name=ctx.linked_stock_bar_name))
        self._stock_bar_lbl.setVisible(True)

    def _clear_stock_link(self) -> None:
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        ctx.use_stock = False
        ctx.linked_stock_bar_id = None
        ctx.linked_stock_bar_name = ""
        self._stock_bar_lbl.setVisible(False)
        self._stock_bar_lbl.setText("")

    def _refresh_stock_ui(self) -> None:
        """Restore the stock toggle + label from the active context (called on tab/context switch)."""
        ensure_material_contexts(self._state)
        ctx = self._state.material_contexts[self._state.active_material_index]
        use = getattr(ctx, "use_stock", False)
        auto = getattr(ctx, "auto_stock", False)
        name = getattr(ctx, "linked_stock_bar_name", "")
        # Block signal so we don't re-open the dialog when restoring saved state
        self._stock_switch.toggled.disconnect(self._on_stock_toggle)
        self._stock_switch.setChecked(use)
        self._stock_switch.toggled.connect(self._on_stock_toggle)
        # Restore the Auto/manual toggle (only enabled while stock is in use).
        self._auto_stock_toggle_ctr.setEnabled(use)
        self._auto_stock_switch.toggled.disconnect(self._on_auto_stock_toggle)
        self._auto_stock_switch.setChecked(auto)
        self._auto_stock_switch.toggled.connect(self._on_auto_stock_toggle)
        if use and name:
            self._stock_bar_lbl.setText(t("use_stock_linked", name=name))
            self._stock_bar_lbl.setVisible(True)
        else:
            self._stock_bar_lbl.setVisible(False)
            self._stock_bar_lbl.setText("")

    def _open_file(self, path: str) -> None:
        import sys
        import subprocess
        try:
            if sys.platform == "win32":
                import os
                os.startfile(path)  # noqa: SLF001
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _export_nesting(self) -> None:
        """Render the nesting scene to a PNG image (Qt file dialog)."""
        from PySide6.QtWidgets import QFileDialog
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtCore import QRectF

        rect = self._scene.itemsBoundingRect()
        if rect.isEmpty():
            QMessageBox.information(self, t("export_nesting_png"), t("no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_nesting_png"), "nestify_nesting.png", "PNG (*.png)")
        if not path:
            return
        # Pad a little and render at up to 2× (capped so very wide layouts don't
        # produce an enormous file). Background = the live canvas colour.
        rect = rect.adjusted(-40, -40, 40, 40)
        scale = min(2.0, 4000.0 / rect.width()) if rect.width() > 0 else 2.0
        img = QImage(max(1, int(rect.width() * scale)),
                     max(1, int(rect.height() * scale)),
                     QImage.Format.Format_ARGB32)
        img.fill(QColor(_th.BG_CANVAS))
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._scene.render(painter, target=QRectF(img.rect()), source=rect)
        painter.end()
        if img.save(path, "PNG"):
            QMessageBox.information(self, t("export_nesting_png"),
                                    t("nesting_png_saved", path=path))
        else:
            QMessageBox.critical(self, t("export_error"), path)

    def _clear_nesting(self) -> None:
        reply = QMessageBox.question(
            self, t("clear"), t("clear_nesting_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._push_undo()
        for bar in self._bars:
            bar.clear()
        for pi in self._pieces:
            pi.placed_qty = 0
        self._cancel_floating()
        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()

    # ── State persistence ─────────────────────────────────────────────────────

    def sync_to_state(self) -> None:
        self._state.barras_necesarias = [
            [pp.corte.largo for pp in bar] for bar in self._bars
        ]
        self._state.nesting_layout = self._serialize_bars()
        self._state.nesting_bar_lengths = list(self._bar_lengths)

    def _restore_from_state(self) -> None:
        layout = getattr(self._state, "nesting_layout", None)
        if layout:
            try:
                self._restore_bars(layout)
                # Restore per-bar lengths alongside the layout; pad/truncate to
                # match the bar count so a context switch never leaves stale or
                # missing lengths (which would mis-scale or break bar indexing).
                bar_len = self._bar_len_for(0)
                saved_lengths = list(getattr(self._state, "nesting_bar_lengths", []) or [])
                self._bar_lengths = [
                    saved_lengths[i] if i < len(saved_lengths) else bar_len
                    for i in range(len(self._bars))
                ]
                self._recount_placed()
                return
            except Exception:
                pass
        # Fallback: empty bars matching barras_necesarias count
        barras = getattr(self._state, "barras_necesarias", None) or []
        bar_len = self._bar_len_for(0)
        self._bars = [[] for _ in range(len(barras))]
        self._bar_lengths = [bar_len] * len(barras)

    # ── Public API ────────────────────────────────────────────────────────────

    def load_state(self, state: AppState) -> None:
        self._state = state
        ensure_material_contexts(state)

        # Rebuild the subtab bar from the model WITHOUT emitting tab_removed
        # (which pops material_contexts and would delete the user's jobs).
        from nestify.naming import context_tab_label
        names = [context_tab_label(ctx, i)
                 for i, ctx in enumerate(state.material_contexts)]
        self._subtabs.set_tabs(names, state.active_material_index)

        self._rebuild_pieces()
        self._restore_from_state()
        self._rebuild_scene()
        self._refresh_sidebar()
        self._update_status()

        # Update toolbar fields
        self.ui.tb_kerf.setText(str(state.perdida_corte or 2.0))
        self.ui.tb_margin.setText(str(state.margen_tubo or 0))
        self.ui.tb_bar_len.setText(str(state.longitud_barra or 6000))
        h_val = getattr(state, "nesting_height_override", None)
        self._apply_height_field(h_val)
        # _apply_height_field may set state.nesting_height_override to the
        # profile's cutting height — read it back so the value actually used by
        # _section_height_mm() matches the field (was using the stale h_val).
        self._height_override = getattr(self._state, "nesting_height_override", None)
        # Keep the "Sel. material" box in sync with the loaded context.
        self._update_sel_material_btn()

    def _apply_height_field(self, h_val) -> None:
        """Fill the bar-height field; read-only and auto-filled when the selected
        profile defines a cutting height, editable otherwise."""
        from nestify.context_sync import effective_cutting_height
        h_known = effective_cutting_height(self._state) if self._state.perfil else 0
        if h_known and h_known > 0:
            self._state.nesting_height_override = h_known
            txt = str(int(h_known)) if float(h_known) == int(h_known) else str(h_known)
            self.ui.tb_height.setText(txt)
            self.ui.tb_height.setReadOnly(True)
        else:
            txt = ""
            if h_val:
                txt = str(int(h_val)) if float(h_val) == int(h_val) else str(h_val)
            self.ui.tb_height.setText(txt)
            self.ui.tb_height.setReadOnly(False)

    def refresh_kerf_margin_fields(self) -> None:
        for w in (self.ui.tb_kerf, self.ui.tb_margin, self.ui.tb_bar_len, self.ui.tb_height):
            w.blockSignals(True)
        self.ui.tb_kerf.setText(str(self._state.perdida_corte or 2.0))
        self.ui.tb_margin.setText(str(self._state.margen_tubo or 0))
        self.ui.tb_bar_len.setText(str(self._state.longitud_barra or 6000))
        h_val = getattr(self._state, "nesting_height_override", None)
        self._apply_height_field(h_val)
        self._height_override = h_val
        for w in (self.ui.tb_kerf, self.ui.tb_margin, self.ui.tb_bar_len, self.ui.tb_height):
            w.blockSignals(False)

    def refresh_from_cuts(self) -> None:
        self.sync_subtabs_bar()
        # Mirror the active context's profile · material into the read-only box
        # next to "Sel. material" so it reflects a selection made in any tab.
        self._update_sel_material_btn()
        self.refresh_kerf_margin_fields()
        self._rebuild_pieces()
        # _rebuild_pieces resets placed_qty to 0; recount against the bars that
        # are still placed so the sidebar/status reflect reality (otherwise a
        # restored or previously-nested layout shows "0/N placed").
        self._recount_placed()
        self._rebuild_scene(refit=True)
        self._refresh_sidebar()
        self._update_status()

    def sync_subtabs_bar(self) -> None:
        contexts = self._state.material_contexts
        # Mirror the bar to the model without emitting tab_removed/_added (those
        # mutate material_contexts and would delete the user's jobs/cuts).
        from nestify.naming import context_tab_label
        names = [context_tab_label(ctx, i) for i, ctx in enumerate(contexts)]
        self._subtabs.set_tabs(names, self._state.active_material_index)

    def sync_active_context(self) -> None:
        self.sync_to_state()
        save_state_to_context(self._state, self._state.active_material_index)

    def _refresh_icons(self) -> None:
        """(Re)tint SVG icons for the current theme palette."""
        self.ui.save_btn.setIcon(themed_icon("save"))
        self.ui.clear_btn.setIcon(themed_icon("trash"))
        self.ui.rem_toolbar_btn.setIcon(themed_icon("undo"))
        self.ui.rotate_left_btn.setIcon(themed_icon("rotate-ccw"))
        self.ui.rotate_right_btn.setIcon(themed_icon("rotate-cw"))
        self.ui.rem_refresh_btn.setIcon(themed_icon("rotate-cw"))
        self.ui.rem_apply_btn.setIcon(themed_icon("check"))
        if not self._auto_nesting:
            self.ui.auto_nest_btn.setIcon(themed_icon("gear", "#FFFFFF", 14))

    def refresh_theme(self) -> None:
        """Re-apply inline stylesheets after a theme switch."""
        self._refresh_icons()
        self._view.update_theme()
        self.ui.toolbar_frame.setStyleSheet(
            f"QFrame{{background:{_th.BG_CARD};border-bottom:1px solid {_th.BORDER};}}")
        self.ui.pieces_hdr_frame.setStyleSheet(f"background:{_th.BG_CARD};")
        self.ui.sidebar_title.setStyleSheet(
            f"color:{_th.ACCENT}; font-size:10px; font-weight:bold;")
        self.ui.bars_hdr_frame.setStyleSheet(f"background:{_th.BG_CARD};")
        self.ui.bars_hdr_title.setStyleSheet(
            f"color:{_th.ACCENT}; font-size:10px; font-weight:bold;")
        self.ui.remnant_panel.setStyleSheet(
            f"QFrame{{background:{_th.BG_CARD};border-top:1px solid {_th.BORDER};}}")
        self.ui.status_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:10px;")
        # Update toggle container labels
        _lbl_ss = f"color:{_th.TEXT_PRI}; font-size:10px; background:transparent;"
        for ctr in (self._mode_toggle_ctr, self._stock_toggle_ctr,
                    self._auto_stock_toggle_ctr,
                    self._common_toggle_ctr, self._snap_toggle_ctr):
            for child in ctr.findChildren(QLabel):
                child.setStyleSheet(_lbl_ss)
        # Repaint toggle knobs
        for toggle in (self._mode_switch, self._stock_switch,
                       self._auto_stock_switch,
                       self._cb_common, self._cb_snap):
            toggle.update()
        if not getattr(self, "_auto_nesting", False):
            self.ui.auto_nest_btn.setStyleSheet(
                f"QPushButton {{background:{_th.ACCENT}; color:#FFFFFF; border-radius:4px; font-weight:bold;}}"
                f"QPushButton:hover {{background:{_th.ACCENT_HVR};}}"
            )
        if hasattr(self, '_esc_hint_lbl'):
            self._esc_hint_lbl.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:9px;")
        # Vertical separators between toolbar groups
        for sep in (self.ui.sep1, self.ui.sep2, self.ui.sep3, self.ui.sep4):
            sep.setStyleSheet(f"color:{_th.BORDER};")
        self.ui.qty_lbl.setStyleSheet(f"color:{_th.ACCENT}; font-size:11px;")
        # Filter and show-all buttons — keep the active filter highlighted.
        self._update_filter_btn_styles()
        self.ui.show_all_btn.setStyleSheet("font-size:9px;")
        self.ui.rem_margin_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        self._apply_export_menu_theme()
        if hasattr(self, "_sel_material_btn"):
            self._sel_material_btn.style().polish(self._sel_material_btn)
        self._rebuild_scene()
        self._refresh_sidebar()

    def _apply_export_menu_theme(self) -> None:
        """Force the export dropdown to use current theme colours.

        QMenu is a top-level window and may not repick the QApplication
        stylesheet after a theme switch.  Applying a minimal stylesheet
        directly on the menu ensures it always matches the current palette.
        """
        if not hasattr(self, "_export_menu"):
            return
        self._export_menu.setStyleSheet(
            f"QMenu{{background:{_th.BG_CARD};color:{_th.TEXT_PRI};"
            f"border:1px solid {_th.BORDER};border-radius:6px;padding:4px;}}"
            f"QMenu::item{{padding:5px 24px 5px 12px;border-radius:4px;}}"
            f"QMenu::item:selected{{background:{_th.ACCENT};color:{_th.BG_CARD};}}"
            f"QMenu::separator{{height:1px;background:{_th.BORDER};margin:4px 8px;}}"
        )

    def _apply_panel_sides(self) -> None:
        """Reorder pieces/bars panels in the splitter according to saved preferences.

        Splitter layout after __init__ setup:
          index 0 = ui.pieces_panel, index 1 = _view (canvas), index 2 = ui.bars_panel.
        Default: pieces left (0), bars right (2). Swap indices if prefs differ.
        """
        from nestify import app_config
        prefs = app_config.get()
        pieces_side = getattr(prefs, "nesting_pieces_side", "left")
        bars_side = getattr(prefs, "nesting_bars_side", "right")
        splitter = self.ui.splitter

        # Both on the same side — append pieces after bars or vice versa.
        if pieces_side == "left" and bars_side == "left":
            splitter.insertWidget(0, self.ui.pieces_panel)
            splitter.insertWidget(1, self.ui.bars_panel)
        elif pieces_side == "right" and bars_side == "right":
            splitter.insertWidget(2, self.ui.bars_panel)
            splitter.insertWidget(3, self.ui.pieces_panel)
        elif pieces_side == "right" and bars_side == "left":
            # Swap: bars left, canvas center, pieces right.
            splitter.insertWidget(0, self.ui.bars_panel)
            splitter.insertWidget(2, self.ui.pieces_panel)
        else:
            # Default: pieces left, canvas centre, bars right.
            # Must be explicit so switching back from a non-default config works.
            splitter.insertWidget(0, self.ui.pieces_panel)
            splitter.insertWidget(1, self._view)
            splitter.insertWidget(2, self.ui.bars_panel)
