"""
test_excel_template_export.py — XLSX template download + import + cuts export (§27).

Regression for the "expected ...MultiCellRange" crash: DataValidation.sqref must
use SPACE-separated ranges. Also covers the import round-trip and cuts export.

conftest stubs openpyxl with a MagicMock, so these restore the real library
(skipping if it isn't installed) and reload the export modules against it.
"""
import importlib
import os
import sys
import tempfile

import pytest


@pytest.fixture
def real_openpyxl(monkeypatch):
    for mod in list(sys.modules):
        if mod == "openpyxl" or mod.startswith("openpyxl."):
            monkeypatch.delitem(sys.modules, mod, raising=False)
    opx = pytest.importorskip("openpyxl")
    if not hasattr(opx, "Workbook") or not hasattr(opx, "load_workbook"):
        pytest.skip("openpyxl not available (only the test stub)")
    # Reload the export modules so their module-level `from openpyxl...` imports
    # bind to the real library, not the stub captured at first import.
    for name in ("nestify.excel_import", "nestify.cuts_export"):
        if name in sys.modules:
            try:
                importlib.reload(sys.modules[name])
            except Exception:
                monkeypatch.delitem(sys.modules, name, raising=False)
    return opx


def test_save_template_no_multicellrange_crash(real_openpyxl):
    from nestify.excel_import import save_template
    p = os.path.join(tempfile.gettempdir(), "nestify_tpl_test.xlsx")
    save_template(p)                      # must not raise TypeError(MultiCellRange)
    assert os.path.getsize(p) > 0


def test_template_import_round_trip(real_openpyxl):
    from nestify.excel_import import save_template, import_cuts_from_excel
    p = os.path.join(tempfile.gettempdir(), "nestify_tpl_rt.xlsx")
    save_template(p)
    wb = real_openpyxl.load_workbook(p)
    ws = wb.active
    ws.append(["Beam", 1500, 3, "Yes", "up", 45, "No", "", ""])
    ws.append(["Plate", 800, 2, "No", "", 0, "No", "", ""])
    p2 = os.path.join(tempfile.gettempdir(), "nestify_tpl_rt_filled.xlsx")
    wb.save(p2)
    cuts = import_cuts_from_excel(p2)
    assert [c.descripcion for c in cuts] == ["Beam", "Plate"]
    assert cuts[0].largo == 1500.0 and cuts[0].cantidad == 3 and cuts[0].inglete1


def test_cuts_export_to_excel(real_openpyxl):
    from nestify.models import Corte
    from nestify.cuts_export import export_cuts_to_excel
    p = os.path.join(tempfile.gettempdir(), "nestify_cuts_exp.xlsx")
    export_cuts_to_excel(p, [Corte(descripcion="A", largo=1000.0, cantidad=2)])
    assert os.path.getsize(p) > 0
