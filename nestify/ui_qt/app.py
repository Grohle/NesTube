"""
nestify/ui_qt/app.py
NestifyApp — QMainWindow, menu bar, QTabWidget, shared AppState.
"""
from __future__ import annotations

import os
import shutil
import uuid
import webbrowser
from typing import Optional

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QInputDialog, QMainWindow,
    QMessageBox, QTabWidget,
)

from nestify import app_config, units
from nestify.app_config import AppPreferences, CustomProfileEntry
from nestify.context_sync import (
    ensure_material_contexts, load_context_to_state,
    save_cuts_tab_to_context, save_state_to_context,
)
from nestify.i18n import available_languages, set_language, t
from nestify.models import AppState
from nestify.resources import icon_png_path
from nestify.ui_qt.tab_cortes import TabCortes
from nestify.ui_qt.tab_jobs import TabJobsExplorer
from nestify.ui_qt.tab_materiales import TabMateriales
from nestify.ui_qt.tab_nesting import TabNesting
from nestify.ui_qt.tab_perfiles import TabPerfiles
from nestify.ui_qt.tab_stock import TabStock
from nestify.ui_qt.theme_qt import apply_theme, build_palette, build_stylesheet

_WIN_W = 1280
_WIN_H = 800
_WIN_MIN_W = 900
_WIN_MIN_H = 580

_JOB_EXT = ".nestjob"
_current_filepath: Optional[str] = None


