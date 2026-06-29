"""
scripts/qt_screenshot.py

Dev-only screenshot harness for the Nestify Qt UI. Renders tabs/dialogs offscreen
in both themes so UI changes can be verified visually.

Usage:
    QT_QPA_PLATFORM=offscreen python scripts/qt_screenshot.py OUTDIR [--seed]

Produces PNGs for each main tab in dark and light themes. With --seed it also
populates a sample profile + cuts and runs a synchronous simple-nest so the
Nesting bars and Cuts preview show real content.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

from nestify import app_config  # noqa: E402
from nestify.ui_qt.fonts_qt import register_bundled_fonts  # noqa: E402
from nestify.ui_qt.theme_qt import apply_theme, build_palette, build_stylesheet  # noqa: E402
from nestify.models import Corte, ConfigPerfil, PerfilDimensiones, TipoPerfil  # noqa: E402
from nestify.context_sync import ensure_material_contexts  # noqa: E402


def _sample_perfil() -> ConfigPerfil:
    p = ConfigPerfil()
    p.dimensiones = PerfilDimensiones(
        tipo=TipoPerfil.RECTANGULAR, lado_a=60.0, lado_b=40.0, espesor=3.0
    )
    p.material.precio_kg = 1.8
    p.material.kg_por_m = 4.5
    return p


def _sample_cortes():
    return [
        Corte(descripcion="Larguero", largo=1200.0, cantidad=3),
        Corte(descripcion="Travesaño", largo=800.0, cantidad=4),
        Corte(descripcion="Diagonal", largo=650.0, cantidad=2,
              inglete1=True, inglete1_deg=45.0),
        Corte(descripcion="Montante", largo=2000.0, cantidad=2),
    ]


def _seed(window) -> None:
    state = window._state
    ensure_material_contexts(state)
    ctx = state.material_contexts[state.active_material_index]
    ctx.material = "Acero"
    ctx.quality = "S235"
    ctx.perfil = _sample_perfil()
    ctx.cortes = _sample_cortes()
    ctx.longitud_barra = 6000.0
    ctx.perdida_corte = 2.0
    state.perfil = ctx.perfil
    state.cortes = list(ctx.cortes)
    state.longitud_barra = ctx.longitud_barra


def _set_theme(app, window, mode: str) -> None:
    """Apply a theme through the real propagation path (without persisting prefs)."""
    apply_theme(mode)
    app.setPalette(build_palette(mode))
    app.setStyleSheet(build_stylesheet(mode))
    for attr in ("_tab_nesting", "_tab_jobs", "_tab_stock", "_tab_cortes", "_tab_perfiles"):
        tab = getattr(window, attr, None)
        if tab and hasattr(tab, "refresh_theme"):
            tab.refresh_theme()


def _run_nest(app, window) -> None:
    """Trigger auto-nest and pump the event loop until the worker finishes."""
    import time
    nt = window._tab_nesting
    nt._run_auto_nest()
    deadline = time.time() + 6.0
    while getattr(nt, "_auto_nesting", False) and time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)
    for _ in range(5):
        app.processEvents()


TABS = {0: "jobs", 1: "cuts", 2: "nesting", 3: "profiles", 4: "stock"}


def main() -> None:
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nestify_shots"
    do_seed = "--seed" in sys.argv
    os.makedirs(outdir, exist_ok=True)

    do_nest = "--nest" in sys.argv
    app = QApplication(sys.argv[:1])
    register_bundled_fonts()

    from nestify.ui_qt.app import NestifyApp

    for mode in ("dark", "light"):
        window = NestifyApp()
        window.resize(1280, 800)
        if do_seed:
            _seed(window)
        window.show()
        _set_theme(app, window, mode)
        app.processEvents()
        for idx, name in TABS.items():
            window._tabs.setCurrentIndex(idx)
            window._refresh_main_tab(idx)
            app.processEvents()
            app.processEvents()
            if do_nest and name == "nesting":
                _run_nest(app, window)
            path = os.path.join(outdir, f"{name}_{mode}.png")
            window.grab().save(path)
            print("saved", path)
        window.close()


if __name__ == "__main__":
    main()
