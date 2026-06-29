# Nestify — UI Map (where to touch each control)

> Developer index: for every interactive control, where it is **wired** in the
> code (`file:line`) and the **handler** method that runs. Line numbers track
> `main` and may drift by a few lines after edits — search the handler name if
> a line has moved. For *visual* sizing/positioning, each control also has an
> inline comment next to its creation explaining what determines its height,
> width, position and font.
>
> Conventions:
> - Tabs live in `nestify/ui_qt/tab_*.py`; their layout/geometry comes from the
>   matching `.ui` form in `nestify/ui_qt/forms/*.ui` (edit the `.ui`, then run
>   `python -m nestify.ui_qt.compile_forms`). Controls built in code are noted.
> - `ui.<name>` = a widget from the `.ui` form (object name = `<name>`).
> - Colours/theme: `nestify/ui_qt/theme_qt.py`. Icons: `nestify/ui_qt/icons.py`.

---

## Window shell & menus — `nestify/ui_qt/app.py`

Tabs are created in `_build_tabs` (`app.py:189-202`), in this order: Jobs
Explorer, Cuts, Nesting, Costs & Weight, Stock. The menu bar is built in
`_build_menu` (`app.py:93`).

| Menu item | Handler | Wired at |
|-----------|---------|----------|
| File → Open / Save / Save as | `_abrir` / `_guardar` / `_guardar_como` | `app.py:94-96` |
| File → Export Excel / PDF | `_exportar_excel` / `_exportar_pdf` | `app.py:101-102` |
| File → Import Excel / Save template | `_importar_excel` / `_save_import_template` | `app.py:104-105` |
| View → Theme | `_set_theme` | `app.py:111-113` |
| View → Font size / UI font | `_set_font_size` / `_set_ui_font_family` | `app.py:115-126` |
| View → Language | `_set_language` | `app.py:120-123` |
| View → Units (metric/imperial) | `_set_unit_system` | `app.py:128-130` |
| View → Cut colours | `_toggle_cut_colors` | `app.py:133` |
| Settings → Cost mode | `_set_cost_mode` | `app.py:144-146` |
| Settings → Materials | `_manage_materials` | `app.py:148` |
| Settings → Profile types (add / edit) | `_open_profile_creator` / `_open_profile_manager` | `app.py:154-155` |
| Settings → Currency | (lambda → state) | `app.py:157-159` |
| Settings → PDF config (font/template/edit/FastReport) | `_configure_pdf_*` | `app.py:162-166` |
| Settings → Optimization times | `_configure_opt_times` | `app.py:168` |
| Settings → Nesting layout | `_configure_nesting_layout` | `app.py:169` |
| Settings → Name assignment / Reset | `_configure_naming` / `_reset_settings` | `app.py:171-173` |
| About / Help → Donate / Issues | `_show_about` / `_open_donate` / `_open_github` | `app.py:177-181` |

---

## Cuts — `nestify/ui_qt/tab_cortes.py`

Signals wired in `_connect_signals` (~`tab_cortes.py:439`). Toolbar/header
geometry comes from `forms/tab_cortes.ui`.

| Control | What it does | Handler | Wired at |
|---------|--------------|---------|----------|
| **Calculate** (`calc_btn`) | Runs the bin-packing engine, fills the preview | `_calcular` | `tab_cortes.py:442` |
| **Calculation system** (`calc_combo_cuts`) | FFD / BFD / NFD | `_on_calc_system_change` | `tab_cortes.py:457` |
| **+ Add Cut** (`add_btn`) | Appends a cut row | `_add_row` | `tab_cortes.py:441` |
| Add field / Edit fields (`add_field_btn`/`edit_fields_btn`) | Custom dimension fields | `_add_custom_field` / `_open_fields_editor` | `tab_cortes.py:439-440` |
| Material search (magnifier) | Opens material picker | in `MaterialAutocomplete` | `widgets/material_autocomplete.py:130` |
| A cut row (description, length, qty, bevel) | One piece | `CorteRow` | `widgets/corte_row.py` (row built in `_add_row`, `tab_cortes.py:486`) |
| Bevel toggle on a row | Enables a mitre end (needs Bar height) | `_validate_bevel_height` | `tab_cortes.py` (`bevel_requested`) |

Header fields `material/quality`, `_e_pedido/_e_oferta/_e_cliente`, and the
parameter fields `_e_kerf/_e_margin/_e_bar_len/_e_bar_height` are assembled in
`_build_header` / `_build_controls`. The inline preview widget is
`NestingPreviewWidget` (`tab_cortes.py:70`).

