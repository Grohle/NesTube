"""
scripts/_vibe_capture.py

Offscreen fallback used by ./auto_capture.sh when there is no real desktop to
screen-grab (e.g. headless CI / cloud containers). Renders the *actual* Nestify
Qt main window via QT_QPA_PLATFORM=offscreen and saves a PNG.

This is NOT a fake/black image: it grabs the real composited widget tree, so the
resulting PNG is a faithful picture of the application UI (the thing that
actually matters for visual verification in this project).

Usage:
    QT_QPA_PLATFORM=offscreen python scripts/_vibe_capture.py OUTPUT.png [theme] [tab_idx]

Exit codes:
    0  PNG written successfully
    3  PySide6 / app could not be imported or rendered (caller decides what to do)
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

out = sys.argv[1] if len(sys.argv) > 1 else "artifacts/vibe_check.png"
mode = sys.argv[2] if len(sys.argv) > 2 else "dark"
tab_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 1  # 1 = Cuts

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - environment dependent
    sys.stderr.write(f"[_vibe_capture] PySide6 unavailable: {exc}\n")
    sys.exit(3)

try:
    app = QApplication.instance() or QApplication(sys.argv[:1])

    # Bundled fonts are optional; ignore if the helper is missing.
    try:
        from nestify.ui_qt.fonts_qt import register_bundled_fonts
        register_bundled_fonts()
    except Exception:
        pass

    from nestify.ui_qt.app import NestifyApp

    window = NestifyApp()
    window.resize(1400, 850)
    # Apply theme through whichever API the window exposes.
    if hasattr(window, "_set_theme"):
        window._set_theme(mode)
    window.show()
    app.processEvents()

    if hasattr(window, "_tabs"):
        window._tabs.setCurrentIndex(tab_idx)
        if hasattr(window, "_refresh_main_tab"):
            window._refresh_main_tab(tab_idx)
    app.processEvents()
    app.processEvents()

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    ok = window.grab().save(out)
    if not ok:
        sys.stderr.write("[_vibe_capture] QPixmap.save() returned False\n")
        sys.exit(3)
    print(f"[_vibe_capture] wrote {out} (theme={mode}, tab={tab_idx})")
except Exception as exc:
    sys.stderr.write(f"[_vibe_capture] render failed: {exc}\n")
    sys.exit(3)
