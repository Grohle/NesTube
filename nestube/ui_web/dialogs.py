"""
nestube/ui_web/dialogs.py
Engine dialogs shown by the HTML interface instead of as Qt windows.

A bridge call runs engine code synchronously, so the page cannot answer a
dialog in the middle of it. Instead, while a call runs, the ``exec()`` of each
dialog listed here is replaced:

* no answer yet → the dialog records what the page needs to draw it
  (``needs``) and is cancelled, so the engine stops where a cancelled dialog
  would stop;
* the page draws the dialog, the user answers, and the page repeats the same
  call with ``_answers = {<dialog>: <answer>}``;
* on the repeat the dialog is "accepted" with that answer and the engine
  carries on exactly as if the user had clicked OK in the Qt window.

Everything before the dialog runs twice; the flows covered here only read
state before their dialog, so repeating them is safe.
"""
from __future__ import annotations

import contextlib
from typing import Any, Dict, List, Optional

_ACCEPTED, _REJECTED = 1, 0


# ── material / stock search ──────────────────────────────────────────────────
def _material_rows(dlg) -> List[Dict[str, Any]]:
    from PySide6.QtCore import Qt
    from nestube.ui_qt.dialogs.stock_material_search_dialog import MaterialSelection
    rows = []
    for i in range(dlg._list.count()):
        item = dlg._list.item(i)
        sel = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(sel, MaterialSelection):
            continue
        bar = sel.stock_bar
        rows.append({
            "label": item.text(), "source": sel.source, "profile_name": sel.profile_name,
            "material": sel.material, "quality": sel.quality,
            "stock_id": getattr(bar, "id", None),
            "length": (bar.retal_length if bar is not None and bar.is_retal
                       else getattr(bar, "length", None)),
            "quantity": getattr(bar, "quantity", None),
        })
    return rows


def material_options(mode: str = "profile", query: str = "", min_len: str = "") -> Dict[str, Any]:
    """Rows of the material search for one mode — the same lists, filters and
    order as the Qt dialog (it is built off-screen and read)."""
    from nestube.ui_qt.dialogs.stock_material_search_dialog import StockMaterialSearchDialog
    dlg = StockMaterialSearchDialog(None, initial_query=query or "", default_mode=mode)
    try:
        if min_len is not None:
            dlg._min_len.setText(str(min_len))
        dlg._search.setText(query or "")
        dlg._set_mode(mode)
        return {"mode": mode, "query": query or "", "rows": _material_rows(dlg)}
    finally:
        dlg.deleteLater()


def _material_exec(dlg, answer: Optional[dict], cap) -> int:
    from nestube.ui_qt.dialogs.stock_material_search_dialog import MaterialSelection
    if answer is None:
        cap.ask({"dialog": "material", "mode": dlg._mode, "query": dlg._search.text(),
                 "min_len": dlg._min_len.text()})
        return _REJECTED
    bar = None
    if answer.get("stock_id") is not None:
        from nestube.stock_db import get_stock
        bar = next((b for b in get_stock().bars if b.id == answer["stock_id"]), None)
    dlg.result_selection = MaterialSelection(
        source=str(answer.get("source", "profile")),
        profile_name=str(answer.get("profile_name", "")),
        material=str(answer.get("material", "")),
        quality=str(answer.get("quality", "")),
        stock_bar=bar,
    )
    return _ACCEPTED


# ── cutting height (profile face) ────────────────────────────────────────────
def _height_exec(dlg, answer: Optional[dict], cap) -> int:
    if answer is None:
        cap.ask({"dialog": "height",
                 "heights": [[str(label), float(v)] for label, v in dlg._heights],
                 "chosen": dlg._chosen})
        return _REJECTED
    dlg._chosen = float(answer["value"])
    return _ACCEPTED


# ── save a drawn profile ─────────────────────────────────────────────────────
def _profile_save_exec(dlg, answer: Optional[dict], cap) -> int:
    ui = dlg.ui
    if answer is None:
        combo = ui.combo_material
        cap.ask({"dialog": "profile_save",
                 "title": dlg.windowTitle(),
                 "name": ui.e_name.text(), "quality": ui.e_quality.text(),
                 "notes": ui.e_notes.toPlainText(), "fields": ui.e_fields.text(),
                 "material": combo.currentText(),
                 "materials": [[combo.itemText(i), float(combo.itemData(i) or 0.0)]
                               for i in range(combo.count())],
                 "names": sorted({cp.name for cp in _custom_profiles() if cp.name})})
        return _REJECTED
    ui.e_name.setText(str(answer.get("name", "")))
    ui.e_quality.setText(str(answer.get("quality", "")))
    ui.e_notes.setPlainText(str(answer.get("notes", "")))
    ui.e_fields.setText(str(answer.get("fields", "")))
    mat = str(answer.get("material", ""))
    idx = ui.combo_material.findText(mat)
    if idx < 0 and mat:
        ui.combo_material.addItem(mat, 7.85)
        idx = ui.combo_material.count() - 1
    ui.combo_material.setCurrentIndex(max(0, idx))
    dlg._confirm()
    return _ACCEPTED if dlg.result is not None else _REJECTED


def _custom_profiles():
    from nestube import app_config
    return getattr(app_config.get(), "custom_profiles", []) or []


# ── choose the nestings to export ────────────────────────────────────────────
def _nesting_selector_exec(dlg, answer: Optional[dict], cap) -> int:
    if answer is None:
        cap.ask({"dialog": "nesting_selector",
                 "rows": [[i, name, bars, pieces] for i, name, bars, pieces in dlg._rows]})
        return _REJECTED
    chosen = {int(i) for i in answer.get("indices", [])}
    for (ctx_idx, _name, _b, _p), cb in zip(dlg._rows, dlg._checkboxes):
        cb.setChecked(ctx_idx in chosen)
    return _ACCEPTED if chosen else _REJECTED


def _targets():
    from nestube.ui_qt.dialogs.nesting_selector_dialog import NestingSelectorDialog
    from nestube.ui_qt.dialogs.profile_height_dialog import ProfileHeightDialog
    from nestube.ui_qt.dialogs.profile_save_dialog import ProfileSaveDialog
    from nestube.ui_qt.dialogs.stock_material_search_dialog import StockMaterialSearchDialog
    return {
        "material": (StockMaterialSearchDialog, _material_exec),
        "height": (ProfileHeightDialog, _height_exec),
        "profile_save": (ProfileSaveDialog, _profile_save_exec),
        "nesting_selector": (NestingSelectorDialog, _nesting_selector_exec),
    }


@contextlib.contextmanager
def web_dialogs(cap):
    """Swap the covered dialogs' ``exec`` for the ask/answer protocol above
    for the duration of one bridge call (``cap`` is the call's _Capture)."""
    saved = []
    try:
        for name, (cls, handler) in _targets().items():
            saved.append((cls, cls.__dict__.get("exec")))

            def _exec(dlg, *a, _name=name, _handler=handler, **k):
                if cap.needs is not None:      # one question per call
                    return _REJECTED
                return _handler(dlg, cap.answers.get(_name), cap)
            cls.exec = _exec
        yield
    finally:
        for cls, orig in saved:
            if orig is not None:
                cls.exec = orig
            else:
                with contextlib.suppress(AttributeError):
                    del cls.exec
