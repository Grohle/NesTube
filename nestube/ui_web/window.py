"""
nestube/ui_web/window.py
Main window of the web UI: a QWebEngineView showing nestube/web/index.html,
with a QWebChannel bridge to the headless NesTubeApp engine.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QFile, QIODevice, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from nestube.resources import icon_png_path
from nestube.ui_web.bridge import Bridge

# Exposes the bridge as window.NTB with a promise API, plus a hook for events:
#   NTB.call("nest.state").then(res => …)     res = {ok, result, alerts}
#   NTB.on("nest:progress", payload => …)
_BOOTSTRAP = r"""
(function () {
  if (window.NTB) return;
  var listeners = {}, queue = [], ready = false, bridge = null;
  window.NT_NATIVE = true;
  window.NTB = {
    call: function (method, args) {
      return new Promise(function (resolve) {
        var go = function () {
          bridge.call(method, JSON.stringify(args || {}), function (s) {
            var r; try { r = JSON.parse(s); } catch (e) { r = { ok: false, error: String(e), alerts: [] }; }
            resolve(r);
          });
        };
        ready ? go() : queue.push(go);
      });
    },
    on: function (name, fn) { (listeners[name] = listeners[name] || []).push(fn); },
    whenReady: function (fn) { ready ? fn() : queue.push(fn); }
  };
  function init() {
    new QWebChannel(qt.webChannelTransport, function (ch) {
      bridge = ch.objects.bridge;
      bridge.event.connect(function (name, payload) {
        var data; try { data = JSON.parse(payload); } catch (e) { data = payload; }
        (listeners[name] || []).forEach(function (fn) { try { fn(data); } catch (e) { console.error(e); } });
      });
      ready = true;
      queue.splice(0).forEach(function (fn) { fn(); });
    });
  }
  if (typeof qt !== "undefined" && qt.webChannelTransport) init();
  else document.addEventListener("DOMContentLoaded", init);
})();
"""


class _Page(QWebEnginePage):
    """Forward JavaScript console errors to stderr (useful in dev and in logs)."""

    def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            print(f"[web] {os.path.basename(source)}:{line} {message}")


def web_index_path() -> str:
    # nestube/web/index.html — relative to this package, which is also where
    # the PyInstaller spec bundles it (nestube/web).
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "index.html")


class WebMainWindow(QMainWindow):
    def __init__(self, engine) -> None:
        super().__init__()
        self.engine = engine
        self.setWindowTitle("NesTube")
        png = icon_png_path()
        if os.path.isfile(png):
            self.setWindowIcon(QIcon(png))
        self.setMinimumSize(1024, 640)
        # The engine restored the last window geometry; use it for this window.
        self.setGeometry(engine.geometry())

        self.view = QWebEngineView(self)
        self.page = _Page(self.view)
        self.view.setPage(self.page)
        s = self.page.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)

        self.bridge = Bridge(engine, window=self)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject("bridge", self.bridge)
        self.page.setWebChannel(self.channel)
        self._inject_scripts()

        self.view.setUrl(QUrl.fromLocalFile(os.path.abspath(web_index_path())))
        self.setCentralWidget(self.view)

    def _inject_scripts(self) -> None:
        f = QFile(":/qtwebchannel/qwebchannel.js")
        src = ""
        if f.open(QIODevice.OpenModeFlag.ReadOnly):
            src = bytes(f.readAll()).decode("utf-8")
            f.close()
        script = QWebEngineScript()
        script.setName("nestube-bridge")
        script.setSourceCode(src + "\n" + _BOOTSTRAP)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        self.page.scripts().insert(script)

    # Native dialogs opened by the engine centre on its (hidden) geometry, so
    # keep it on top of this window.
    def moveEvent(self, event) -> None:  # noqa: N802
        self.engine.setGeometry(self.geometry())
        super().moveEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self.engine.setGeometry(self.geometry())
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        # The engine owns the unsaved-changes prompt and saves window geometry.
        self.engine.setGeometry(self.geometry())
        if self.engine.close():
            event.accept()
        else:
            event.ignore()
