"""
scripts/shot_profile_manager.py — §21.4 visual check (run once per theme).

    QT_QPA_PLATFORM=offscreen python scripts/shot_profile_manager.py OUTDIR THEME
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from nestify import app_config, profile_catalog  # noqa: E402
from nestify.ui_qt.fonts_qt import register_bundled_fonts  # noqa: E402
from nestify.ui_qt.theme_qt import apply_theme, build_palette, build_stylesheet  # noqa: E402


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nestify_shots"
    mode = sys.argv[2] if len(sys.argv) > 2 else "dark"
    os.makedirs(outdir, exist_ok=True)

    app = QApplication(sys.argv[:1])
    register_bundled_fonts()
    profile_catalog.ensure_catalog_profiles()
    apply_theme(mode)
    app.setPalette(build_palette(mode))
    app.setStyleSheet(build_stylesheet(mode))

    from PySide6.QtWidgets import QWidget
    from nestify.ui_qt.dialogs.profile_manager import ProfileManager

    parent = QWidget()
    cat = next((p for p in app_config.get().custom_profiles
                if p.id.startswith("catalog-")), None)
    dlg = ProfileManager(parent, initial_select_id=cat.id if cat else None)
    dlg.resize(860, 600)
    dlg.show()
    app.processEvents()
    app.processEvents()
    path = os.path.join(outdir, f"profile_manager_{mode}.png")
    dlg.grab().save(path)
    print("saved", path, "| selected:", cat.name if cat else "none")


if __name__ == "__main__":
    main()