---

## Nesting — `nestify/ui_qt/tab_nesting.py`

Toolbar built in `_setup_toolbar` (~`tab_nesting.py:349`); per-piece/per-bar
rows in `_make_piece_row` / `_make_bar_section`. Canvas =
`nestify/ui_qt/nesting_scene.py` + `nesting_view.py`.

| Control | What it does | Handler | Wired at |
|---------|--------------|---------|----------|
| **Save** (`save_btn`, 💾→SVG) | Save nesting to the job | `_save_nesting` | `tab_nesting.py:374` |
| **Clear** (`clear_btn`, 🗑→SVG) | Clear placements | `_clear_nesting` | `tab_nesting.py:378` |
| **Advanced** toggle (`_mode_switch`) | Simple ↔ Advanced engine | `_on_mode_change` | `tab_nesting.py:385` |
| **Use stock** toggle (`_stock_switch`) | Plan against stock | `_on_use_stock_toggled` (app) | `tab_nesting.py:391` |
| **+ Add bar** (`add_bar_btn`) | Adds an empty bar | `_add_bar` | `tab_nesting.py:398` |
| **Remnants** (`rem_toolbar_btn`) | Toggle remnant panel | `_toggle_remnant_panel` | `tab_nesting.py:402` |
| Rotate left/right (`rotate_left_btn`/`rotate_right_btn`) | Cycle orientation | `_cycle_orientation` | `tab_nesting.py:406/418` |
| Flip V / H (`flip_v_btn`/`flip_h_btn`) | Mirror piece | `_flip_vertical` / `_flip_horizontal` | `tab_nesting.py:410/414` |
| **Auto-nest** (`auto_nest_btn`) | Run/stop auto-nesting | `_toggle_auto_nest` → `_run_auto_nest`/`_run_simple_nest` | `tab_nesting.py:426` |
| Zoom % (`_zoom_btn`) | Reset to 100% / fit | `_view.fit_scene` | `tab_nesting.py:446` |
| Common cut / Snap toggles (`_cb_common`/`_cb_snap`) | Engine options | (read in `_placement_params`) | `tab_nesting.py:491/497` |
| Strategy combo (`strategy_combo`) | Advanced strategy | `_update_status` | `tab_nesting.py:523` |
| Calc-system combo (`_calc_combo`) | Simple FFD/BFD/NFD | `_on_calc_system_change` | `tab_nesting.py:537` |
| **Borrar / Eliminar X** (`delete_btn`/`remove_btn`) | Remove from bar / delete permanently | `_delete_selected_placed` / `_remove_piece_permanently` | `tab_nesting.py:545/547` |
| Sidebar filters (`filter_all/complete/incomplete_btn`) | Filter pieces list | `_set_sidebar_filter` | `tab_nesting.py:552-560` |
| **Show all** (`show_all_btn`) | Clear bar filter | `_show_all_bars` | `tab_nesting.py:565` |
| Remnant refresh/apply (`rem_refresh_btn`/`rem_apply_btn`) | Generate / send to stock | `_refresh_remnants` / `_apply_remnants_to_stock` | `tab_nesting.py:579/582` |
| Right-click on a placed piece | Context menu (delete/flip/change values) | `menu.addAction(...)` | `tab_nesting.py:1712-1721` |

---

## Costs & Weight — `nestify/ui_qt/tab_perfiles.py`

Signals wired in `_connect_signals` (~`tab_perfiles.py:219`).

| Control | What it does | Handler | Wired at |
|---------|--------------|---------|----------|
| **Calculate** (`calc_btn`) | Compute per-cut + total costs | `_calcular` | `tab_perfiles.py:219` |
| **Clear** (`clear_btn`) | Reset fields | `_limpiar` | `tab_perfiles.py:220` |
| **Export Excel / PDF / DOCX** (`btn_excel/pdf/docx`) | Export quote | `_export_excel` / `_export_pdf` / `_export_docx` | `tab_perfiles.py:221-223` |
| **Print** (`btn_print`, 🖨→SVG) | Print quote | `_print` | `tab_perfiles.py:224` |
| Profile combo (`profile_combo`) | Pick profile type | `_on_profile_combo_change` | `tab_perfiles.py:225` |
| Profile gallery tiles | Select / open creator | `_select_profile` / `_on_add_profile` | `tab_perfiles.py:350/372` (built in `_rebuild_favorites`) |
| Solid section (`cb_macizo`) | Toggle hollow/solid | `_toggle_espesor` | `tab_perfiles.py:226` |
| Currency combo (`currency_combo`) | Change currency | `_on_currency_change` | `tab_perfiles.py:227` |
| Result cards ("Results per cut") | Per-line breakdown | `_ResultCard` | `tab_perfiles.py:74` |

