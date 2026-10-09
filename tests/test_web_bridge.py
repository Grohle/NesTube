"""
tests/test_web_bridge.py — the HTML interface drives the REAL engine.

The web UI (nestube/web) talks to a headless NesTubeApp through the QWebChannel
bridge (nestube/ui_web). These tests call the bridge exactly like the page does
— JSON in, JSON out — and check the things that must never break:

  * cuts typed in the web Cuts view reach Nesting;
  * auto-nest places every piece;
  * picking pieces up, rotating them while carried and dropping them again
    (same bar, another bar, back into their own slot) never overlaps two
    pieces and never loses one;
  * engine message boxes come back as alerts instead of blocking modals.

Plus regressions for the fixes that came with the web UI: the cutting height
shown in Nesting is the one its geometry uses, Ctrl+click on a piece selects
instead of panning, and a bar-start piece re-drops into its own slot.
"""
import json
import os
import random
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")
shapely = pytest.importorskip("shapely")

from shapely import affinity  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

CUTS = [
    {"descripcion": "Viga", "largo": 3500, "cantidad": 4},
    {"descripcion": "Correa", "largo": 1200, "cantidad": 6},
    {"descripcion": "Montante", "largo": 800, "cantidad": 8},
    {"descripcion": "Diagonal", "largo": 2800, "cantidad": 2, "inglete1": True, "inglete2": True,
     "inglete1_dir": "up", "inglete2_dir": "down"},
    {"descripcion": "Tirante", "largo": 1500, "cantidad": 3, "inglete1": True, "inglete2": True},
    {"descripcion": "Placa", "largo": 400, "cantidad": 4},
]
TOTAL = sum(c["cantidad"] for c in CUTS)


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(scope="module")
def web(qapp):
    from nestube.ui_qt.app import NesTubeApp
    from nestube.ui_web.bridge import Bridge
    engine = NesTubeApp(headless=True)
    bridge = Bridge(engine)
    yield qapp, engine, bridge
    engine._tab_nesting._discard_dirty = True
    engine.deleteLater()


def call(bridge, method, **args):
    res = json.loads(bridge.call(method, json.dumps(args)))
    assert res["ok"], res.get("error")
    return res


def overlaps(tab):
    bad = []
    for bi, bar in enumerate(tab._bars):
        polys = [(pp, affinity.translate(Polygon(pp.poly_local), pp.x_offset, 0)) for pp in bar]
        length = tab._bar_len_for(bi)
        for pp, p in polys:
            lo, _, hi, _ = p.bounds
            if lo < -0.5 or hi > length + 0.5:
                bad.append(("out", bi, pp.corte.descripcion))
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                if polys[i][1].intersection(polys[j][1]).area > 1.0:
                    bad.append(("overlap", bi, polys[i][0].corte.descripcion,
                                polys[j][0].corte.descripcion))
    return bad


def nest(qapp, bridge, *, advanced, margin=0.0, common=False):
    call(bridge, "data.cuts_set", rows=CUTS,
         params={"bar_len": 6000, "kerf": 3, "margin": margin, "height": 80})
    call(bridge, "data.set_view", name="nesting")
    # opt=0 → the 1 s optimisation level (the default may be "unlimited",
    # which runs until stopped).
    call(bridge, "nest.set_params", height=80, advanced=advanced, snap=True, common=common, opt=0)
    call(bridge, "nest.auto_nest", continue_without_material=True)
    tab = bridge.engine._tab_nesting
    t0 = time.time()
    while tab._auto_nesting and time.time() - t0 < 30:
        qapp.processEvents()
        time.sleep(0.02)
    assert not tab._auto_nesting, "auto-nest did not finish"
    qapp.processEvents()
    return call(bridge, "nest.state")["result"]


def centre(state, bar, piece):
    xs = [q[0] + piece["x"] for q in piece["poly"]]
    return (min(xs) + max(xs)) / 2.0, bar["y"] + state["sh"] / 2.0


def drag(bridge, x0, y0, x1, y1, rotations=()):
    zoom = 1.0   # 1 px per mm: the 5 px drag threshold is 5 mm
    call(bridge, "nest.press", x=x0, y=y0, zoom=zoom)
    for k in (1, 2, 3):
        call(bridge, "nest.move", x=x0 + (x1 - x0) * k / 3, y=y0 + (y1 - y0) * k / 3, zoom=zoom)
    for name in rotations:
        call(bridge, "nest.action", name=name)
    call(bridge, "nest.move", x=x1, y=y1, zoom=zoom)
    state = call(bridge, "nest.release", x=x1, y=y1, zoom=zoom)["result"]
    if state["floating"]:
        state = call(bridge, "nest.action", name="cancel_float")["result"]
    return state


