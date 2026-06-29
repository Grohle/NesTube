# Changelog

## 2.0.0-alpha.1

- **PySide6 (Qt) is the default UI** — `python3 main.py` launches the Qt application.
- CustomTkinter 1.x line frozen at **`v1.0.0-alpha.1`** (branch `legacy/v1.0-ctk`, entry `main_ctk.py`).
- Packaging: `packaging/nestify.spec` builds Qt; `packaging/nestify_ctk_legacy.spec` for legacy 1.x builds.

## 1.0.0-alpha.1

- First public alpha (CustomTkinter UI).
- Windows portable build via PyInstaller (`Nestify.exe` in `Nestify-*-windows.zip`).
- Interactive nesting with contour-based placement and mitre/bevel geometry.
- Offline PDF, Excel, and DOCX export; materials and stock databases.
