"""
nestube/ui_web/api_data.py
Jobs, Cuts, Costs, Profiles, Stock, menus and settings for the web UI.

Each call goes through the headless NesTubeApp and its tabs, so persistence,
cross-tab state sync, cost formulas and stock rules are the application's own.
Dialogs that the web UI does not draw yet open as the native Qt dialogs (they
follow the app theme); file pickers are always native.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QUrl

from nestube import __version__, app_config
from nestube.context_sync import ensure_material_contexts
from nestube.i18n import t

_VIEWS = ["jobs", "cuts", "nesting", "costs", "profiles", "stock"]


def _file_url(path: str) -> str:
    return QUrl.fromLocalFile(path).toString() if path and os.path.isfile(path) else ""


def _num(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


class DataAPI:
    def __init__(self, bridge) -> None:
        self.b = bridge

    @property
    def app(self):
        return self.b.engine

    @property
    def state(self):
        return self.b.engine._state

    def _ctx(self):
        ensure_material_contexts(self.state)
        return self.state.material_contexts[self.state.active_material_index]

    # ── boot / view ─────────────────────────────────────────────────────────
    def boot(self) -> Dict[str, Any]:
        p = app_config.get()
        return {"version": __version__, "theme": p.theme, "language": p.language,
                "units": getattr(p, "unit_system", "metric"),
                "cut_colors": bool(getattr(p, "nesting_use_cut_colors", True)),
                "job": self.job_header(), "view": _VIEWS[self.app._tabs.currentIndex()],
                "db_path": self._db_path(), "github": self.app._github_url()}

    def _db_path(self) -> str:
        try:
            from nestube.database import get_geometry_db
            return os.path.basename(get_geometry_db()._db_path)
        except Exception:
            return "nestube_geometry.db"

    def job_header(self) -> Dict[str, Any]:
        st = self.state
        name = ""
        jid = getattr(self.app, "_current_job_id", None)
        if jid is not None:
            try:
                from nestube.database import get_geometry_db
                name = next((j.get("name") or "" for j in get_geometry_db().list_jobs_summary()
                             if j.get("id") == jid), "")
            except Exception:
                name = ""
        from nestube.naming import format_full_name
        ctx = self._ctx()
        return {"id": jid, "name": name, "order": st.pedido or "", "offer": st.oferta or "",
                "client": st.cliente or "", "dirty": bool(self.app._is_dirty()),
                "material": format_full_name(ctx.profile_name or "", ctx.material or "", ctx.quality or "").strip()}

    def set_view(self, name: str) -> Dict[str, Any]:
        """Switch the engine's main tab — runs the same flush/refresh as the
        classic UI (cuts → nesting sync, unsaved-nesting guard via _answer)."""
        idx = _VIEWS.index(name)
        tabs = self.app._tabs
        tabs.setCurrentIndex(idx)
        return {"view": _VIEWS[tabs.currentIndex()], "job": self.job_header()}

    # ── material sub-tabs (shared by Cuts / Nesting / Costs) ────────────────
    def _subtab_widget(self):
        i = self.app._tabs.currentIndex()
        tab = {1: self.app._tab_cortes, 3: self.app._tab_perfiles}.get(i, self.app._tab_nesting)
        return tab._subtabs

    def subtabs(self) -> Dict[str, Any]:
        from nestube.naming import context_tab_label
        st = self.state
        ensure_material_contexts(st)
        return {"names": [context_tab_label(c, i) for i, c in enumerate(st.material_contexts)],
                "active": st.active_material_index,
                "counts": [sum(int(c.cantidad or 0) for c in (ctx.cortes or [])) for ctx in st.material_contexts],
                "total_view": bool(getattr(self.app._tab_perfiles, "_on_total_tab", False))}

    def subtab_switch(self, i: int) -> Dict[str, Any]:
        self._subtab_widget()._on_tab_clicked(int(i))
        return self.subtabs()

    def subtab_add(self) -> Dict[str, Any]:
        self._subtab_widget()._on_add_clicked()
        return self.subtabs()

    def subtab_delete(self, i: int) -> Dict[str, Any]:
        self._subtab_widget()._delete_tab(int(i))
        return self.subtabs()

    def subtab_rename(self, i: int, name: str) -> Dict[str, Any]:
        w = self._subtab_widget()
        w.rename_tab(int(i), name)
        w.tab_renamed.emit(int(i), name)
        return self.subtabs()

    # ── cuts ────────────────────────────────────────────────────────────────
    def cuts_get(self) -> Dict[str, Any]:
        tab = self.app._tab_cortes
        rows = []
        for r in tab._rows:
            c = r.get_corte()
            if c is None:
                continue
            rows.append(c.to_dict())
        from nestube.ui_qt.tab_cortes import _get_cut_color
        for d in rows:
            d["color"] = _get_cut_color((d["descripcion"], d["largo"])) if d["largo"] else "#888888"
        ctx = self._ctx()
        st = self.state
        bars = [list(map(float, b)) for b in (st.barras_necesarias or [])]
        return {
            "rows": rows,
            "header": {"profile": tab._search_bar.profile_name(), "material": tab._search_bar.material(),
                       "quality": tab._search_bar.quality(), "order": tab._e_pedido.text(),
                       "offer": tab._e_oferta.text(), "client": tab._e_cliente.text(),
                       "custom": dict(getattr(st, "custom_fields", {}) or {})},
            "params": {"bar_len": tab._e_bar_len.text(), "kerf": tab._e_kerf.text(),
                       "margin": tab._e_margin.text(), "height": tab._e_bar_height.text(),
                       "height_ro": tab._e_bar_height.isReadOnly(),
                       "calc": tab.ui.calc_combo_cuts.currentData() or "ffd"},
            "result": tab._result_lbl.text(),
            "bars": bars, "bar_len": float(ctx.longitud_barra or 6000),
        }

    def cuts_set(self, rows: Optional[List[dict]] = None, header: Optional[dict] = None,
                 params: Optional[dict] = None) -> Dict[str, Any]:
        from nestube.models import Corte
        tab = self.app._tab_cortes
        if self.app._tabs.currentIndex() != 1:
            # The Cuts widgets are only refreshed when that tab is shown; load
            # the active context first so the flush below doesn't write a stale
            # header (e.g. an empty material search) over it.
            tab.sync_subtabs_bar()
            tab._apply_context_to_ui()
        if header:
            for key, w in (("order", tab._e_pedido), ("offer", tab._e_oferta), ("client", tab._e_cliente)):
                if key in header:
                    w.setText(str(header[key]))
            tab._sync_header()
        if params:
            for key, w in (("bar_len", tab._e_bar_len), ("kerf", tab._e_kerf),
                           ("margin", tab._e_margin), ("height", tab._e_bar_height)):
                if key in params and not (key == "height" and w.isReadOnly()):
                    w.setText(str(params[key]))
            if "calc" in params:
                j = tab.ui.calc_combo_cuts.findData(params["calc"])
                if j >= 0:
                    tab.ui.calc_combo_cuts.setCurrentIndex(j)
            tab._on_bar_params_change()
        if rows is not None:
            tab._clear_rows()
            for d in rows:
                tab._add_row(corte=Corte.from_dict(d))
            if not tab._rows:
                tab._add_row()
            tab._assign_row_colors()
        if rows is not None or params:
            # Commit to the shared state and the material context right away
            # (the classic UI only does it when leaving the Cuts tab), so
            # Nesting/Costs see the edit whichever view the engine is on.
            self.app._flush_main_tab(1)
            cur = self.app._tabs.currentIndex()
            if cur != 1:
                self.app._refresh_main_tab(cur)
        return self.cuts_get()

    def cuts_calc(self) -> Dict[str, Any]:
        self.app._tab_cortes._calcular()
        return self.cuts_get()

    def material_options(self, mode: str = "profile", query: str = "", min_len: str = "") -> Dict[str, Any]:
        """Rows for the web material search (same lists as the Qt dialog)."""
        from nestube.ui_web.dialogs import material_options
        return material_options(mode, query, min_len)

    def cuts_material_search(self) -> Dict[str, Any]:
        self.app._tab_cortes._search_bar._open_dialog()
        return self.cuts_get()

    def cuts_action(self, name: str) -> Dict[str, Any]:
        a, tab = self.app, self.app._tab_cortes
        {"template": a._save_import_template, "import": a._importar_excel,
         "export_pdf": a._exportar_pdf, "export_xlsx": a._exportar_xlsx,
         "export_dxf": tab._export_cut_dxf, "add_field": tab._add_custom_field,
         "edit_fields": tab._open_fields_editor}[name]()
        return self.cuts_get()

    def cut_piece_dialog(self, i: int) -> Dict[str, Any]:
        """Open the native cut-drawing editor for row i (same as the Qt row)."""
        tab = self.app._tab_cortes
        if 0 <= i < len(tab._rows):
            row = tab._rows[i]
            c = row.get_corte()
            if c is not None:
                self.app._tab_nesting._open_cut_piece_in_profile_creator(c)
        return self.cuts_get()

    # ── jobs ────────────────────────────────────────────────────────────────
    def jobs_list(self) -> Dict[str, Any]:
        from nestube.database import get_geometry_db
        jobs = get_geometry_db().list_jobs_summary()
        out = []
        for j in jobs:
            from nestube.naming import format_full_name
            out.append({"id": j["id"], "name": j.get("name") or f"Job #{j['id']}",
                        "client": j.get("client") or "", "offer": j.get("offer") or "",
                        "order": j.get("order_ref") or "", "desc": j.get("description") or "",
                        "created": (j.get("created_at") or "")[:16], "updated": (j.get("updated_at") or "")[:16],
                        "material": format_full_name(j.get("profile_name") or "", j.get("mat_name") or "", "").strip()})
        return {"jobs": out, "current": getattr(self.app, "_current_job_id", None)}

    def job_detail(self, id: int) -> Dict[str, Any]:
        from nestube.database import get_geometry_db
        from nestube.naming import format_full_name
        db = get_geometry_db()
        sd = db.get_job_state(int(id)) or {}
        mats, pieces, stock_lines = [], [], []
        for mc in sd.get("material_contexts") or []:
            label = format_full_name(mc.get("profile_name", ""), mc.get("material", ""),
                                     mc.get("quality", "")).strip(" ·")
            if label:
                mats.append(label)
            for c in mc.get("cortes") or []:
                pieces.append({"name": c.get("descripcion") or "", "len": c.get("largo", 0),
                               "qty": c.get("cantidad", 1), "material": label})
            if mc.get("use_stock") and int(mc.get("nesting_bars_deducted", 0) or 0) > 0:
                stock_lines.append(t("jobs_stock_used_line", name=mc.get("linked_stock_bar_name", ""),
                                     count=int(mc.get("nesting_bars_deducted", 0))))
        if not pieces:
            for c in sd.get("cortes") or []:
                pieces.append({"name": c.get("descripcion") or "", "len": c.get("largo", 0),
                               "qty": c.get("cantidad", 1), "material": ""})
        n_bars = sum(len([b for b in (mc.get("nesting_layout") or []) if b])
                     for mc in sd.get("material_contexts") or [])
        job = next((j for j in db.list_jobs_summary() if j["id"] == int(id)), {})
        retales = []
        try:
            from nestube.stock_db import get_bars_by_creation_job
            retales = [t("jobs_retal_line", name=b.profile_name or b.display_name, length=b.retal_length)
                       for b in get_bars_by_creation_job(job.get("name", "")) if b.is_retal]
        except Exception:
            pass
        return {"id": int(id), "name": job.get("name", ""), "client": job.get("client") or "",
                "offer": job.get("offer") or "", "order": job.get("order_ref") or "",
                "desc": job.get("description") or "", "created": (job.get("created_at") or "")[:16],
                "materials": mats, "pieces": pieces, "bars": n_bars,
                "stock": stock_lines, "retales": retales}

    def job_open(self, id: int) -> Dict[str, Any]:
        self.app._tab_jobs._open_job(int(id))
        return {"view": _VIEWS[self.app._tabs.currentIndex()], "job": self.job_header()}

    def job_new(self) -> Dict[str, Any]:
        self.app._tab_jobs._new_job()
        return {"view": _VIEWS[self.app._tabs.currentIndex()], "job": self.job_header()}

    def job_save_meta(self, id: int, client: str = "", offer: str = "", order: str = "",
                      desc: str = "") -> Dict[str, Any]:
        from nestube.database import get_geometry_db
        get_geometry_db().update_job_meta(int(id), description=desc, client=client,
                                          offer=offer, order_ref=order)
        if int(id) == getattr(self.app, "_current_job_id", None):
            self.state.cliente, self.state.oferta, self.state.pedido = client, offer, order
        return self.job_detail(id)

    def job_delete(self, id: int) -> Dict[str, Any]:
        from nestube.database import get_geometry_db
        get_geometry_db().delete_job(int(id))
        if getattr(self.app, "_current_job_id", None) == int(id):
            self.app._current_job_id = None
        return self.jobs_list()

    # ── costs ───────────────────────────────────────────────────────────────
    def costs_get(self) -> Dict[str, Any]:
        tp = self.app._tab_perfiles
        ui = tp.ui
        ctx = self._ctx()
        fields = {
            "kg_m": ui.e_kg_m.text(), "dens": ui.e_peso_esp.text(), "wall": ui.e_espesor.text(),
            "solid": ui.cb_macizo.isChecked(), "price_kg": ui.e_precio_kg.text(),
            "price_m": ui.e_precio_m.text(), "price_bar": ui.e_precio_barra.text(),
            "margin": ui.e_margen_beneficio.text(), "currency": ui.currency_combo.currentData() or "EUR",
            "t_cut": ui.e_t_recto.text(), "miter": ui.e_pct_inglete.text(), "op": ui.e_coste_op.text(),
            "mode": app_config.get().cost_mode, "scrap": ui.cb_retales.isChecked(),
            "confirm": ui.cb_confirm_costs.isChecked(),
        }
        currencies = [[ui.currency_combo.itemData(i), ui.currency_combo.itemText(i)]
                      for i in range(ui.currency_combo.count())]
        dims = [[k, tp._dim_entries[k].text()] for k in tp._dim_entries]
        results, total = self._cost_results(ctx)
        from nestube.context_sync import layout_covers_all_cuts
        totals, grand = [], 0.0
        if getattr(tp, "_on_total_tab", False):
            from nestube.logic import calcular_resultado
            from nestube.naming import context_tab_label
            for i, c in enumerate(self.state.material_contexts):
                if not c.cortes or c.perfil is None:
                    continue
                try:
                    barras = tp._barras_for_costing(c)
                    n_ing = sum(1 for k in c.cortes if k.inglete1 or k.inglete2)
                    sub = sum(calcular_resultado(k, c.perfil, barras, c.longitud_barra, n_ing).precio_total_linea
                              for k in c.cortes)
                except Exception:
                    continue
                grand += sub
                totals.append({"name": context_tab_label(c, i), "total": sub})
        return {"fields": fields, "currencies": currencies, "dims": dims,
                "totals": totals, "grand": grand,
                "profile_key": getattr(tp, "_profile_key", "") or "",
                "profile": self._profile_card(),
                "profiles": self._profile_choices(),
                "results": results, "total": total,
                "using_nesting": bool(layout_covers_all_cuts(ctx)) if ctx.cortes else False,
                "total_view": bool(getattr(tp, "_on_total_tab", False))}

    def _cost_results(self, ctx):
        from nestube.logic import calcular_resultado
        tp = self.app._tab_perfiles
        perfil = self.state.perfil
        if not ctx.cortes or perfil is None or not getattr(tp, "_results_ready", True):
            return [], 0.0
        try:
            barras = tp._barras_for_costing(ctx)
            n_ing = sum(1 for c in ctx.cortes if c.inglete1 or c.inglete2)
            rows, total = [], 0.0
            for c in ctx.cortes:
                r = calcular_resultado(c, perfil, barras, ctx.longitud_barra, n_ing)
                total += r.precio_total_linea
                rows.append({"name": r.descripcion, "len": r.largo, "qty": r.cantidad,
                             "kg": r.kg_ud, "m2": r.m2_ud, "mat": r.precio_material_ud,
                             "labour": r.coste_mano_obra_ud, "unit": r.precio_total_ud,
                             "per_m": r.precio_m, "line": r.precio_total_linea})
            return rows, total
        except Exception:
            return [], 0.0

    def _profile_card(self) -> Dict[str, Any]:
        tp = self.app._tab_perfiles
        e = getattr(tp, "_catalog_entry", None)
        if e is not None:
            m = e.meta or {}
            return {"key": f"custom:{e.name}", "name": e.name, "material": m.get("material", ""),
                    "image": _file_url(os.path.join(app_config.PROFILES_DIR, e.image)) if e.image else "",
                    "h": m.get("h"), "b": m.get("b"), "tw": m.get("tw"), "tf": m.get("tf"),
                    "section": m.get("seccion_cm2"), "kg_m": m.get("peso_lineal_kg_m"), "locked": True}
        key = getattr(tp, "_profile_key", "") or ""
        from nestube.ui_qt.tab_perfiles import _builtin_profiles
        label = next((lbl for k, _tp, lbl in _builtin_profiles() if k == key), key)
        return {"key": key, "name": label, "material": "", "image": "", "locked": False}

    def _profile_choices(self) -> List[Dict[str, Any]]:
        from nestube.ui_qt.tab_perfiles import _builtin_profiles
        out = [{"key": k, "name": lbl, "builtin": True, "type": tp.value, "image": ""}
               for k, tp, lbl in _builtin_profiles()]
        for cp in app_config.get().custom_profiles:
            out.append({"key": f"custom:{cp.name}", "name": cp.name, "builtin": False,
                        "material": (cp.meta or {}).get("material", ""),
                        "image": _file_url(os.path.join(app_config.PROFILES_DIR, cp.image)) if cp.image else ""})
        usage = getattr(app_config.get(), "profile_usage", {}) or {}
        for o in out:
            o["uses"] = usage.get(o["key"], 0)
        return out

    def costs_set(self, fields: Optional[dict] = None, dims: Optional[dict] = None) -> Dict[str, Any]:
        tp = self.app._tab_perfiles
        ui = tp.ui
        f = fields or {}
        for key, w in (("kg_m", ui.e_kg_m), ("wall", ui.e_espesor), ("price_kg", ui.e_precio_kg),
                       ("price_m", ui.e_precio_m), ("price_bar", ui.e_precio_barra),
                       ("margin", ui.e_margen_beneficio), ("t_cut", ui.e_t_recto),
                       ("miter", ui.e_pct_inglete), ("op", ui.e_coste_op)):
            if key in f:
                w.setText(str(f[key]))
        if "dens" in f and ui.e_peso_esp.isEnabled():
            ui.e_peso_esp.setText(str(f["dens"]))
        if "solid" in f:
            ui.cb_macizo.setChecked(bool(f["solid"]))
        if "scrap" in f:
            ui.cb_retales.setChecked(bool(f["scrap"]))
        if "confirm" in f:
            ui.cb_confirm_costs.setChecked(bool(f["confirm"]))
        if "currency" in f:
            j = ui.currency_combo.findData(f["currency"])
            if j >= 0:
                ui.currency_combo.setCurrentIndex(j)
        if "mode" in f:
            j = ui.cost_mode_combo.findData(f["mode"])
            if j >= 0:
                ui.cost_mode_combo.setCurrentIndex(j)
        for k, v in (dims or {}).items():
            if k in tp._dim_entries:
                tp._dim_entries[k].setText(str(v))
        return self.costs_get()

    def costs_select_profile(self, key: str) -> Dict[str, Any]:
        self.app._tab_perfiles._select_profile(key)
        return self.costs_get()

    def costs_calc(self) -> Dict[str, Any]:
        # The web UI already asked for confirmation (when enabled).
        self.app._tab_perfiles._calcular()
        return self.costs_get()

    def costs_action(self, name: str) -> Dict[str, Any]:
        tp = self.app._tab_perfiles
        {"clear": tp._limpiar, "excel": tp._export_excel, "pdf": tp._export_pdf,
         "docx": tp._export_docx, "print": tp._print, "edit_material": tp._edit_catalog_material,
         "material_search": tp._mat_search_bar._open_dialog}[name]()
        return self.costs_get()

    # ── profiles catalogue ──────────────────────────────────────────────────
    def profiles_list(self) -> Dict[str, Any]:
        from nestube.naming import localize_material
        items = []
        for e in app_config.get().custom_profiles:
            m = e.meta or {}
            items.append({"id": e.id, "name": e.name, "material": localize_material(m.get("material", "")),
                          "family": m.get("family") or m.get("geometry_type") or "",
                          "geometry": m.get("geometry_type") or "", "quality": e.quality or m.get("quality", ""),
                          "h": m.get("h"), "b": m.get("b"), "tw": m.get("tw"), "tf": m.get("tf"),
                          "section": m.get("seccion_cm2"), "kg_m": m.get("peso_lineal_kg_m"),
                          "image": _file_url(os.path.join(app_config.PROFILES_DIR, e.image)) if e.image else "",
                          "custom": bool(e.drawing_shapes) and not str(e.id).startswith("catalog-")})
        return {"profiles": items}

    def profiles_action(self, name: str, id: str = "") -> Dict[str, Any]:
        tm = self.app._tab_materiales
        if name == "edit" and id:
            from nestube.ui_qt.dialogs.profile_manager import ProfileManager
            ProfileManager(self.app, on_change=tm._on_change_proxy, initial_select_id=id).exec()
        elif name == "materials":
            tm._edit_materials()
        elif name == "manager":
            self.app._open_profile_manager()
        elif name == "creator_native":
            self.app._open_profile_creator()
        elif name == "use_in_costs" and id:
            e = next((p for p in app_config.get().custom_profiles if p.id == id), None)
            if e is not None:
                self.app._tab_perfiles._select_profile(f"custom:{e.name}")
        tm.refresh()
        self.app._tab_perfiles.refresh_profile_selector()
        return self.profiles_list()

    def save_drawing(self, shapes: List[dict], meta: Optional[dict] = None,
                     sides: Optional[List[dict]] = None) -> Dict[str, Any]:
        """Persist a profile drawn in the web drawing module (asks for the name
        and fields in the app's profile-save dialog, then stores it)."""
        self.app._save_profile_drawing(shapes, meta or {}, sides or [])
        self.app._tab_materiales.refresh()
        return self.profiles_list()

    # ── stock ───────────────────────────────────────────────────────────────
    def stock_list(self) -> Dict[str, Any]:
        from nestube.stock_db import get_stock
        db = get_stock()
        bars = []
        for b in db.bars:
            bars.append({"id": b.id, "profile": b.profile_name, "material": b.material_desc,
                         "quality": b.quality, "name": getattr(b, "display_name", "") or b.profile_name,
                         "len": b.retal_length if b.is_retal else b.length, "qty": b.quantity,
                         "available": b.quantity > 0, "retal": b.is_retal,
                         "created_in": b.creation_job_name, "used_in": list(b.used_in_job_names or [])})
        return {"bars": bars, "min_retal": db.min_retal_length}

    def stock_action(self, name: str, ids: Optional[List[str]] = None, value: Any = None) -> Dict[str, Any]:
        from nestube.stock_db import get_stock, remove_bar, save_stock
        ts = self.app._tab_stock
        if name == "add":
            ts._add_bar_dialog()
        elif name == "edit" and ids:
            bar = next((b for b in get_stock().bars if b.id == ids[0]), None)
            if bar is not None:
                ts._open_stock_dialog(bar)
        elif name == "delete" and ids:
            for bid in ids:
                remove_bar(bid)
        elif name == "export":
            ts._export_stock()
        elif name == "min_retal":
            db = get_stock()
            db.min_retal_length = _num(value, db.min_retal_length)
            save_stock()
        ts._refresh_list()
        return self.stock_list()

    # ── menus & settings ────────────────────────────────────────────────────
    def menu(self, name: str, value: Any = None) -> Dict[str, Any]:
        a = self.app
        actions = {
            "open": a._abrir, "save": a._guardar, "save_as": a._guardar_como,
            "save_config": a._save_app_config, "load_config": a._load_app_config,
            "backups": a._open_backups, "db": a._open_db_management,
            "material_add": a._add_new_material, "materials": a._manage_materials,
            "profile_creator_native": a._open_profile_creator, "profile_manager": a._open_profile_manager,
            "pdf_font": a._configure_pdf_font, "pdf_template": a._configure_pdf_template,
            "pdf_templates": a._open_edit_templates, "cost_defaults": a._configure_cost_defaults,
            "opt_times": a._configure_opt_times, "nesting_layout": a._configure_nesting_layout,
            "naming": a._configure_naming, "reset": a._reset_settings, "about": a._show_about,
            "github": a._open_github, "donate": a._open_donate,
        }
        if name == "theme":
            a._set_theme(str(value))
        elif name == "language":
            a._set_language(str(value))
        elif name == "units":
            a._set_unit_system(str(value))
        elif name == "cut_colors":
            a._toggle_cut_colors(bool(value))
        elif name == "exit":
            from PySide6.QtCore import QTimer
            if self.b.window is not None:
                QTimer.singleShot(0, self.b.window.close)
        elif name in actions:
            actions[name]()
        else:
            raise AttributeError(f"unknown menu action {name!r}")
        return self.boot()
