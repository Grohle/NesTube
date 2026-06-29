"""
scripts/shot_costs_catalog.py — §21.2 visual check.

Seeds the catalogue, selects a catalogue profile in the Costs tab and captures
the tab in both themes so the read-only summary + "Edit material" button (and a
computed cost) can be verified.

    QT_QPA_PLATFORM=offscreen python scripts/shot_costs_catalog.py OUTDIR
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from nestify import app_config, profile_catalog  # noqa: E402
from nestify.ui_qt.fonts_qt import register_bundled_fonts  # noqa: E402
from nestify.ui_qt.theme_qt import apply_theme, build_palette, build_stylesheet  # noqa: E402
from nestify.models import Corte  # noqa: E402
from nestify.context_sync import ensure_material_contexts  # noqa: E402


def _set_theme(app, window, mode):
    apply_theme(mode)
    app.setPalette(build_palette(mode))
    app.setStyleSheet(build_stylesheet(mode))
    for attr in ("_tab_nesting", "_tab_jobs", "_tab_stock", "_tab_cortes",
                 "_tab_perfiles", "_tab_materiales"):
        tab = getattr(window, attr, None)
        if tab and hasattr(tab, "refresh_theme"):
            tab.refresh_theme()


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nestify_shots"
    # Optional single-theme mode (run once per theme in separate processes to
    # avoid second-window construction quirks in the headless event loop).
    only = sys.argv[2] if len(sys.argv) > 2 else None
    modes = (only,) if only in ("dark", "light") else ("dark", "light")
    os.makedirs(outdir, exist_ok=True)

    app = QApplication(sys.argv[:1])
    register_bundled_fonts()
    profile_catalog.ensure_catalog_profiles()

    # The startup About dialog (QTimer.singleShot → exec) would block
    # processEvents; disable it for the headless capture.
    app_config.get().show_about_on_startup = False

    from nestify.ui_qt.app import NestifyApp

    cat = next((p for p in app_config.get().custom_profiles
                if p.id.startswith("catalog-")), None)

    # A fresh window per theme avoids accumulated-state quirks in the headless
    # event loop; the startup About dialog is already disabled above.
    for mode in modes:
        window = NestifyApp()
        window.resize(1280, 820)
        # Use the real theme-switch path so palette/QSS and every tab repaint.
        window._set_theme(mode)
        state = window._state
        ensure_material_contexts(state)
        ctx = state.material_contexts[state.active_material_index]
        ctx.cortes = [
            Corte(descripcion="Larguero", largo=1200.0, cantidad=3),
            Corte(descripcion="Travesaño", largo=800.0, cantidad=4),
        ]
        ctx.longitud_barra = 6000.0
        state.cortes = list(ctx.cortes)
        state.longitud_barra = ctx.longitud_barra
        window.show()

        tab = window._tab_perfiles
        for i in range(window._tabs.count()):
            if window._tabs.widget(i) is tab:
                window._tabs.setCurrentIndex(i)
                window._refresh_main_tab(i)
                break
        app.processEvents()

        if cat is not None:
            tab._select_profile(f"custom:{cat.name}")
            tab.ui.e_precio_kg.setText("2.0")
            app.processEvents()
            tab._calcular()
            app.processEvents()
        for _ in range(3):
            app.processEvents()
        path = os.path.join(outdir, f"costs_catalog_{mode}.png")
        window.grab().save(path)
        print("saved", path, "| selected:", cat.name if cat else "none")
        window.close()
        app.processEvents()


if __name__ == "__main__":
    main()