def test_unknown_method_is_an_error_not_a_crash(web):
    _, _, bridge = web
    res = json.loads(bridge.call("nest.does_not_exist", "{}"))
    assert res["ok"] is False and "unknown bridge method" in res["error"]
    res = json.loads(bridge.call("nest._private", "{}"))
    assert res["ok"] is False


def test_message_boxes_become_alerts(web, monkeypatch):
    _, engine, bridge = web
    from PySide6.QtWidgets import QMessageBox

    def warn():
        QMessageBox.warning(engine, "Aviso", "Mensaje de prueba")

    monkeypatch.setattr(engine._tab_nesting, "_add_bar", warn)
    res = call(bridge, "nest.action", name="add_bar")
    assert {"kind": "warning", "title": "Aviso", "msg": "Mensaje de prueba"} in res["alerts"]


def test_cuts_from_web_reach_nesting(web):
    qapp, _, bridge = web
    call(bridge, "data.set_view", name="nesting")
    call(bridge, "data.cuts_set", rows=CUTS[:2], params={"bar_len": 6000, "kerf": 3, "height": 80})
    state = call(bridge, "nest.state")["result"]
    assert [p["name"] for p in state["pieces"]] == ["Viga", "Correa"]
    assert sum(p["total"] for p in state["pieces"]) == 10


@pytest.mark.parametrize("advanced,margin,common,seed", [
    (True, 0.0, False, 1),
    (False, 0.0, False, 2),
    (True, 50.0, False, 3),
    (True, 50.0, True, 4),
])
def test_pick_rotate_and_drop_never_overlaps_or_loses_pieces(web, advanced, margin, common, seed):
    qapp, engine, bridge = web
    state = nest(qapp, bridge, advanced=advanced, margin=margin, common=common)
    tab = engine._tab_nesting
    assert state["placed"] == state["total"] == TOTAL
    assert overlaps(tab) == []

    rnd = random.Random(seed)
    for step in range(30):
        bars = [b for b in state["bars"] if b["pieces"]]
        bar = rnd.choice(bars)
        piece = rnd.choice(bar["pieces"])
        x0, y0 = centre(state, bar, piece)
        op = rnd.choice(["same", "other", "rotate"])
        if op == "same":
            x1, y1 = x0 + rnd.uniform(-10, 10), y0
        else:
            target = rnd.choice(state["bars"])
            x1, y1 = rnd.uniform(0, target["len"]), target["y"] + state["sh"] / 2.0
        rotations = [rnd.choice(["rotate_left", "rotate_right"])
                     for _ in range(rnd.randint(1, 3))] if op == "rotate" else []
        state = drag(bridge, x0, y0, x1, y1, rotations)
        assert overlaps(tab) == [], (step, op, piece["name"])
        assert state["placed"] == TOTAL, (step, op, piece["name"])
        assert sum(len(b) for b in tab._bars) == sum(pi.placed_qty for pi in tab._pieces)


def test_dropping_a_piece_where_it_was_keeps_its_slot(web):
    qapp, engine, bridge = web
    state = nest(qapp, bridge, advanced=False)
    for bar in state["bars"][:2]:
        for piece in bar["pieces"]:
            x0, y0 = centre(state, bar, piece)
            # Drag it well away, then back to (almost) where it was.
            call(bridge, "nest.press", x=x0, y=y0, zoom=1.0)
            call(bridge, "nest.move", x=x0 + 40, y=y0, zoom=1.0)
            call(bridge, "nest.move", x=x0 + 1, y=y0, zoom=1.0)
            state = call(bridge, "nest.release", x=x0 + 1, y=y0, zoom=1.0)["result"]
            same = state["bars"][bar["i"]]["pieces"]
            assert any(q["name"] == piece["name"] and abs(q["x"] - piece["x"]) < 2.0 for q in same), \
                (bar["i"], piece["name"], piece["x"], [(q["name"], q["x"]) for q in same])
    assert overlaps(engine._tab_nesting) == []


