"""
tests/test_nesting_extent_identity.py — bar extent, usage and cut identity.

* A piece mitered in opposite directions is a parallelogram that reaches
  largo + section height; offcuts and the used length must come from that
  real contour, not from ``x_offset + largo``.
* Bar usage is measured by contour area, so mitered pieces that nest into
  each other never read more than 100 %.
* Two cuts with the same name and length but different miters are different
  cuts: counting, removing and undo must not mix them up.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from nestube.models import AppState, Corte  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _tab(cortes, height=200.0):
    from nestube.ui_qt.tab_nesting import TabNesting
    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.margen_tubo = 0.0
    st.cortes = cortes
    tab = TabNesting(st)
    tab._height_override = height
    return tab


def _place(tab, corte, bar, x, fh=False, fv=False):
    from nestube.ui_qt.tab_nesting import PlacedPiece
    while len(tab._bars) <= bar:
        tab._bars.append([])
        tab._bar_lengths.append(6000.0)
    pp = PlacedPiece(corte, bar, x, 0.0, fh, fv, "#888888",
                     tab._compute_poly_local(corte, fh, fv))
    tab._bars[bar].append(pp)
    return pp


def test_parallelogram_piece_end_uses_its_real_contour(qapp):
    from nestube.ui_qt.nesting_scene import piece_end
    par = Corte("P", 1000, 1, inglete1=True, inglete2=True, inglete1_dir="up", inglete2_dir="down")
    tab = _tab([par])
    pp = _place(tab, par, 0, 100.0)
    # 45° miters at 200 mm high: the parallelogram spans 1000 + 200 mm.
    assert piece_end(pp) == pytest.approx(1300.0)
    assert tab._bar_used_length(0) == pytest.approx(1300.0)


def test_remnant_preview_measures_from_the_contour_end(qapp, monkeypatch):
    par = Corte("P", 1000, 1, inglete1=True, inglete2=True, inglete1_dir="up", inglete2_dir="down")
    tab = _tab([par])
    _place(tab, par, 0, 0.0)
    monkeypatch.setattr(tab, "_active_uses_stock", lambda: True)
    tab.ui.remnant_min_entry.setText("100")
    tab.ui.rem_margin_entry.setText("0")
    tab._refresh_remnants()
    # 6000 − 1200 = 4800 mm, not 6000 − 1000 = 5000 mm.
    assert "4800 mm" in tab.ui.remnant_list_lbl.text()


def test_bar_usage_never_passes_100_percent_with_nested_miters(qapp):
    from nestube.ui_qt.nesting_scene import bar_usage_pct
    t = Corte("T", 960, 7, inglete1=True, inglete2=True, inglete1_dir="up", inglete2_dir="up")
    tab = _tab([t])
    # Alternate the trapezoids so they mate flush: nominal lengths add up to
    # 6720 mm on a 6000 mm bar.
    x = 0.0
    for k in range(7):
        _place(tab, t, 0, x, fv=bool(k % 2))
        x += 760.0
    usage = bar_usage_pct(tab._bars[0], 6000.0, tab._section_height_mm())
    assert 0.0 < usage <= 100.0
    tab._update_status()
    pct = float(tab.ui.status_lbl.text().rsplit("·", 1)[1].strip().rstrip("%"))
    assert pct == pytest.approx(usage, abs=0.05)


def test_cuts_differing_only_in_miters_are_not_mixed_up(qapp):
    from nestube.ui_qt.tab_nesting import cut_key, same_cut
    a = Corte("D", 1500, 2, inglete1=True, inglete2=True, inglete1_dir="up", inglete2_dir="up")
    b = Corte("D", 1500, 3, inglete1=True, inglete2=True, inglete1_dir="up", inglete2_dir="down")
    assert not same_cut(a, b) and cut_key(a) != cut_key(b)
    assert same_cut(a, Corte.from_dict(a.to_dict()))

    tab = _tab([a, b])
    tab._mode_switch.setChecked(False)
    tab._update_mode_controls()
    tab._run_simple_nest()
    counts = {id(pi.corte): pi.placed_qty for pi in tab._pieces}
    assert counts[id(a)] == 2 and counts[id(b)] == 3

    # Undo/redo snapshots carry the miters, so a restore keeps each piece on
    # its own cut instead of folding everything onto the first "D 1500".
    tab._restore_bars(tab._serialize_bars())
    assert {id(pi.corte): pi.placed_qty for pi in tab._pieces} == counts
    assert all(pp.corte is a or pp.corte is b for bar in tab._bars for pp in bar)
    assert sum(1 for bar in tab._bars for pp in bar if pp.corte is b) == 3

    # Highlighting one cut highlights only its own pieces.
    pi_b = next(pi for pi in tab._pieces if pi.corte is b)
    tab._highlight_all_instances(pi_b)
    assert len(tab._highlighted_pps) == 3
    assert all(pp.corte is b for pp in tab._highlighted_pps)


def test_layouts_saved_without_miters_still_load(qapp):
    a = Corte("A", 800, 2)
    tab = _tab([a])
    old = [[{"descripcion": "A", "largo": 800, "x_offset": 0.0, "rotation": 0,
             "flipped_h": False, "flipped_v": False, "color": "", "bar_index": 0}]]
    tab._restore_bars(old)
    assert tab._bars[0][0].corte is a
    assert tab._pieces[0].placed_qty == 1
