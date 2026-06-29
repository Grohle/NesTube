"""
test_export_headers.py — regression guard for §2.1/§17 export headers.

The quote PDF / DOCX length column header used t("placeholder_length") without
passing the unit kwarg, leaving the literal "{u}" placeholder in the output.
This verifies the DOCX export (a real dependency) substitutes the unit and never
emits an unfilled format placeholder. The fpdf/openpyxl/docx libs are stubbed in
conftest, so we restore the real python-docx (skipping if it isn't installed).
"""
import importlib
import os
import sys

import pytest


@pytest.fixture
def real_docx(monkeypatch):
    """Drop the conftest MagicMock stub and import the real python-docx."""
    for mod in list(sys.modules):
        if mod == "docx" or mod.startswith("docx."):
            monkeypatch.delitem(sys.modules, mod, raising=False)
    docx = pytest.importorskip("docx")  # real lib, or skip the test
    if not hasattr(docx, "Document") or not callable(getattr(docx, "Document")):
        pytest.skip("python-docx not available (only the test stub)")
    # python-docx loaded via stub may have left a mock Document; ensure it's real.
    try:
        importlib.reload(docx)
    except Exception:
        pass
    return docx


def _state():
    from nestify.models import AppState, Corte
    st = AppState()
    st.descripcion = "Bastidor"
    st.longitud_barra = 6000.0
    st.cortes = [Corte(descripcion="Larguero", largo=2000.0, cantidad=3),
                 Corte(descripcion="Travesaño", largo=1500.0, cantidad=2)]
    st.barras_necesarias = [[2000, 2000, 1500], [2000, 1500]]
    return st


def test_docx_quote_headers_have_no_unfilled_placeholder(real_docx, tmp_path):
    from nestify.export_utils import _write_docx
    from nestify import units

    path = os.path.join(str(tmp_path), "quote.docx")
    _write_docx(path, _state())

    doc = real_docx.Document(path)
    assert doc.tables, "quote DOCX has no table"
    headers = [c.text for c in doc.tables[0].rows[0].cells]

    # No header may contain an unsubstituted format placeholder.
    assert not any("{" in h or "}" in h for h in headers), headers
    # The length column carries the actual unit.
    assert any(units.u_len() in h for h in headers), headers
