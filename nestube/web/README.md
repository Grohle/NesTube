# NesTube web UI (stage 1: mockup)

A new HTML/CSS/JS interface for NesTube with a Figma-style layout, meant to be
wrapped in a native window with [pywebview](https://pywebview.flowrl.com/) and
packaged for Windows with the existing PyInstaller / Inno Setup scripts in
`packaging/`.

Open `index.html` in any Chromium-based browser to try it. It has no build step
and no network dependencies; fonts come from `nestube/fonts/`.

| File | Purpose |
|---|---|
| `index.html` | Shell (top bar, status bar) and the six views |
| `css/app.css` | Design tokens (mirror `ui_qt/theme_qt.py`, light and dark) and components |
| `js/ui.js` | Menus, dialogs, alerts, toasts, theme |
| `js/nesting.js` | Nesting canvas: zoom, pan, selection, floating piece, snap, undo/redo |
| `js/views.js` | Jobs, Cuts, Costs, Profiles and Stock views |
| `js/dialogs.js` | Every Qt dialog as a layout |
| `js/alerts.js` | Every `QMessageBox` in `ui_qt/` (generated, Spanish text) |
| `js/cad.js` | Drawing module (profile creator) with an AutoCAD-style layout: ribbon, command line, object snaps, dynamic input |
| `js/viewer.js` | Full-window profile image viewer |
| `js/profile-images.js` | `Profiles/*.png` embedded as data URIs (generated) |
| `js/tutorial.js` | Interactive tutorial (same steps as `ui_qt/tutorial.py`) |
| `js/app.js` | Main menu, keyboard shortcuts, action routing, Nesting panels |

The full inventory of menus, buttons, shortcuts, dialogs and alerts, and where
each one lives in this UI, is in [`docs/ui-inventario.md`](../../docs/ui-inventario.md).

## Stage 2 (functionality)

Everything the mockup does with example data goes through a few seams that
will call Python instead:

- `NestCanvas` placement checks (`fits`, `snapCandidates`) are a 1D placeholder.
  They will call `TabNesting._find_best_snap` / `_fits_physically` logic and
  `nesting_engine` (NFP, contour collision) through a pywebview `js_api`, so the
  existing collision logic is reused unchanged.
- Auto-nest will run `_AutoNestWorker` / `nesting_engine` and stream live results.
- `NT.action` / `NT.dialog` handlers will read and write the SQLite database via
  `database.py`, `stock_db.py`, `profile_catalog.py` and `app_config.py`.
- Strings will come from `i18n.py` so English/Spanish switching keeps working.
