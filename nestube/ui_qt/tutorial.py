"""
nestube/ui_qt/tutorial.py — interactive guided tour.

A dimmed overlay covers the main window with a spotlight cut out around the
current step's widget, plus a card explaining it (Back / Next / Skip).
Steps switch tabs as the tour progresses so every highlighted control is
really on screen. Launched from Help → Interactive tutorial, and offered
automatically on the very first run (``AppPreferences.tutorial_seen``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from PySide6.QtCore import QEvent, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from nestube import app_config
from nestube.i18n import t
import nestube.ui_qt.theme_qt as _th


@dataclass
class TutorialStep:
    key: str                                   # i18n prefix: tut_<key>_title/_body
    tab: Optional[int] = None                  # main tab to activate first
    target: Optional[Callable[[object], Optional[QWidget]]] = None


def _steps() -> List[TutorialStep]:
    """The tour. Target resolvers are lazy and defensive — a missing widget
    just turns that step into a centered card instead of crashing the tour."""
    return [
        TutorialStep("welcome"),
        TutorialStep("tabs", target=lambda w: w._tabs.tabBar()),
        TutorialStep("cuts_add", tab=1, target=lambda w: w._tab_cortes.ui.add_btn),
        TutorialStep("cuts_params", tab=1, target=lambda w: w._tab_cortes._e_bar_len),
        TutorialStep("cuts_calc", tab=1, target=lambda w: w._tab_cortes.ui.calc_btn),
        TutorialStep("nest_auto", tab=2, target=lambda w: w._tab_nesting.ui.auto_nest_btn),
        TutorialStep("nest_strategy", tab=2, target=lambda w: w._tab_nesting.ui.strategy_combo),
        TutorialStep("nest_opt", tab=2, target=lambda w: w._tab_nesting.ui.opt_combo),
        TutorialStep("nest_manual", tab=2, target=lambda w: w._tab_nesting._view),
        TutorialStep("costs", tab=3),
        TutorialStep("profiles", tab=4),
        TutorialStep("stock", tab=5),
        TutorialStep("jobs_save", tab=0, target=lambda w: w._tab_jobs._create_job_btn),
        TutorialStep("done"),
    ]


class TutorialOverlay(QWidget):
    """Full-window dimmer with a rounded spotlight and an explaining card."""

    PAD = 8          # spotlight padding around the target (px)
    CARD_W = 400

    def __init__(self, window) -> None:
        super().__init__(window)
        self._w = window
        self._steps = _steps()
        self._idx = 0
        self._spot: Optional[QRect] = None

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setGeometry(window.rect())

        self._card = QFrame(self)
        self._card.setObjectName("tutCard")
        self._card.setStyleSheet(
            f"QFrame#tutCard {{background:{_th.BG_MID}; border:1px solid {_th.ACCENT};"
            f" border-radius:8px;}}"
            f"QLabel {{background:transparent; border:none; color:{_th.TEXT_PRI};}}"
            f"QPushButton {{background:{_th.BG_APP}; color:{_th.TEXT_PRI};"
            f" border:1px solid {_th.BORDER}; border-radius:4px; padding:6px 14px;}}"
            f"QPushButton#tutNext {{background:{_th.ACCENT}; color:#FFFFFF;"
            f" border:none; font-weight:bold;}}"
            f"QPushButton#tutNext:hover {{background:{_th.ACCENT_HVR};}}"
        )
        lay = QVBoxLayout(self._card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)

        self._counter = QLabel(self._card)
        self._counter.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold;")
        self._title = QLabel(self._card)
        self._title.setWordWrap(True)
        self._title.setStyleSheet("font-size:15px; font-weight:bold;")
        self._body = QLabel(self._card)
        self._body.setWordWrap(True)
        self._body.setStyleSheet(f"color:{_th.TEXT_SEC};")
        lay.addWidget(self._counter)
        lay.addWidget(self._title)
        lay.addWidget(self._body)

        btn_row = QHBoxLayout()
        self._skip = QPushButton(t("tut_skip"), self._card)
        self._back = QPushButton(t("tut_back"), self._card)
        self._next = QPushButton(t("tut_next"), self._card)
        self._next.setObjectName("tutNext")
        self._skip.clicked.connect(self.finish)
        self._back.clicked.connect(self.prev_step)
        self._next.clicked.connect(self.next_step)
        btn_row.addWidget(self._skip)
        btn_row.addStretch(1)
        btn_row.addWidget(self._back)
        btn_row.addWidget(self._next)
        lay.addLayout(btn_row)
        self._card.setFixedWidth(self.CARD_W)

        window.installEventFilter(self)
        self.show()
        self.raise_()
        self.setFocus()
        self._apply_step()

    # ── Navigation ────────────────────────────────────────────────────────────

    def next_step(self) -> None:
        if self._idx >= len(self._steps) - 1:
            self.finish()
            return
        self._idx += 1
        self._apply_step()

    def prev_step(self) -> None:
        if self._idx > 0:
            self._idx -= 1
            self._apply_step()

    def finish(self) -> None:
        try:
            prefs = app_config.get()
            if not getattr(prefs, "tutorial_seen", False):
                prefs.tutorial_seen = True
                app_config.save(prefs)
        except Exception:
            pass
        self._w.removeEventFilter(self)
        self.hide()
        self.deleteLater()

    # ── Step layout ───────────────────────────────────────────────────────────

    def _apply_step(self) -> None:
        step = self._steps[self._idx]
        if step.tab is not None:
            try:
                self._w._tabs.setCurrentIndex(step.tab)
            except Exception:
                pass
        # Let the tab switch settle before measuring the target's geometry.
        QTimer.singleShot(0, self._position_step)

    def _position_step(self) -> None:
        step = self._steps[self._idx]
        self.setGeometry(self._w.rect())
        target: Optional[QWidget] = None
        if step.target is not None:
            try:
                target = step.target(self._w)
            except Exception:
                target = None
        if target is not None and target.isVisible():
            top_left = target.mapTo(self._w, target.rect().topLeft())
            r = QRect(top_left, target.size())
            self._spot = r.adjusted(-self.PAD, -self.PAD, self.PAD, self.PAD)
        else:
            self._spot = None

        n = len(self._steps)
        self._counter.setText(t("tut_step", i=self._idx + 1, n=n))
        self._title.setText(t(f"tut_{step.key}_title"))
        self._body.setText(t(f"tut_{step.key}_body"))
        self._back.setVisible(self._idx > 0)
        self._next.setText(t("tut_finish") if self._idx == n - 1 else t("tut_next"))
        self._card.adjustSize()

        # Card near the spotlight (below if space, else above), else centered.
        ch = self._card.sizeHint().height()
        if self._spot is not None:
            x = max(12, min(self._spot.x(), self.width() - self.CARD_W - 12))
            below = self._spot.bottom() + 12
            if below + ch + 12 <= self.height():
                y = below
            else:
                y = max(12, self._spot.y() - ch - 12)
        else:
            x = (self.width() - self.CARD_W) // 2
            y = (self.height() - ch) // 2
        self._card.move(int(x), int(y))
        self.update()

    # ── Painting / events ─────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        path.addRect(0, 0, self.width(), self.height())
        if self._spot is not None:
            path.addRoundedRect(self._spot, 6, 6)
        p.fillPath(path, QColor(0, 0, 0, 150))
        if self._spot is not None:
            pen_color = QColor(_th.ACCENT)
            p.setPen(pen_color)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(self._spot, 6, 6)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        # Clicking the dimmed area advances; the card handles its own clicks.
        self.next_step()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        k = event.key()
        if k == Qt.Key.Key_Escape:
            self.finish()
        elif k in (Qt.Key.Key_Right, Qt.Key.Key_Return, Qt.Key.Key_Enter,
                   Qt.Key.Key_Space):
            self.next_step()
        elif k == Qt.Key.Key_Left:
            self.prev_step()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._w and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            QTimer.singleShot(0, self._position_step)
        return False


def start_tutorial(window) -> TutorialOverlay:
    return TutorialOverlay(window)


def maybe_offer_tutorial(window) -> None:
    """Auto-start the tour once, on the very first launch."""
    try:
        if getattr(app_config.get(), "tutorial_seen", False):
            return
    except Exception:
        return
    QTimer.singleShot(800, lambda: start_tutorial(window))
