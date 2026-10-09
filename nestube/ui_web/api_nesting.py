"""
nestube/ui_web/api_nesting.py
Nesting API for the web UI — a thin adapter over the REAL TabNesting.

Every placement decision (NFP collision, snap candidates, same-slot guarantee,
in-place flip guard, auto-nest) is made by ``nestube.ui_qt.tab_nesting`` itself;
this module only forwards pointer/keyboard events in scene coordinates (mm,
bar i at y = i·(section_h + BAR_GAP_MM)) and serialises the resulting state.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QPointF, Slot
from PySide6.QtGui import QTransform

from nestube.context_sync import ensure_material_contexts
from nestube.ui_qt.nesting_scene import BAR_GAP_MM, PlacedPieceItem

_MAIN_TABS = {"jobs": 0, "cuts": 1, "nesting": 2, "costs": 3, "profiles": 4, "stock": 5}


def _r(v: float, d: int = 2) -> float:
    return round(float(v), d)


class _AutoNestRelay(QObject):
    """Receives the auto-nest worker's signals in the GUI thread, runs the
    tab's own handler, then tells the page.

    These MUST be slots of a QObject living in the GUI thread: connected to
    plain Python functions, the worker's queued "finished" was dropped as soon
    as its (auto-deleted) signals object went away, and the run never ended.
    """

    def __init__(self, api: "NestingAPI", parent: QObject) -> None:
        super().__init__(parent)
        self.api = api
        tab = api.tab
        self._progress, self._live, self._finished = (
            tab._on_nest_progress, tab._on_live_result, tab._on_nest_finished)

    @Slot(int)
    def progress(self, pct: int) -> None:
        self._progress(pct)
        # A queued progress tick can arrive after the run finished; it must
        # not bring the progress banner back.
        if self.api.tab._auto_nesting:
            self.api.b.emit("nest:progress", {"pct": pct})

    @Slot(object, float)
    def live(self, result, bar_len: float) -> None:
        self._live(result, bar_len)
        self.api.b.emit("nest:state", self.api.state())

    @Slot(object, float)
    def finished(self, result, bar_len: float) -> None:
        self._finished(result, bar_len)
        self.api.b.emit("nest:finished", self.api.state())


class NestingAPI:
    def __init__(self, bridge) -> None:
        self.b = bridge
        self._wrap_autonest_slots()

    # ── handles ─────────────────────────────────────────────────────────────
    @property
    def app(self):
        return self.b.engine

    @property
    def tab(self):
        return self.b.engine._tab_nesting

    def _pos(self, x: float, y: float) -> QPointF:
        return QPointF(float(x), float(y))

    def _set_zoom(self, zoom: Optional[float]) -> None:
        # Drag/marquee thresholds are "5 px on screen" → 5 / zoom mm. Mirror the
        # web canvas zoom (px per mm) into the hidden view so they match.
        if zoom:
            self.tab._view._zoom_factor = max(1e-4, float(zoom))

    # ── auto-nest progress → events ─────────────────────────────────────────
    def _wrap_autonest_slots(self) -> None:
        # The worker connects to these attributes when a run starts, so
        # instance-level replacements are picked up without touching the tab.
        tab = self.tab
        self._relay = _AutoNestRelay(self, self.b)
        tab._on_nest_progress = self._relay.progress
        tab._on_live_result = self._relay.live
        tab._on_nest_finished = self._relay.finished

    # ── state snapshot ──────────────────────────────────────────────────────
    def state(self) -> Dict[str, Any]:
        tab = self.tab
        ensure_material_contexts(tab._state)
        ctx = tab._state.material_contexts[tab._state.active_material_index]
        sh = tab._section_height_mm()
        pitch = sh + BAR_GAP_MM
        sel = set(id(p) for p in tab._selected_pps())
        hl = set(id(p) for p in tab._highlighted_pps)
        pieces_idx = {id(pi): i for i, pi in enumerate(tab._pieces)}

        bars = []
        for bi, bar in enumerate(tab._bars):
            items = []
            for k, pp in enumerate(bar):
                pi = tab._piece_info_for(pp)
                poly = pp.poly_local or tab._compute_poly_local(pp.corte, pp.flipped_h, pp.flipped_v)
                items.append({
                    "k": k, "cut": pieces_idx.get(id(pi), -1), "x": _r(pp.x_offset, 3),
                    "fh": pp.flipped_h, "fv": pp.flipped_v, "len": pp.corte.largo,
                    "name": pp.corte.descripcion or f"{pp.corte.largo:.0f} mm",
                    "color": pp.color or (pi.color if pi else "#888888"),
                    "poly": [[_r(x, 2), _r(y, 2)] for x, y in poly],
                    "sel": id(pp) in sel, "hl": id(pp) in hl,
                })
            used = sum(p.corte.largo for p in bar)
            L = tab._bar_len_for(bi)
            bars.append({"i": bi, "len": L, "y": bi * pitch, "pieces": items,
                         "eff": _r(used / L * 100 if L else 0, 1),
                         "rem": _r(max(0.0, L - max((p.x_offset + p.corte.largo for p in bar), default=0.0)), 0),
                         "stock": (tab._bar_stock_ids[bi] if bi < len(tab._bar_stock_ids) else None)})

        pieces = []
        for i, pi in enumerate(tab._pieces):
            c = pi.corte
            pieces.append({
                "i": i, "name": c.descripcion or f"{c.largo:.0f} mm", "len": c.largo,
                "total": pi.total_qty, "placed": pi.placed_qty, "remaining": pi.remaining,
                "color": pi.color,
                "aL": c.inglete1_deg if c.inglete1 else 0, "aR": c.inglete2_deg if c.inglete2 else 0,
                "dL": c.inglete1_dir, "dR": c.inglete2_dir,
            })

        floating = None
        if tab._floating and tab._selected_piece is not None:
            fi = tab._scene._float_item
            ghost = None
            if fi.isVisible():
                ghost = {"poly": [[_r(p.x(), 2), _r(p.y(), 2)] for p in fi.polygon()],
                         "snapped": tab._snap_preview is not None}
            floating = {"cut": pieces_idx.get(id(tab._selected_piece), -1),
                        "fh": tab._float_flipped_h, "fv": tab._float_flipped_v,
                        "moving": tab._moving_original is not None, "ghost": ghost,
                        "remaining": tab._selected_piece.remaining}

        remnants = []
        if getattr(tab, "_show_remnants", False):
            _min, rem_margin = tab._rem_min_margin()
            for bi, name in tab._remnant_names.items():
                if bi < len(tab._bars) and tab._bars[bi]:
                    used = max(pp.x_offset + pp.corte.largo for pp in tab._bars[bi])
                    start = used + rem_margin
                    remnants.append({"bar": bi, "x": _r(start), "w": _r(tab._bar_len_for(bi) - start), "name": name})

        n_total = sum(pi.total_qty for pi in tab._pieces)
        n_placed = sum(pi.placed_qty for pi in tab._pieces)
        return {
            "sh": sh, "gap": BAR_GAP_MM, "bars": bars, "pieces": pieces, "floating": floating,
            "remnants": remnants, "show_remnants": bool(getattr(tab, "_show_remnants", False)),
            "status": tab.ui.status_lbl.text(), "placed": n_placed, "total": n_total,
            "sel_count": len(sel), "left_pan": bool(tab._view._left_pan_enabled),
            "auto_nesting": bool(tab._auto_nesting), "pct": getattr(tab, "_auto_nest_pct", 0),
            "undo": len(tab._undo_stack), "redo": len(tab._redo_stack),
            "dirty": bool(tab._nesting_dirty or self.app._is_dirty()),
            "nest_dirty": bool(tab._nesting_dirty),
            "params": self._params(ctx),
            "subtabs": self._subtabs(),
        }

    def _params(self, ctx) -> Dict[str, Any]:
        tab = self.tab
        ui = tab.ui
        from nestube.naming import format_full_name
        return {
            "kerf": ui.tb_kerf.text(), "margin": ui.tb_margin.text(), "bar_len": ui.tb_bar_len.text(),
            "height": ui.tb_height.text(), "height_ro": ui.tb_height.isReadOnly(),
            "advanced": tab._mode_switch.isChecked(), "snap": tab._cb_snap.isChecked(),
            "common": tab._cb_common.isChecked(),
            "strategy": ui.strategy_combo.currentData() or "length",
            "strategies": [[ui.strategy_combo.itemData(i), ui.strategy_combo.itemText(i)] for i in range(ui.strategy_combo.count())],
            "opt": ui.opt_combo.currentIndex(),
            "opt_labels": [ui.opt_combo.itemText(i) for i in range(ui.opt_combo.count())],
            "calc": tab._calc_combo.currentData() or "ffd",
            "auto_mode": tab._auto_mode_combo.currentData() or "all",
            "use_stock": tab._stock_switch.isChecked(), "auto_stock": tab._auto_stock_switch.isChecked(),
            "stock_label": tab._stock_bar_lbl.text() if tab._stock_bar_lbl.isVisible() else "",
            "material": format_full_name(ctx.profile_name or "", ctx.material or "", ctx.quality or "").strip(),
            "rem_min": ui.remnant_min_entry.text(), "rem_margin": ui.rem_margin_entry.text(),
        }

    def _subtabs(self) -> Dict[str, Any]:
        from nestube.naming import context_tab_label
        st = self.tab._state
        return {"names": [context_tab_label(c, i) for i, c in enumerate(st.material_contexts)],
                "active": st.active_material_index,
                "counts": [sum(c.cantidad for c in (ctx.cortes or [])) for ctx in st.material_contexts]}

    # ── pointer events (scene coordinates, mm) ──────────────────────────────
    def press(self, x: float, y: float, zoom: float = 0) -> Dict[str, Any]:
        """Left button down. Mirrors NestingView.mousePressEvent: the tab's
        view handler runs first, then the item under the cursor (if any)."""
        self._set_zoom(zoom)
        tab, pos = self.tab, self._pos(x, y)
        tab._on_view_pressed(pos)
        hit = tab._scene.itemAt(pos, QTransform())
        if isinstance(hit, PlacedPieceItem) and hit.pp_ref is not None:
            tab._on_scene_piece_pressed(hit)
        return self.state()

    def move(self, x: float, y: float, zoom: float = 0) -> Dict[str, Any]:
        self._set_zoom(zoom)
        self.tab._on_view_moved(self._pos(x, y))
        return self.state()

    def release(self, x: float, y: float, ctrl: bool = False, zoom: float = 0) -> Dict[str, Any]:
        self._set_zoom(zoom)
        self.tab._on_view_released(self._pos(x, y), additive=bool(ctrl))
        return self.state()

    def hit(self, x: float, y: float) -> Optional[Dict[str, int]]:
        item = self.tab._scene.itemAt(self._pos(x, y), QTransform())
        if isinstance(item, PlacedPieceItem) and item.pp_ref is not None:
            pp = item.pp_ref
            return {"bar": pp.bar_index, "k": self.tab._bars[pp.bar_index].index(pp)}
        return None

    def context(self, x: float, y: float) -> Dict[str, Any]:
        """Right button on a piece: same selection rule as the Qt canvas (the
        menu itself is drawn by the web UI)."""
        tab = self.tab
        item = tab._scene.itemAt(self._pos(x, y), QTransform())
        piece = None
        if isinstance(item, PlacedPieceItem) and item.pp_ref is not None:
            pp = item.pp_ref
            tab._selected_placed = pp
            if pp not in tab._sel:
                tab._sel = [pp]
                tab._update_delete_btn_visibility()
                tab._rebuild_scene()
            pi = tab._piece_info_for(pp)
            piece = {"cut": tab._pieces.index(pi) if pi in tab._pieces else -1,
                     "name": pp.corte.descripcion, "len": pp.corte.largo}
        return {"piece": piece, "state": self.state()}

    # ── piece / sidebar actions ─────────────────────────────────────────────
    def select_piece(self, i: int) -> Dict[str, Any]:
        tab = self.tab
        if 0 <= i < len(tab._pieces):
            pi = tab._pieces[i]
            if pi.remaining > 0:
                tab._select_piece(pi)
            else:
                tab._highlight_all_instances(pi)
        return self.state()

    def action(self, name: str, **kw) -> Dict[str, Any]:
        tab = self.tab
        fn = {
            "undo": tab._undo, "redo": tab._redo,
            "rotate_left": lambda: tab._cycle_orientation(-1),
            "rotate_right": lambda: tab._cycle_orientation(1),
            "flip_h": tab._flip_horizontal, "flip_v": tab._flip_vertical,
            "delete": tab._delete_selected_placed, "remove": tab._remove_piece_permanently,
            "escape": tab._on_escape, "cancel_float": tab._cancel_floating,
            "clear_selection": tab._clear_placed_selection,
            "save": tab._save_nesting, "clear": tab._clear_nesting, "add_bar": tab._add_bar,
            "show_all": tab._show_all_bars,
            "move_selected": self._move_selected,
            "rem_refresh": tab._refresh_remnants, "rem_apply": tab._apply_remnants_to_stock,
            "rem_clear": tab._clear_remnant_selection, "rem_delete_all": tab._delete_all_remnants,
            "export_pdf": tab._export_nesting_pdf, "print": tab._print_nesting,
            "export_dxf": tab._export_nesting_dxf, "export_png": tab._export_nesting,
            "sel_material": tab._open_material_search,
            "edit_drawing": self._edit_selected_drawing, "export_piece_dxf": self._export_selected_dxf,
            "change_values_native": self._change_values_native,
        }.get(name)
        if fn is None:
            raise AttributeError(f"unknown nesting action {name!r}")
        fn()
        return self.state()

    def _first_selected(self):
        sel = self.tab._selected_pps()
        return sel[0] if sel else None

    def _move_selected(self) -> None:
        pp = self._first_selected()
        if pp is not None:
            self.tab._pick_up_placed(pp)

    def _edit_selected_drawing(self) -> None:
        pp = self._first_selected()
        if pp is not None:
            self.tab._edit_piece_drawing(pp)

    def _export_selected_dxf(self) -> None:
        pp = self._first_selected()
        if pp is not None:
            self.tab._export_piece_dxf(pp)

    def _change_values_native(self) -> None:
        pp = self._first_selected()
        pi = self.tab._piece_info_for(pp) if pp is not None else None
        if pi is not None:
            self.tab._change_piece_values(pi)

    def piece_action(self, i: int, name: str) -> Dict[str, Any]:
        """Sidebar context menu actions on a cut (PieceInfo index)."""
        tab = self.tab
        if not (0 <= i < len(tab._pieces)):
            return self.state()
        pi = tab._pieces[i]
        {
            "change_values_native": lambda: tab._change_piece_values(pi),
            "edit_drawing": lambda: tab._edit_sidebar_piece_drawing(pi),
            "export_piece_dxf": lambda: tab._export_sidebar_piece_dxf(pi),
            "remove": lambda: tab._remove_sidebar_piece(pi),
            "highlight": lambda: tab._highlight_all_instances(pi),
        }[name]()
        return self.state()

    def set_cut_values(self, i: int, values: Dict[str, Any], renest: bool = False) -> Dict[str, Any]:
        """Apply the web "Cambiar valores" form — same effect as the Qt
        ChangeValuesDialog path in TabNesting._change_piece_values."""
        tab = self.tab
        if not (0 <= i < len(tab._pieces)):
            return self.state()
        pi = tab._pieces[i]
        tab._push_undo()
        old_desc, old_largo = pi.corte.descripcion, pi.corte.largo
        c = pi.corte
        c.descripcion = str(values.get("descripcion", c.descripcion))
        c.largo = float(values.get("largo", c.largo))
        c.cantidad = max(0, int(values.get("cantidad", c.cantidad)))
        for k in ("inglete1", "inglete2"):
            if k in values:
                setattr(c, k, bool(values[k]))
        for k in ("inglete1_dir", "inglete2_dir"):
            if k in values:
                setattr(c, k, str(values[k]))
        for k in ("inglete1_deg", "inglete2_deg"):
            if k in values:
                setattr(c, k, float(values[k]))
        pi.total_qty = c.cantidad
        if values.get("color"):
            pi.color = values["color"]
        for bar in tab._bars:
            for pp in bar:
                if pp.corte.descripcion == old_desc and pp.corte.largo == old_largo:
                    pp.corte = c
                    if values.get("color"):
                        pp.color = values["color"]
                    pp.poly_local = tab._compute_poly_local(c, pp.flipped_h, pp.flipped_v)
        tab._recount_placed()
        tab._rebuild_scene()
        tab._refresh_sidebar()
        tab._update_status()
        tab.sync_to_state()
        if renest:
            tab._run_auto_nest(skip_clear_warning=True, prompt_material=False)
        return self.state()

    # ── bars panel ──────────────────────────────────────────────────────────
    def move_bar(self, i: int, direction: int) -> Dict[str, Any]:
        self.tab._move_bar(int(i), int(direction))
        return self.state()

    def highlight_in_bar(self, bar: int, cut: int) -> Dict[str, Any]:
        tab = self.tab
        if 0 <= cut < len(tab._pieces):
            c = tab._pieces[cut].corte
            tab._highlight_in_bar(int(bar), c.descripcion, c.largo)
        return self.state()

    # ── auto-nest ───────────────────────────────────────────────────────────
    def needs_material(self) -> bool:
        tab = self.tab
        ensure_material_contexts(tab._state)
        ctx = tab._state.material_contexts[tab._state.active_material_index]
        return not ctx.profile_name and not ctx.material and not getattr(ctx, "use_stock", False)

    def auto_nest(self, continue_without_material: bool = True) -> Dict[str, Any]:
        tab = self.tab
        if tab._auto_nesting:
            tab._cancel_auto_nest()
        else:
            tab._run_auto_nest(skip_clear_warning=True,
                               prompt_material=not continue_without_material)
        return self.state()

    def stop_auto_nest(self) -> Dict[str, Any]:
        if self.tab._auto_nesting:
            self.tab._cancel_auto_nest()
        return self.state()

    # ── parameters ──────────────────────────────────────────────────────────
    def set_params(self, **p) -> Dict[str, Any]:
        tab, ui = self.tab, self.tab.ui
        fields = {"kerf": ui.tb_kerf, "margin": ui.tb_margin, "bar_len": ui.tb_bar_len, "height": ui.tb_height}
        touched = False
        for k, w in fields.items():
            if k in p and not (k == "height" and w.isReadOnly()):
                w.setText(str(p[k]))
                touched = True
        if touched:
            tab._on_toolbar_params_changed()
            tab._viable_cache.clear()
            tab._rebuild_scene()
            tab._update_status()
        if "advanced" in p:
            tab._mode_switch.setChecked(bool(p["advanced"]))
        if "snap" in p:
            tab._cb_snap.setChecked(bool(p["snap"]))
        if "common" in p:
            tab._cb_common.setChecked(bool(p["common"]))
            tab._viable_cache.clear()
        if "strategy" in p:
            j = ui.strategy_combo.findData(p["strategy"])
            if j >= 0:
                ui.strategy_combo.setCurrentIndex(j)
        if "opt" in p:
            ui.opt_combo.setCurrentIndex(int(p["opt"]))
        if "calc" in p:
            j = tab._calc_combo.findData(p["calc"])
            if j >= 0:
                tab._calc_combo.setCurrentIndex(j)
        if "auto_mode" in p:
            j = tab._auto_mode_combo.findData(p["auto_mode"])
            if j >= 0:
                tab._auto_mode_combo.setCurrentIndex(j)
        if "use_stock" in p:
            tab._stock_switch.setChecked(bool(p["use_stock"]))   # opens the native stock picker
        if "auto_stock" in p:
            tab._auto_stock_switch.setChecked(bool(p["auto_stock"]))
        if "rem_min" in p:
            ui.remnant_min_entry.setText(str(p["rem_min"]))
        if "rem_margin" in p:
            ui.rem_margin_entry.setText(str(p["rem_margin"]))
        return self.state()
