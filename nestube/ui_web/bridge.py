"""
nestube/ui_web/bridge.py
QWebChannel bridge between the HTML UI and the headless NesTubeApp engine.

JavaScript calls ``bridge.call(method, argsJson)`` and gets back a JSON string:

    {"ok": true,  "result": <any>, "alerts": [{kind, title, msg}, ...]}
    {"ok": false, "error": "<message>", "alerts": [...]}

``alerts`` carries every QMessageBox the engine tried to show during the call
(information / warning / critical / question). They are never shown natively;
the web UI renders them with its own alert component. Questions are answered
with ``_answer`` (default "yes") because the web UI asks the user *before*
calling — so a confirmation is never asked twice.

Long-running work (auto-nest) reports through the ``event(name, json)`` signal.
"""
from __future__ import annotations

import contextlib
import json
import traceback
from typing import Any, Dict, List

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox

_SB = QMessageBox.StandardButton
_ANSWERS = {
    "yes": _SB.Yes, "no": _SB.No, "save": _SB.Save, "discard": _SB.Discard,
    "cancel": _SB.Cancel, "ok": _SB.Ok,
}


class _Capture:
    """Swap QMessageBox's static helpers for collectors for one bridge call."""

    def __init__(self, answer: str = "yes") -> None:
        self.alerts: List[Dict[str, str]] = []
        self.answer = answer

    def _collector(self, kind: str):
        cap = self

        def _fn(parent=None, title="", text="", *args, **kwargs):
            cap.alerts.append({"kind": kind, "title": str(title), "msg": str(text)})
            if kind == "question":
                buttons = args[0] if args else kwargs.get("buttons")
                ans = _ANSWERS.get(cap.answer, _SB.Yes)
                # Save/Discard/Cancel questions: map yes→Save, no→Discard.
                try:
                    if buttons is not None and not (buttons & ans):
                        if cap.answer in ("yes", "save") and buttons & _SB.Save:
                            ans = _SB.Save
                        elif cap.answer in ("no", "discard") and buttons & _SB.Discard:
                            ans = _SB.Discard
                except TypeError:
                    pass
                return ans
            return _SB.Ok
        return staticmethod(_fn)

    @contextlib.contextmanager
    def active(self):
        saved = {k: QMessageBox.__dict__.get(k) for k in
                 ("information", "warning", "critical", "question")}
        saved_exec = QMessageBox.__dict__.get("exec")
        cap = self

        def _exec(box, *a, **k):
            # Instance-style message boxes (custom buttons): record and cancel.
            cap.alerts.append({"kind": "warning", "title": box.windowTitle(), "msg": box.text()})
            return 0
        try:
            for k in saved:
                setattr(QMessageBox, k, self._collector(k))
            QMessageBox.exec = _exec
            yield self
        finally:
            for k, v in saved.items():
                if v is not None:
                    setattr(QMessageBox, k, v)
                else:
                    with contextlib.suppress(AttributeError):
                        delattr(QMessageBox, k)
            if saved_exec is not None:
                QMessageBox.exec = saved_exec
            else:
                with contextlib.suppress(AttributeError):
                    delattr(QMessageBox, "exec")


class Bridge(QObject):
    """The object exposed to JavaScript as ``bridge``."""

    event = Signal(str, str)   # (name, json payload)

    def __init__(self, engine, window=None) -> None:
        super().__init__()
        self.engine = engine
        self.window = window
        from nestube.ui_web.api_nesting import NestingAPI
        from nestube.ui_web.api_data import DataAPI
        self.nesting = NestingAPI(self)
        self.data = DataAPI(self)

    # ── dispatch ────────────────────────────────────────────────────────────
    @Slot(str, str, result=str)
    def call(self, method: str, args_json: str) -> str:
        try:
            args = json.loads(args_json or "{}") or {}
        except ValueError:
            args = {}
        answer = str(args.pop("_answer", "yes"))
        cap = _Capture(answer)
        try:
            target = self._resolve(method)
            with cap.active():
                result = target(**args)
            return json.dumps({"ok": True, "result": result, "alerts": cap.alerts},
                              ensure_ascii=False, default=_json_default)
        except Exception as exc:  # report, never crash the UI
            traceback.print_exc()
            return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}",
                               "alerts": cap.alerts}, ensure_ascii=False,
                              default=_json_default)

    def _resolve(self, method: str):
        ns, _, name = method.partition(".")
        api = {"nest": self.nesting, "data": self.data}.get(ns)
        fn = getattr(api, name, None) if api is not None and not name.startswith("_") else None
        if fn is None or not callable(fn):
            raise AttributeError(f"unknown bridge method {method!r}")
        return fn

    def emit(self, name: str, payload: Any) -> None:
        self.event.emit(name, json.dumps(payload, ensure_ascii=False, default=_json_default))

    # Native file dialogs stay native (OS look on Windows); parent them to the
    # visible web window so they centre over it.
    def dialog_parent(self):
        return self.window or self.engine

    def pick_open_file(self, title: str, filt: str) -> str:
        path, _ = QFileDialog.getOpenFileName(self.dialog_parent(), title, "", filt)
        return path


def _json_default(o):
    if hasattr(o, "to_dict"):
        return o.to_dict()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)