def test_a_grabbed_piece_keeps_the_grab_point_under_the_cursor(qapp):
    """Grabbing a piece by its middle must not make it jump so its left end
    sits on the cursor — that sent "put it back where it was" to another slot."""
    from PySide6.QtCore import QPointF
    from nestube.models import AppState, Corte
    from nestube.ui_qt.tab_nesting import TabNesting

    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.cortes = [Corte("A", 3500, 1), Corte("B", 1500, 1), Corte("C", 800, 1)]
    tab = TabNesting(st)
    tab._cb_snap.setChecked(True)
    tab._mode_switch.setChecked(False)
    tab._update_mode_controls()
    tab._run_simple_nest()
    y = tab._scene.bar_y_for(0) + tab._section_height_mm() / 2.0
    for pp in sorted(tab._bars[0], key=lambda q: q.x_offset):
        x0 = pp.x_offset
        mid = x0 + pp.corte.largo / 2.0
        tab._pick_up_placed(pp, grab_x=mid)
        tab._update_float_preview(QPointF(mid + 1.0, y))
        tab._place_floating_piece(QPointF(mid + 1.0, y))
        assert not tab._floating
        back = [q for q in tab._bars[0] if q.corte is pp.corte]
        assert back and abs(back[0].x_offset - x0) < 2.0, (pp.corte.descripcion, x0, back[0].x_offset)


def test_ctrl_click_on_a_piece_selects_instead_of_panning(qapp):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from nestube.models import AppState, Corte
    from nestube.ui_qt.tab_nesting import TabNesting

    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.cortes = [Corte("A", 2000, 2)]
    tab = TabNesting(st)
    tab._mode_switch.setChecked(False)
    tab._update_mode_controls()
    tab._run_simple_nest()
    view = tab._view
    view.resize(1200, 400)
    view.show()
    view.fit_scene()
    qapp.processEvents()
    pp = tab._bars[0][0]
    from PySide6.QtCore import QPointF
    scene_pt = QPointF(pp.x_offset + pp.corte.largo / 2.0,
                       tab._scene.bar_y_for(0) + tab._section_height_mm() / 2.0)
    vp = view.mapFromScene(scene_pt)
    pressed = []
    view.scene_pressed.connect(lambda p: pressed.append(p))
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.ControlModifier, QPoint(vp.x(), vp.y()))
    assert not view._pan_active
    assert pressed, "Ctrl+click on a piece must reach the scene (multi-select)"
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.ControlModifier, QPoint(vp.x(), vp.y()))
    view.hide()


def test_nesting_geometry_uses_the_displayed_cutting_height(qapp):
    """The Nesting height field showed the user's cutting face (40) while the
    geometry still used the section height (80) after a context load — pieces
    were laid out for one height and drawn/checked at another."""
    from nestube import app_config
    from nestube.context_sync import ensure_material_contexts, load_context_to_state
    from nestube.models import AppState, Corte, TipoPerfil
    from nestube.ui_qt.tab_nesting import TabNesting

    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.cortes = [Corte("D", 1000, 6, inglete1=True, inglete2=True,
                       inglete1_dir="up", inglete2_dir="down")]
    ensure_material_contexts(st)
    ctx = st.material_contexts[0]
    ctx.profile_name = "Tubo 80x40 (test)"
    ctx.material = "S235"
    ctx.perfil.dimensiones.tipo = TipoPerfil.RECTANGULAR
    ctx.perfil.dimensiones.lado_a = 80
    ctx.perfil.dimensiones.lado_b = 40
    ctx.perfil.dimensiones.espesor = 2
    ctx.cortes = list(st.cortes)
    ctx.longitud_barra = 6000
    ctx.perdida_corte = 3
    choices = app_config.get().cutting_height_choices
    had = "Tubo 80x40 (test)" in choices
    old = choices.get("Tubo 80x40 (test)")
    choices["Tubo 80x40 (test)"] = 40.0
    try:
        load_context_to_state(st, 0)
        tab = TabNesting(st)
        tab._load_from_context()
        assert float(tab.ui.tb_height.text()) == pytest.approx(40.0)
        assert tab._section_height_mm() == pytest.approx(40.0)
        tab.refresh_from_cuts()
        assert tab._section_height_mm() == pytest.approx(40.0)
    finally:
        if had:
            choices["Tubo 80x40 (test)"] = old
        else:
            choices.pop("Tubo 80x40 (test)", None)