---

## Stock — `nestify/ui_qt/tab_stock.py`

Signals wired in `_connect_signals` (~`tab_stock.py:148`); rows built in
`_refresh_list` (~`tab_stock.py:175`).

| Control | What it does | Handler | Wired at |
|---------|--------------|---------|----------|
| **+ Add to stock** (`add_btn`) | New stock bar dialog | `_add_bar_dialog` | `tab_stock.py:148` |
| **Edit fields** (`edit_btn`) | Edit selected bar | `_edit_selected` | `tab_stock.py:149` |
| **Remove** (`del_btn`) | Delete selected | `_delete_selected` | `tab_stock.py:150` |
| Profile filter (`profile_combo`) | Filter by profile | `_on_profile_filter` | `tab_stock.py:155` |
| Search field (magnifier action) | Text filter (debounced 200ms) | `_refresh_list` | `tab_stock.py:66` / timer `:48` |
| Select-all (`select_all_cb`) | Toggle all checkboxes | `_toggle_select_all` | `tab_stock.py:156` |
| Per-row availability button | Toggle in/out of stock | `_toggle_availability` | `tab_stock.py:241` |
| Right-click on a row | Edit / Remove menu | `menu.addAction(...)` | `tab_stock.py:381-382` |

---

## Jobs Explorer — `nestify/ui_qt/tab_jobs.py`

Signals wired in `_connect_signals` (~`tab_jobs.py:223`); tiles built in
`_render_job_list` (~`tab_jobs.py:255`).

| Control | What it does | Handler | Wired at |
|---------|--------------|---------|----------|
| **New** (`new_btn`) | Start a blank job | `_new_job` | `tab_jobs.py:223` |
| Search field/entry + **Search** (`search_btn`) | Filter jobs | `_run_search` | `tab_jobs.py:224-227` |
| **Clear** (`clear_btn`) | Reset search | `_clear_search` | `tab_jobs.py:228` |
| **Open** (`open_btn`) | Open selected job | `_open_selected` | `tab_jobs.py:229` |
| **Delete** (`del_btn`) | Delete selected job | `_delete_selected` | `tab_jobs.py:230` |
| A job tile (click / double-click) | Select / open | `_select` / `_open_job` | `tab_jobs.py:272-273` (`_JobTile`, `tab_jobs.py:29`) |

---

## Dialogs — `nestify/ui_qt/dialogs/`

| Dialog | File | Opened from |
|--------|------|-------------|
| Add bar | `add_bar_dialog.py` | Stock → Add to stock |
| Stock add/edit (form) | `stock_add_dialog.py` | Stock → Add / Edit |
| Material picker / manager | `material_picker_dialog.py` / `materials_manager.py` | Cuts magnifier / Settings → Materials |
| Profile creator (CAD) | `profile_creator.py` | Settings → Add profile / Costs "+" tile |
| Profile manager | `profile_manager.py` | Settings → Edit profiles |
| Change piece values | `change_values_dialog.py` | Nesting → right-click → Change values |
| Generate remnants | `retal_dialog.py` | Nesting remnant panel |
| Nesting layout settings | `nesting_layout_dialog.py` | Settings → Nesting layout |
| Optimization times | `optimization_times_dialog.py` | Settings → Optimization times |
| Profile height | `profile_height_dialog.py` | Use-stock flow (multiple heights) |
| PDF template editor | `pdf_template_editor.py` | Settings → PDF → Edit template |
| About | `about_dialog.py` | About menu |

Most dialogs take their geometry from a `.ui` form (`forms/ui_*`); those whose
layout is built in code (`stock_add_dialog`, `materials_manager`,
`profile_creator`, `add_bar_dialog`, `retal_dialog`, `pdf_template_editor`)
have inline comments on each sizing decision.

---

## Reusable widgets — `nestify/ui_qt/widgets/`

| Widget | File | Used by |
|--------|------|---------|
| Cut row (desc/length/qty/bevel) | `corte_row.py` | Cuts list |
| Material autocomplete + picker | `material_autocomplete.py` | Cuts header |
| Material sub-tabs ("Nesting N") | `material_subtabs.py` | Cuts / Costs |
| Pill switch (animated toggle) | `pill_switch.py` | various |
| Profile tile (gallery thumbnail) | `profile_tile.py` | Costs gallery |