class NestifyApp(QMainWindow):
    """Root application window."""

    def __init__(self) -> None:
        super().__init__()

        self._prefs = app_config.load()
        self._apply_preferences(self._prefs)

        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(_WIN_MIN_W, _WIN_MIN_H)
        self._apply_window_icon()

        self._state = AppState(
            language=self._prefs.language,
            calc_system=self._prefs.calc_system,
            currency=self._prefs.currency,
        )

        self._last_main_tab = 0
        # ID of the job currently open from the database; None for a new unsaved job.
        # Set by tab_jobs when a job is opened so Ctrl+S updates the same row.
        self._current_job_id: Optional[int] = None

        self._build_menu()
        self._build_tabs()
        self._restore_geometry()
        # Baseline for the unsaved-changes guard (a fresh, empty job is "clean").
        self._clean_snapshot = ""
        self._mark_clean()

        if self._prefs.show_about_on_startup:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(800, self._show_about_startup)

    def _apply_preferences(self, prefs: AppPreferences) -> None:
        set_language(prefs.language)
        units.set_unit_system(prefs.unit_system)
        apply_theme(prefs.theme)
        app = QApplication.instance()
        if app:
            from PySide6.QtWidgets import QToolTip
            pal = build_palette(prefs.theme)
            app.setPalette(pal)
            app.setStyleSheet(build_stylesheet(prefs.theme))
            QToolTip.setPalette(pal)

    def _sync_prefs_from_state(self) -> None:
        self._prefs.language = self._state.language
        self._prefs.calc_system = self._state.calc_system
        self._prefs.currency = self._state.currency
        app_config.save(self._prefs)

    # ── Menu Bar ─────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        menubar.clear()

        # File
        file_menu = menubar.addMenu(t("file"))
        file_menu.addAction(t("open"), self._abrir)
        _save_action = file_menu.addAction(t("save"), self._guardar)
        from PySide6.QtGui import QKeySequence
        _save_action.setShortcut(QKeySequence("Ctrl+S"))
        file_menu.addAction(t("save_as"), self._guardar_como)
        file_menu.addSeparator()
        file_menu.addAction(t("save_app_config"), self._save_app_config)
        file_menu.addAction(t("load_app_config"), self._load_app_config)
        file_menu.addAction(t("backups"), self._open_backups)
        file_menu.addAction(t("db_management"), self._open_db_management)
        file_menu.addSeparator()
        file_menu.addAction(t("exit"), self.close)

        # View
        view_menu = menubar.addMenu(t("view"))
        theme_menu = view_menu.addMenu(t("theme"))
        for mode, label in [("dark", t("dark")), ("light", t("light"))]:
            theme_menu.addAction(label, lambda m=mode: self._set_theme(m))

        # Font-size selection removed (§27): the app uses a fixed, consistent
        # type scale. A leftover negative offset could also drive a QSS font-size
        # to <=0 ("QFont::setPointSize: Point size <= 0"); sizes are now clamped.

        lang_menu = view_menu.addMenu(t("language"))
        lang_labels = {"en": "English", "es": "Español"}
        for code in available_languages():
            lang_menu.addAction(lang_labels.get(code, code),
                                lambda c=code: self._set_language(c))

        units_menu = view_menu.addMenu(t("unit_system"))
        units_menu.addAction(t("metric"), lambda: self._set_unit_system("metric"))
        units_menu.addAction(t("imperial"), lambda: self._set_unit_system("imperial"))

        # Color-per-cut toggle for the nesting canvas (checkable).
        self._cut_colors_action = view_menu.addAction(t("nesting_use_cut_colors"))
        self._cut_colors_action.setCheckable(True)
        self._cut_colors_action.setChecked(bool(self._prefs.nesting_use_cut_colors))
        self._cut_colors_action.toggled.connect(self._toggle_cut_colors)

        # Settings
        settings_menu = menubar.addMenu(t("settings"))

        # Calculation-system selection now lives in the Cuts tab toolbar
        # (calc_combo_cuts), so it is no longer duplicated here in Settings.

        # Cost mode and currency are no longer here — cost management is
        # centralised in the Costing tab (cost_mode_combo / currency_combo).

        materials_menu = settings_menu.addMenu(t("materials"))
        materials_menu.addAction(t("add_new_material"), self._add_new_material)
        materials_menu.addAction(t("manage_materials"), self._manage_materials)

        profiles_menu = settings_menu.addMenu(t("profile_types"))
        # Simplified: "Add new profile" opens the drawing module (blank);
        # "Edit profiles" lists saved profiles and re-opens the drawing module
        # pre-filled with each one's shapes/params.
        profiles_menu.addAction(t("add_new_profile"), self._open_profile_creator)
        profiles_menu.addAction(t("edit_profiles"), self._open_profile_manager)

        pdf_menu = settings_menu.addMenu(t("pdf_config"))
        pdf_menu.addAction(t("pdf_font"), self._configure_pdf_font)
        pdf_menu.addAction(t("pdf_template"), self._configure_pdf_template)
        pdf_menu.addAction(t("edit_templates"), self._open_edit_templates)

        settings_menu.addAction(t("cost_defaults"), self._configure_cost_defaults)
        settings_menu.addAction(t("opt_time_levels"), self._configure_opt_times)
        settings_menu.addAction(t("nesting_layout_settings"),
                                self._configure_nesting_layout)
        settings_menu.addAction(t("name_assignment"), self._configure_naming)
        settings_menu.addSeparator()
        settings_menu.addAction(t("reset_settings"), self._reset_settings)

        # About / Help
        about_menu = menubar.addMenu(t("about_menu"))
        about_menu.addAction(t("about_title"), self._show_about)

        help_menu = menubar.addMenu(t("help"))
        help_menu.addAction(t("github_issues"), self._open_github)

    # ── Tabs ─────────────────────────────────────────────────────────────────

    def _build_tabs(self) -> None:
        tabs = QTabWidget()
        tabs.currentChanged.connect(self._on_main_tab_changed)

        self._tab_jobs = TabJobsExplorer(app_ref=self)
        tabs.addTab(self._tab_jobs, t("tab_jobs"))

        self._tab_cortes = TabCortes(state=self._state)
        tabs.addTab(self._tab_cortes, t("tab_cuts"))

        # Import/export actions moved from the File menu into the Cuts toolbar
        # (TODO §1/§2.1). The cross-tab logic stays here (Export PDF needs the
        # nesting tab + multi-material flow), so wire the tab's buttons to it.
        self._tab_cortes.btn_template.clicked.connect(self._save_import_template)
        self._tab_cortes.btn_import.clicked.connect(self._importar_excel)
        self._tab_cortes.btn_export_pdf.clicked.connect(self._exportar_pdf)
        self._tab_cortes.btn_export_xlsx.clicked.connect(self._exportar_xlsx)

        # Live-sync offer/order/client fields from Cuts to Job Explorer detail panel.
        self._tab_cortes.ui.e_oferta.textChanged.connect(self._on_cuts_offer_changed)
        self._tab_cortes.ui.e_pedido.textChanged.connect(self._on_cuts_order_changed)
        self._tab_cortes.ui.e_cliente.textChanged.connect(self._on_cuts_client_changed)

        self._tab_nesting = TabNesting(state=self._state)
        tabs.addTab(self._tab_nesting, t("tab_nesting"))

        self._tab_perfiles = TabPerfiles(state=self._state, on_add_profile=self._open_profile_creator)
        tabs.addTab(self._tab_perfiles, t("tab_profiles"))

        self._tab_materiales = TabMateriales(
            on_add_profile=self._open_profile_creator,
            on_profiles_changed=self._tab_perfiles.refresh_profile_selector,
        )
        tabs.addTab(self._tab_materiales, t("tab_profiles_tubes").replace("&", "&&"))

        self._tab_stock = TabStock(state=self._state)
        tabs.addTab(self._tab_stock, t("tab_stock"))

        self.setCentralWidget(tabs)
        self._tabs = tabs

        # Wire the Nesting "Use stock" toggle to the cross-tab prefill flow.
        if hasattr(self._tab_nesting, "_stock_switch"):
            self._tab_nesting._stock_switch.toggled.connect(self._on_use_stock_toggled)

        # Ctrl+S inside the Nesting tab triggers the app-level save (§3.5).
        self._tab_nesting.save_requested.connect(self._guardar)

        # Clicking a job-name cell in the Stock tab navigates to Job Explorer (§11).
        self._tab_stock.open_job_requested.connect(self._navigate_to_job)

    def _navigate_to_job(self, job_name: str) -> None:
        """Switch to the Job Explorer tab and select the job matching job_name (§11)."""
        jobs_tab_idx = self._tabs.indexOf(self._tab_jobs)
        self._tabs.setCurrentIndex(jobs_tab_idx)
        self._tab_jobs.select_job_by_name(job_name)

    def _on_cuts_offer_changed(self, text: str) -> None:
        if self._tab_jobs._selected_job_id is not None:
            self._tab_jobs._detail_offer_lbl.setText(text)

    def _on_cuts_order_changed(self, text: str) -> None:
        if self._tab_jobs._selected_job_id is not None:
            self._tab_jobs._detail_order_lbl.setText(text)

    def _on_cuts_client_changed(self, text: str) -> None:
        if self._tab_jobs._selected_job_id is not None:
            self._tab_jobs._detail_client_lbl.setText(text)

    def _set_stock_fields_readonly(self, ro: bool) -> None:
        """Lock/unlock bar length & height fields (forced to the stock bar)."""
        for w in (self._tab_nesting.ui.tb_bar_len, self._tab_nesting.ui.tb_height):
            w.setReadOnly(ro)
        for w in (self._tab_cortes._e_bar_len, self._tab_cortes._e_bar_height):
            w.setReadOnly(ro)

    def _on_use_stock_toggled(self, checked: bool) -> None:
        """Replicate the legacy Use-stock flow: prefill costs/length/height from
        the matching stock bar across the Profiles/Cuts/Nesting tabs."""
        nt = self._tab_nesting
        if not checked:
            self._set_stock_fields_readonly(False)
            return
        from nestify.stock_prefill import prefill_active_material_from_stock
        from nestify.bevel_geom import profile_available_heights

        self._tab_cortes._sync_header()
        ensure_material_contexts(self._state)
        save_state_to_context(self._state, self._state.active_material_index)
        bar = prefill_active_material_from_stock(self._state)
        if bar is None:
            ctx = self._state.material_contexts[self._state.active_material_index]
            mat = (ctx.material or self._state.descripcion or "").strip()
            msg = (t("stock_none_for_material", material=mat) if mat
                   else t("stock_prefill_not_found"))
            QMessageBox.warning(self, t("warning"), msg)
            nt._stock_switch.setChecked(False)
            return
        if getattr(bar, "length", 0) and bar.length > 0:
            self._state.longitud_barra = bar.length
        save_state_to_context(self._state, self._state.active_material_index)
        if hasattr(self._tab_perfiles, "set_values") and self._state.perfil:
            self._tab_perfiles.set_values(self._state.perfil.to_dict())
        self._tab_cortes.refresh_bar_length()
        nt.refresh_kerf_margin_fields()
        # If several profile faces could serve as the cutting height, ask (and
        # remember per profile). Shared helper keeps Cuts/Nesting/Costs aligned.
        from nestify.ui_qt.cutting_height import resolve_cutting_height
        h = resolve_cutting_height(self, self._state)
        if h:
            nt._height_override = h
            nt.ui.tb_height.setText(f"{h:.0f}" if float(h) == int(h) else f"{h:.1f}")
        self._set_stock_fields_readonly(True)
        QMessageBox.information(self, t("info"), t("stock_prefill_done"))

    def _on_main_tab_changed(self, index: int) -> None:
        old = self._last_main_tab
        if old != index:
            if old == 2 and hasattr(self._tab_nesting, "has_unsaved_nesting_changes") \
                    and self._tab_nesting.has_unsaved_nesting_changes():
                reply = QMessageBox.question(
                    self,
                    t("unsaved_nesting_title"),
                    t("unsaved_nesting_msg"),
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Save,
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    self._tabs.blockSignals(True)
                    self._tabs.setCurrentIndex(old)
                    self._tabs.blockSignals(False)
                    return
                if reply == QMessageBox.StandardButton.Save:
                    self._tab_nesting._save_nesting()
            self._flush_main_tab(old)
        self._last_main_tab = index
        self._refresh_main_tab(index)

    def _flush_main_tab(self, index: int) -> None:
        ensure_material_contexts(self._state)
        idx = self._state.active_material_index
        if index == 1:
            self._state.reset_from(self._tab_cortes.get_current_state())
            save_cuts_tab_to_context(self._state, idx, list(self._state.cortes))
        elif index == 2:
            self._tab_nesting.sync_to_state()
            save_state_to_context(self._state, idx)
        elif index == 3:
            self._tab_perfiles._save_active_perfil()
            save_state_to_context(self._state, idx)

    def _refresh_main_tab(self, index: int) -> None:
        ensure_material_contexts(self._state)
        load_context_to_state(self._state, self._state.active_material_index)
        if index == 0:
            self._tab_jobs.refresh_list()
        elif index == 1 and hasattr(self._tab_cortes, '_apply_context_to_ui'):
            self._tab_cortes.sync_subtabs_bar()
            self._tab_cortes._apply_context_to_ui()
        elif index == 2:
            self._tab_nesting.refresh_from_cuts()
        elif index == 3 and hasattr(self._tab_perfiles, '_apply_context_to_ui'):
            # Mirror the Nesting/Cuts material sub-tabs before applying the
            # active context, so the Costs tab stays in sync (TODO §4).
            self._tab_perfiles.sync_subtabs_bar()
            self._tab_perfiles._apply_context_to_ui()
        elif index == 4 and hasattr(self._tab_materiales, 'refresh'):
            self._tab_materiales.refresh()
        elif index == 5 and hasattr(self._tab_stock, '_refresh_list'):
            self._tab_stock._refresh_list()

    # ── Theme / Language / Units ─────────────────────────────────────────────

    def _set_theme(self, mode: str) -> None:
        apply_theme(mode)
        app = QApplication.instance()
        if app:
            pal = build_palette(mode)
            app.setPalette(pal)
            app.setStyleSheet(build_stylesheet(mode))
            # Force tooltip windows to repick the new palette — they are
            # top-level windows and cache their own palette at first show.
            from PySide6.QtWidgets import QToolTip
            QToolTip.setPalette(pal)
        for attr in ('_tab_nesting', '_tab_jobs', '_tab_stock', '_tab_cortes', '_tab_perfiles',
                     '_tab_materiales'):
            tab = getattr(self, attr, None)
            if tab and hasattr(tab, 'refresh_theme'):
                tab.refresh_theme()
        self._prefs.theme = mode
        app_config.save(self._prefs)

    def _set_language(self, lang: str) -> None:
        # Live language switch — no restart, no data loss. We capture the full
        # working state, swap the locale, rebuild the menu + tabs (which re-read
        # every t() string in the new language), then reload the state into the
        # fresh tabs and return to the tab the user was on.
        self._flush_main_tab(self._tabs.currentIndex())
        self._state.reset_from(self._tab_cortes.get_current_state())
        self._tab_nesting.sync_to_state()
        save_state_to_context(self._state, self._state.active_material_index)
        active_tab = self._tabs.currentIndex()

        set_language(lang)
        self._state.language = lang
        self._prefs.language = lang
        app_config.save(self._prefs)

        # Reset the tab-change bookkeeping so the rebuild's construction-time
        # currentChanged(0) flushes the (no-op) Jobs tab, not a half-built one.
        self._last_main_tab = 0
        self._build_menu()
        self._build_tabs()
        self._load_state_into_all_tabs()
        if 0 <= active_tab < self._tabs.count():
            self._tabs.setCurrentIndex(active_tab)

    def _load_state_into_all_tabs(self) -> None:
        """Push self._state into every tab (used by Open and the live language
        switch). Mirrors the load path so freshly built tabs are populated."""
        self._tab_cortes.load_state(self._state)
        if hasattr(self._tab_nesting, "load_state"):
            self._tab_nesting.load_state(self._state)
        if self._state.perfil is not None:
            self._tab_perfiles.set_values(self._state.perfil.to_dict())
        if hasattr(self._tab_stock, "load_state"):
            self._tab_stock.load_state(self._state)

    def _set_unit_system(self, system: str) -> None:
        units.set_unit_system(system)
        self._prefs.unit_system = system
        app_config.save(self._prefs)
        QMessageBox.information(self, t("unit_system"), t("unit_system_set", system=system))

    def _set_calc_system(self, system: str) -> None:
        self._state.calc_system = system
        self._prefs.calc_system = system
        app_config.save(self._prefs)

    # Cost mode and currency are now managed in the Costing tab
    # (cost_mode_combo / currency_combo); the old Settings-menu handlers were
    # removed along with their submenus.

    def _configure_opt_times(self) -> None:
        """Edit auto-nest optimization time limits and refresh the level combo."""
        from nestify.ui_qt.dialogs.optimization_times_dialog import OptimizationTimesDialog
        if OptimizationTimesDialog(self).exec():
            if hasattr(self._tab_nesting, "refresh_opt_menu_labels"):
                self._tab_nesting.refresh_opt_menu_labels()
            QMessageBox.information(self, t("opt_time_levels"), t("opt_time_saved"))

    def _configure_cost_defaults(self) -> None:
        """Edit the global, profile-independent cost defaults for new jobs (§24)."""
        from nestify.ui_qt.dialogs.cost_defaults_dialog import CostDefaultsDialog
        if CostDefaultsDialog(self).exec():
            QMessageBox.information(self, t("cost_defaults"), t("cost_defaults_saved"))

    def _set_ui_font_family(self) -> None:
        """Choose the interface font family and apply it app-wide."""
        from PySide6.QtGui import QFont, QFontDialog
        # Seed with a font that has a valid point size; a family-only QFont has
        # pointSize -1, which makes Qt emit "QFont::setPointSize: Point size <= 0".
        _app = QApplication.instance()
        _seed = QFont(_app.font()) if _app else QFont()
        if self._prefs.ui_font_family:
            _seed.setFamily(self._prefs.ui_font_family)
        if _seed.pointSize() <= 0:
            _seed.setPointSize(10)
        font, ok = QFontDialog.getFont(_seed, self, t("ui_font"))
        if not ok:
            return
        family = font.family()
        self._prefs.ui_font_family = family
        app_config.save(self._prefs)
        app = QApplication.instance()
        if app:
            base = app.font()
            base.setFamily(family)
            app.setFont(base)
        QMessageBox.information(self, t("font_family"), f"{t('ui_font')}: {family}")

    def _toggle_cut_colors(self, checked: bool) -> None:
        """Toggle color-per-cut mode on the nesting canvas and persist it."""
        self._prefs.nesting_use_cut_colors = bool(checked)
        app_config.save(self._prefs)
        if hasattr(self._tab_nesting, "_rebuild_scene"):
            self._tab_nesting._rebuild_scene()

    # ── Materials / Profiles ─────────────────────────────────────────────────

    def _add_new_material(self) -> None:
        from nestify.ui_qt.dialogs.materials_manager import MaterialsManagerDialog
        dlg = MaterialsManagerDialog(self)
        dlg._clear_form()
        dlg.exec()

    def _manage_materials(self) -> None:
        from nestify.ui_qt.dialogs.materials_manager import MaterialsManagerDialog
        MaterialsManagerDialog(self).exec()

    def _open_profile_manager(self) -> None:
        from nestify.ui_qt.dialogs.profile_manager import ProfileManager
        ProfileManager(self, on_change=self._tab_perfiles.refresh_profile_selector).exec()

    def _open_profile_creator(self) -> None:
        from nestify.ui_qt.dialogs.profile_creator import ProfileCreator
        from nestify.ui_qt.dialogs.profile_save_dialog import ProfileSaveDialog

        def on_save(data):
            fields = data.get("fields", ["A (mm)", "B (mm)"])
            field_defaults = data.get("field_defaults", {})
            thumbnail_path = data.get("thumbnail_path", "")
            drawing_shapes = data.get("shapes", [])  # persist so it can be edited later
            meta = dict(data.get("meta", {}))         # full material data sheet
            manual_sides = list(data.get("manual_sides", []))

            def on_confirm(result):
                name = result["name"]
                quality = result.get("quality", "")
                notes = result.get("notes", "")
                final_fields = result.get("fields", fields)
                image_name = ""
                _MAX_THUMB = 10 * 1024 * 1024  # 10 MB
                if (thumbnail_path and os.path.isfile(thumbnail_path)
                        and os.path.getsize(thumbnail_path) <= _MAX_THUMB):
                    os.makedirs(app_config.PROFILES_DIR, exist_ok=True)
                    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
                    image_name = f"{safe}.png"
                    profiles_real = os.path.realpath(app_config.PROFILES_DIR)
                    dest = os.path.join(profiles_real, image_name)
                    if os.path.realpath(dest).startswith(profiles_real + os.sep):
                        shutil.copy2(thumbnail_path, dest)
                try:
                    if thumbnail_path:
                        os.remove(thumbnail_path)
                except OSError:
                    pass
                if result.get("material"):
                    meta["material"] = result["material"]
                    meta["specific_weight"] = result.get("specific_weight", 7.85)
                existing = next(
                    (p for p in self._prefs.custom_profiles if p.name.lower() == name.lower()), None
                )
                if existing:
                    existing.fields = final_fields
                    existing.quality = quality
                    existing.notes = notes
                    merged = dict(existing.field_defaults)
                    merged.update(field_defaults)
                    existing.field_defaults = merged
                    existing.drawing_shapes = drawing_shapes
                    existing.meta = meta
                    existing.manual_sides = manual_sides
                    if image_name:
                        existing.image = image_name
                    app_config.save_profile_file(existing)
                else:
                    entry = CustomProfileEntry(
                        id=uuid.uuid4().hex[:10], name=name, image=image_name,
                        quality=quality, notes=notes, fields=final_fields,
                        field_defaults=field_defaults,
                        drawing_shapes=drawing_shapes, meta=meta,
                        manual_sides=manual_sides,
                    )
                    self._prefs.custom_profiles.append(entry)
                    app_config.save_profile_file(entry)
                app_config.save(self._prefs)
                self._tab_perfiles.refresh_profile_selector()

            ProfileSaveDialog(self, fields=fields, on_confirm=on_confirm).exec()

        ProfileCreator(self, on_save=on_save).exec()

    def _add_profile_type(self) -> None:
        name, ok = QInputDialog.getText(self, t("add_profile_type"), t("field_name") + ":")
        if not ok or not name.strip():
            return
        name = name.strip()
        count, ok2 = QInputDialog.getInt(
            self, t("add_profile_type"), t("custom_field_count"), 2, 1, 20,
        )
        if not ok2:
            count = 2
        fields = []
        for idx in range(count):
            fld, ok3 = QInputDialog.getText(
                self, t("add_profile_type"), t("custom_field_name_n", n=str(idx + 1)),
            )
            if ok3 and fld.strip():
                fields.append(fld.strip())
        if not fields:
            fields = ["A (mm)", "B (mm)"]

        existing = next(
            (p for p in self._prefs.custom_profiles if p.name.lower() == name.lower()), None
        )
        if existing:
            existing.fields = fields
            target = existing
        else:
            target = CustomProfileEntry(
                id=uuid.uuid4().hex[:10], name=name, fields=fields,
            )
            self._prefs.custom_profiles.append(target)
        app_config.save(self._prefs)
        app_config.save_profile_file(target)
        self._tab_perfiles.refresh_profile_selector()

    # ── PDF / Nesting config ─────────────────────────────────────────────────

    def _configure_pdf_font(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("pdf_font"), "", "TrueType Font (*.ttf);;All (*.*)",
        )
        if path:
            self._prefs.pdf_font_regular = path
            bold = path.replace(".ttf", "bd.ttf").replace("Regular", "Bold")
            self._prefs.pdf_font_bold = bold if os.path.isfile(bold) else path
            app_config.save(self._prefs)

    def _configure_pdf_template(self) -> None:
        """Open a file picker for the FastReport .frx template, then launch it in the system-associated designer."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        path, _ = QFileDialog.getOpenFileName(
            self, t("pdf_template"), "", "FastReport (*.frx *.fr3);;All (*.*)",
        )
        if not path:
            return
        self._prefs.pdf_fastreport_path = path
        app_config.save(self._prefs)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_pdf_template_editor(self) -> None:
        self._open_edit_templates()

    def _open_edit_templates(self) -> None:
        from nestify.ui_qt.dialogs.pdf_template_editor import EditTemplatesDialog
        EditTemplatesDialog(self).exec()

    def _configure_nesting_layout(self) -> None:
        from nestify.ui_qt.dialogs.nesting_layout_dialog import NestingLayoutDialog

        def _on_layout_apply() -> None:
            prefs = app_config.get()
            self._cut_colors_action.setChecked(bool(prefs.nesting_use_cut_colors))
            if hasattr(self._tab_nesting, "_rebuild_scene"):
                self._tab_nesting._rebuild_scene()
            if hasattr(self._tab_nesting, "_apply_panel_sides"):
                self._tab_nesting._apply_panel_sides()

        NestingLayoutDialog(self, on_apply=_on_layout_apply).exec()

    def _configure_naming(self) -> None:
        from nestify.ui_qt.dialogs.naming_dialog import NamingDialog
        NamingDialog(self).exec()

    def _reset_settings(self) -> None:
        reply = QMessageBox.question(self, t("reset_settings"), t("reset_settings_confirm"))
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._prefs = AppPreferences()
        app_config.save(self._prefs)
        self._apply_preferences(self._prefs)
        self._state.language = "en"
        self._state.calc_system = "ffd"
        self._state.currency = "EUR"
        self._build_menu()

    # ── File operations ──────────────────────────────────────────────────────

    def _abrir(self) -> None:
        global _current_filepath
        import json as _json
        filepath, _ = QFileDialog.getOpenFileName(
            self, t("open_job_title"), "",
            f"{t('job_filter_nestjob')} (*{_JOB_EXT});;"
            f"{t('job_filter_json')} (*.json);;"
            f"{t('job_filter_all')} (*{_JOB_EXT} *.json)",
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                raw = _json.load(fh)
            loaded = AppState.from_dict(raw)
        except Exception as exc:
            QMessageBox.critical(self, t("open_error"), t("open_fail_msg", error=str(exc)))
            return
        _current_filepath = filepath
        # Opening a file is NOT the same DB job: clear the tracked id so the next
        # Ctrl+S inserts a fresh row instead of overwriting whatever DB job was
        # previously loaded (which corrupted that unrelated job).
        self._current_job_id = None
        self._state.reset_from(loaded)
        self._tab_cortes.load_state(self._state)
        if hasattr(self._tab_nesting, 'load_state'):
            self._tab_nesting.load_state(self._state)
        self._tab_perfiles.set_values(self._state.perfil.to_dict())
        if hasattr(self._tab_stock, 'load_state'):
            self._tab_stock.load_state(self._state)
        # Restore the saved active tab and refresh it (mirrors _open_job) so the
        # opened file shows correct UI for every tab, not just Cuts.
        active_tab = getattr(self._state, "active_tab", 0)
        if 0 <= active_tab < self._tabs.count():
            self._tabs.setCurrentIndex(active_tab)
        self._refresh_main_tab(self._tabs.currentIndex())
        self._mark_clean()

    def _guardar(self) -> None:
        self._flush_main_tab(self._tabs.currentIndex())
        self._state.reset_from(self._tab_cortes.get_current_state())
        self._tab_nesting.sync_to_state()
        save_state_to_context(self._state, self._state.active_material_index)
        self._save_job_to_db()
        self._mark_clean()

    def _guardar_como(self) -> None:
        global _current_filepath
        import json as _json
        self._flush_main_tab(self._tabs.currentIndex())
        self._state.reset_from(self._tab_cortes.get_current_state())
        self._tab_nesting.sync_to_state()
        save_state_to_context(self._state, self._state.active_material_index)
        filepath, _ = QFileDialog.getSaveFileName(
            self, t("save_job_title"), "",
            f"{t('job_filter_nestjob')} (*{_JOB_EXT});;"
            f"{t('job_filter_json')} (*.json)",
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", encoding="utf-8") as fh:
                _json.dump(self._state.to_dict(), fh, ensure_ascii=False, indent=2)
            _current_filepath = filepath
            self._mark_clean()
            QMessageBox.information(self, t("save_ok"), t("save_ok_msg"))
        except Exception as exc:
            QMessageBox.critical(self, t("save_error"), t("save_fail_msg", error=str(exc)))

    @staticmethod
    def _generate_job_name() -> str:
        from datetime import datetime
        from nestify.database import get_geometry_db
        prefs = app_config.get()
        prefix = prefs.job_name_prefix or "JOB"
        date_str = datetime.now().strftime("%y%m%d")
        try:
            db = get_geometry_db()
            jobs = db.list_jobs_summary()
            day_prefix = f"{prefix}-{date_str}-"
            seq = 1
            for j in jobs:
                n = j.get("name", "")
                if n.startswith(day_prefix):
                    try:
                        seq = max(seq, int(n[len(day_prefix):]) + 1)
                    except ValueError:
                        pass
        except Exception:
            seq = 1
        return f"{prefix}-{date_str}-{seq:04d}"

    def _save_job_to_db(self, silent: bool = False) -> None:
        try:
            import json as _json
            from nestify.database import get_geometry_db
            db = get_geometry_db()
            # Remember which main tab the user was on so re-opening the job
            # lands them back where they left off (not always on Cuts).
            self._state.active_tab = self._tabs.currentIndex()
            state_dict = self._state.to_dict()
            file_path = _current_filepath or ""
            # A job's name is ALWAYS the auto-generated job number — no
            # exception, no override: never the material/description, never a
            # file name, never a user edit. Generated once when the job is
            # first created and kept stable on every subsequent save.
            existing_id = getattr(self, "_current_job_id", None)
            name = ""
            if existing_id is not None:
                for j in db.list_jobs_summary():
                    if j.get("id") == existing_id:
                        name = j.get("name") or ""
                        break
            if not name:
                name = self._generate_job_name()
            saved_id = db.upsert_job(
                name=name, state_json=_json.dumps(state_dict, ensure_ascii=False),
                description=self._state.descripcion, client=self._state.cliente,
                offer=self._state.oferta, order_ref=self._state.pedido, file_path=file_path,
                job_id=existing_id,
            )
            # Track the DB row so future Ctrl+S calls update the same record.
            self._current_job_id = saved_id
            self._tab_jobs.refresh_list()
            if not silent:
                QMessageBox.information(self, t("jobs_open"), t("job_saved_ok"))
        except Exception as exc:
            if not silent:
                QMessageBox.critical(self, t("open_error"), str(exc))

    def _save_app_config(self) -> None:
        self._sync_prefs_from_state()
        if app_config.save(self._prefs):
            QMessageBox.information(self, t("save_app_config"), t("config_saved"))

    def _open_backups(self) -> None:
        from nestify.ui_qt.dialogs.backup_dialog import BackupDialog
        BackupDialog(self).exec()

    def _open_db_management(self) -> None:
        from nestify.ui_qt.dialogs.database_management_dialog import DatabaseManagementDialog
        DatabaseManagementDialog(self).exec()

    def _load_app_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("load_app_config"),
            os.path.dirname(app_config.get_config_path()),
            "JSON (*.json);;All (*.*)",
        )
        if not path:
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            prefs = AppPreferences.from_dict(raw)
            self._prefs = prefs
            app_config.save(prefs)
            self._apply_preferences(prefs)
            self._state.language = prefs.language
            self._state.calc_system = prefs.calc_system
            self._state.currency = prefs.currency
        except Exception as exc:
            QMessageBox.critical(self, t("config_error"), str(exc))

    def _importar_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("import_excel"), "", "Excel (*.xlsx *.xls);;All (*.*)",
        )
        if not path:
            return
        try:
            from nestify.excel_import import import_cuts_from_excel
            cuts = import_cuts_from_excel(path)
            if not cuts:
                QMessageBox.warning(self, t("import_excel"), t("import_error"))
                return
            # get_current_state() flushes the UI into BOTH state.cortes and the
            # active material context. The imported cuts must be written into the
            # active context too — load_state repaints the cut rows from
            # ctx.cortes, so extending only state.cortes would silently drop them
            # (the "import shows no cuts" bug, §27).
            state = self._tab_cortes.get_current_state()
            ensure_material_contexts(state)
            ctx = state.material_contexts[state.active_material_index]
            combined = list(ctx.cortes) + list(cuts)
            ctx.cortes = combined
            state.cortes = list(combined)
            self._tab_cortes.load_state(state)
            QMessageBox.information(self, t("import_excel"), t("import_success", n=len(cuts)))
        except Exception as e:
            QMessageBox.critical(self, t("import_error"), str(e))

    def _save_import_template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, t("save_template"), "nestify_import_template.xlsx", "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from nestify.excel_import import save_template
            save_template(path)
        except Exception as e:
            QMessageBox.critical(self, t("import_error"), str(e))

    def _exportar_xlsx(self) -> None:
        state = self._tab_cortes.get_current_state()
        if not state.cortes:
            QMessageBox.warning(self, t("export_xlsx"), t("no_cuts_to_export"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_xlsx"), "nestify_cuts.xlsx", "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from nestify.cuts_export import export_cuts_to_excel
            export_cuts_to_excel(path, state.cortes)
            QMessageBox.information(self, t("export_xlsx"), t("export_xlsx_ok", n=len(state.cortes)))
        except Exception as e:
            QMessageBox.critical(self, t("export_xlsx"), str(e))

    def _exportar_pdf(self) -> None:
        from nestify.export_utils import exportar_pdf, _next_number
        from nestify.context_sync import effective_barras, recompute_auto_barras

        self._state.reset_from(self._tab_cortes.get_current_state())
        if hasattr(self._tab_nesting, 'sync_to_state'):
            self._tab_nesting.sync_to_state()
        ensure_material_contexts(self._state)
        save_state_to_context(self._state, self._state.active_material_index)

        # Determine which material contexts to include.
        contexts = self._state.material_contexts or []
        # Per §2.1 this export covers the cut list + bin-packing. A context that
        # has cuts but no nesting/bin-packing yet would otherwise raise "no
        # nesting data" and look like it wiped the preview — instead quick-pack it
        # now. effective_barras already returns a real (manual) layout when one
        # exists, so this NEVER overwrites a completed manual nesting.
        calc_sys = getattr(self._state, "calc_system", "ffd") or "ffd"
        for ctx in contexts:
            if ctx.cortes and not effective_barras(ctx):
                recompute_auto_barras(ctx, calc_system=calc_sys)
        contexts_with_data = [i for i, ctx in enumerate(contexts) if effective_barras(ctx)]
        # Always export via material_contexts (which reads effective_barras per
        # context) rather than state.barras_necesarias — the latter is empty for a
        # freshly quick-packed single context, which caused a spurious
        # "no nesting data" even though the cuts were just packed.
        material_contexts = [contexts[i] for i in contexts_with_data] or None

        if len(contexts_with_data) > 1:
            from nestify.ui_qt.dialogs.nesting_selector_dialog import NestingSelectorDialog
            active_idx = self._state.active_material_index
            active_ctx = contexts[active_idx] if active_idx < len(contexts) else None
            active_bars = active_ctx.nesting_layout or [] if active_ctx else []
            dlg = NestingSelectorDialog(
                self._state, active_idx, active_bars, [], 0.0, parent=self,
            )
            if dlg.exec() != NestingSelectorDialog.DialogCode.Accepted:
                return
            selected = dlg.selected_context_indices()
            if not selected:
                return
            material_contexts = [contexts[i] for i in selected]

        initial_dir = self._state.export_path or "."
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_pdf"),
            f"Nestify_Anidado_{_next_number(initial_dir, 'pdf')}.pdf",
            "PDF (*.pdf)",
        )
        if not path:
            return

        try:
            exportar_pdf(self._state, material_contexts=material_contexts, filename=path)
        except Exception as exc:
            QMessageBox.critical(self, t("export_error"), str(exc))

    # ── About / Links ────────────────────────────────────────────────────────

    def _github_url(self) -> str:
        url = (self._prefs.github_url or "").strip()
        if not url or "example.com" in url:
            return "https://github.com/Grohle/nestify"
        return url

    def _show_about(self) -> None:
        from nestify.ui_qt.dialogs.about_dialog import show_about_dialog
        show_about_dialog(
            self, github_url=self._github_url(),
            paypal_url=self._prefs.paypal_url,
            buymeacoffee_url=self._prefs.buymeacoffee_url,
        )

    def _show_about_startup(self) -> None:
        from nestify.ui_qt.dialogs.about_dialog import AboutDialog

        def on_no_show() -> None:
            self._prefs.show_about_on_startup = False
            app_config.save(self._prefs)

        AboutDialog(
            self, github_url=self._github_url(),
            paypal_url=self._prefs.paypal_url,
            buymeacoffee_url=self._prefs.buymeacoffee_url,
            on_no_show=on_no_show,
        ).exec()

    def _open_donate(self) -> None:
        webbrowser.open(self._prefs.donation_url)

    def _open_github(self) -> None:
        webbrowser.open(self._github_url())

    def _apply_window_icon(self) -> None:
        png = icon_png_path()
        if os.path.isfile(png):
            self.setWindowIcon(QIcon(png))

    # ── Window geometry ──────────────────────────────────────────────────────

    # ── Unsaved-changes guard (isDirty) ──────────────────────────────────────
    # Keys excluded from the dirty comparison: derived (barras_necesarias),
    # navigation (active_tab), and app-level prefs that are saved separately and
    # shouldn't flag the *job* as modified (language/calc_system/currency).
    _DIRTY_VOLATILE_KEYS = frozenset({
        "active_tab", "barras_necesarias", "export_path",
        "language", "calc_system", "currency",
    })

    def _job_snapshot(self) -> str:
        """JSON of the current job content for unsaved-changes detection.

        Flushes the active tab so in-progress edits are captured, then drops the
        volatile/derived keys so they don't cause false positives."""
        import json as _json
        import logging
        try:
            self._flush_main_tab(self._tabs.currentIndex())
            self._state.reset_from(self._tab_cortes.get_current_state())
            self._tab_nesting.sync_to_state()
            save_state_to_context(self._state, self._state.active_material_index)
        except Exception:
            # Don't silently swallow: a flush/sync failure here could otherwise
            # make _is_dirty() return a stale-but-equal snapshot and skip the
            # unsaved-changes warning. Log it and fail SAFE by returning a unique
            # snapshot so the job is treated as dirty (warn rather than lose edits).
            logging.getLogger(__name__).exception("job snapshot flush failed")
            import time as _time
            return f"__dirty__{_time.monotonic()}"
        d = {k: v for k, v in self._state.to_dict().items()
             if k not in self._DIRTY_VOLATILE_KEYS}
        return _json.dumps(d, sort_keys=True, ensure_ascii=False, default=str)

    def _mark_clean(self) -> None:
        """Record the current job as the saved baseline (call after save/open/new)."""
        self._clean_snapshot = self._job_snapshot()

    def _is_dirty(self) -> bool:
        return self._job_snapshot() != getattr(self, "_clean_snapshot", None)

    def closeEvent(self, event) -> None:
        # Warn about unsaved job changes before closing (Save / Discard / Cancel).
        if self._is_dirty():
            box = QMessageBox(self)
            box.setWindowTitle(t("unsaved_title"))
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(t("unsaved_msg"))
            save_b = box.addButton(t("save"), QMessageBox.ButtonRole.AcceptRole)
            box.addButton(t("discard"), QMessageBox.ButtonRole.DestructiveRole)
            cancel_b = box.addButton(t("cancel"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(save_b)
            box.exec()
            clicked = box.clickedButton()
            if clicked is cancel_b:
                event.ignore()
                return
            if clicked is save_b:
                self._guardar()

        self._sync_prefs_from_state()
        try:
            self._prefs.window_geometry = self.saveGeometry().toHex().data().decode()
        except Exception:
            pass
        app_config.save(self._prefs)
        super().closeEvent(event)

    def _restore_geometry(self) -> None:
        geo = self._prefs.window_geometry
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromHex(geo.encode()))
                return
            except Exception:
                pass
        self.resize(_WIN_W, _WIN_H)
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.geometry().center()
            self.move(center.x() - _WIN_W // 2, center.y() - _WIN_H // 2)
