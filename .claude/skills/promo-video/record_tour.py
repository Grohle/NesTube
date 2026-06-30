#!/usr/bin/env python3
"""
record_tour.py — drive the live NesTube app through a scripted tour and screen-
record it, producing raw live footage for the promo video.

Runs INSIDE the app's Qt event loop on an X display (Xvfb in CI, or a real one).
A smooth, eased cursor glides between tabs, switches them, and dwells on each so
the viewer briefly sees every part of the app actually running. ffmpeg x11grab
records the display for exactly the tour's duration, so the caption timeline the
script writes out lines up frame-accurately with the footage.

This is normally launched by record_live.sh (which starts Xvfb + the app env).
Output: a raw H.264 clip and a timeline.json of (start, end, caption) segments.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/NesTube")

from PySide6.QtCore import Qt, QTimer, QElapsedTimer, QPointF
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QDialog

from nestube import app_config
from nestube.ui_qt.fonts_qt import register_bundled_fonts
from nestube.ui_qt.theme_qt import build_stylesheet

# Captions per tab title fragment (matched case-insensitively on the tab text).
CAPTIONS = {
    "job":      {"es": "Explorador de trabajos",        "en": "Job explorer"},
    "corte":    {"es": "Lista de cortes y algoritmos",  "en": "Cut list & algorithms"},
    "cut":      {"es": "Lista de cortes y algoritmos",  "en": "Cut list & algorithms"},
    "anidad":   {"es": "Nesting visual e interactivo",  "en": "Visual interactive nesting"},
    "nest":     {"es": "Nesting visual e interactivo",  "en": "Visual interactive nesting"},
    "coste":    {"es": "Costes y peso por pieza",        "en": "Per-piece cost & weight"},
    "cost":     {"es": "Costes y peso por pieza",        "en": "Per-piece cost & weight"},
    "perfil":   {"es": "Catálogo de perfiles y tubos",  "en": "Profile & tube catalogue"},
    "profile":  {"es": "Profile & tube catalogue",       "en": "Profile & tube catalogue"},
    "stock":    {"es": "Inventario de stock y retales",  "en": "Stock & offcut inventory"},
}


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


class TourDriver:
    """A tiny keyframe animation engine running on a 60 Hz QTimer."""

    def __init__(self, window, ff_cmd, fps, lang, out_timeline):
        self.w = window
        self.ff_cmd = ff_cmd
        self.fps = fps
        self.lang = lang
        self.out_timeline = out_timeline
        self.ff = None
        self.tabbar = window._tabs.tabBar()
        self.clock = QElapsedTimer()
        self.actions: list = []
        self.idx = 0
        self.action_start = 0.0
        self.cursor_from = QPointF(0, 0)
        self.segments: list = []          # (t_start, t_end, caption)
        self._seg_open = None
        self.timer = QTimer()
        self.timer.setInterval(int(1000 / 60))
        self.timer.timeout.connect(self._tick)

    # ── storyboard construction ──────────────────────────────────────────
    def _tab_center(self, i) -> QPointF:
        r = self.tabbar.tabRect(i)
        g = self.tabbar.mapToGlobal(r.center())
        return QPointF(g.x(), g.y())

    def build(self):
        n = self.w._tabs.count()
        # Start the cursor near the first tab.
        self.cursor_from = self._tab_center(0)
        QCursor.setPos(int(self.cursor_from.x()), int(self.cursor_from.y()))
        for i in range(n):
            title = self.w._tabs.tabText(i).replace("&", "").strip().lower()
            cap = ""
            for key, val in CAPTIONS.items():
                if key in title:
                    cap = val.get(self.lang, val["en"]); break
            target = self._tab_center(i)
            # Glide to the tab, switch to it, then dwell so the panel is readable.
            self.actions.append(("move", target, 0.9))
            self.actions.append(("tab", i, 0.0))
            self.actions.append(("caption", cap, 0.05))
            self.actions.append(("dwell", None, 2.6))
            self.actions.append(("endcap", None, 0.0))

    # ── run loop ─────────────────────────────────────────────────────────
    def start(self):
        self.clock.start()
        self.ff = subprocess.Popen(self.ff_cmd, stdin=subprocess.PIPE,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.action_start = 0.0
        self.timer.start()

    def _now(self) -> float:
        return self.clock.elapsed() / 1000.0

    def _tick(self):
        if self.idx >= len(self.actions):
            return self._finish()
        kind, arg, dur = self.actions[self.idx]
        t = self._now() - self.action_start
        if kind == "move":
            f = smoothstep(t / dur) if dur > 0 else 1.0
            x = self.cursor_from.x() + (arg.x() - self.cursor_from.x()) * f
            y = self.cursor_from.y() + (arg.y() - self.cursor_from.y()) * f
            QCursor.setPos(int(round(x)), int(round(y)))
            if t >= dur:
                self.cursor_from = arg
                self._advance()
        elif kind == "tab":
            self.w._tabs.setCurrentIndex(arg)
            self._advance()
        elif kind == "caption":
            self._seg_open = (self._now(), arg)
            self._advance()
        elif kind == "endcap":
            if self._seg_open:
                s, cap = self._seg_open
                self.segments.append((s, self._now(), cap))
                self._seg_open = None
            self._advance()
        elif kind == "dwell":
            if t >= dur:
                self._advance()

    def _advance(self):
        self.idx += 1
        self.action_start = self._now()

    def _finish(self):
        self.timer.stop()
        total = self._now()
        if self.ff and self.ff.poll() is None:
            try:
                self.ff.communicate(input=b"q", timeout=10)
            except Exception:
                self.ff.terminate()
        Path(self.out_timeline).write_text(
            json.dumps({"duration": total, "fps": self.fps,
                        "segments": self.segments}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        # ffmpeg has finalised the mp4 by now; exit hard so a lingering Qt
        # modal or timer can't keep the process alive past the tour.
        sys.stdout.flush()
        os._exit(0)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", default=":99")
    ap.add_argument("--out", default="raw_tour.mp4")
    ap.add_argument("--timeline", default="timeline.json")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--lang", default="es")
    args = ap.parse_args()
    W, H = (int(x) for x in args.size.lower().split("x"))

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("NesTube")
    register_bundled_fonts()
    # Force the app UI language to match the promo language. app_config.load()
    # re-reads the stored config (which may be 'es') every call — including
    # inside NesTubeApp.__init__ — so patch it to override the language field,
    # otherwise the recorded UI ignores --lang.
    import nestube.i18n as i18n
    _orig_load = app_config.load

    def _load_lang():
        prefs = _orig_load()
        prefs.language = args.lang
        return prefs

    app_config.load = _load_lang
    i18n.set_language(args.lang)
    app.setStyleSheet(build_stylesheet("dark"))
    from nestube.ui_qt.app import NesTubeApp
    w = NesTubeApp()
    # No window manager under Xvfb honours showFullScreen(), so size explicitly.
    w.setWindowFlag(Qt.FramelessWindowHint, True)
    w.setGeometry(0, 0, W, H)
    w.show()

    ff_cmd = [
        "ffmpeg", "-y", "-f", "x11grab", "-draw_mouse", "1",
        # Tag every grabbed frame with its real capture time. Without this,
        # x11grab assumes a perfectly uniform rate; when the encoder can't keep
        # up (heavy renders) frames are dropped but the survivors are spaced
        # evenly, so the footage timebase no longer matches wall-clock — and the
        # wall-clock-based caption timeline drifts badly out of sync. With real
        # timestamps, the CFR resample below reproduces true timing (freezing a
        # frame where capture lagged) so footage time == tour time == timeline.
        "-use_wallclock_as_timestamps", "1",
        "-framerate", str(args.fps), "-video_size", args.size,
        "-i", args.display, "-c:v", "libx264", "-preset", "ultrafast",
        "-crf", "16", "-pix_fmt", "yuv420p", "-vsync", "cfr",
        "-r", str(args.fps), args.out,
    ]
    driver = TourDriver(w, ff_cmd, args.fps, args.lang, args.timeline)

    def kickoff():
        # Close the first-run About/update dialog (and any other modal).
        for tw in QApplication.topLevelWidgets():
            if isinstance(tw, QDialog) and tw.isVisible():
                tw.close()
        # Load the demo job so every tab shows real content (cuts, packed bars,
        # costs) — an empty app looks like a fresh install, not a working tool.
        try:
            from nestube.database import get_geometry_db
            jobs = get_geometry_db().list_jobs()
            if jobs:
                first = jobs[0]
                jid = (first["id"] if isinstance(first, dict)
                       else first[0] if isinstance(first, (list, tuple))
                       else getattr(first, "id", None))
                if jid is not None:
                    w._tab_jobs._open_job(jid)
        except Exception as exc:  # never let demo data block the recording
            print("demo job load failed:", exc)
        w._tabs.setCurrentIndex(0)
        w.setGeometry(0, 0, W, H)
        driver.build()
        QTimer.singleShot(600, driver.start)

    QTimer.singleShot(1200, kickoff)
    app.exec()


if __name__ == "__main__":
    main()
