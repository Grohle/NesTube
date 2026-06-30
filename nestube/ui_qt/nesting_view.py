"""
nestube/ui_qt/nesting_view.py
QGraphicsView with smooth zoom (Ctrl+wheel), pan (middle-button or Ctrl+drag),
and scene-coordinate mouse signals forwarded to TabNesting.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QGraphicsView

import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.nesting_scene import NestingScene

# Zoom limits/step for the wheel zoom. The view's transform scale is clamped to
# [_ZOOM_MIN, _ZOOM_MAX]; each wheel notch multiplies/divides the scale by
# _ZOOM_STEP (≈15% per notch) about the cursor position.
_ZOOM_MIN = 0.05
_ZOOM_MAX = 40.0
_ZOOM_STEP = 1.15


class NestingView(QGraphicsView):
    """Interactive view for NestingScene.

    Emits scene-coordinate signals for the nesting tab to handle.
    All piece placement logic stays in TabNesting — the view is purely
    responsible for display, zoom, and pan.
    """

    # scene-coord mouse events
    scene_pressed  = Signal(QPointF)
    scene_moved    = Signal(QPointF)
    scene_released = Signal(QPointF)
    scene_right_pressed = Signal(QPointF)
    zoom_changed   = Signal(int)   # current zoom as a percentage of the fit scale

    def __init__(self, scene: NestingScene, parent=None) -> None:
        super().__init__(scene, parent)
        self._scene_ref = scene
        self._zoom_factor: float = 1.0
        # Baseline scale at which the whole scene fits the viewport. 100% on the
        # toolbar zoom button == this scale; updated by fit_scene / initial scale.
        self._fit_scale: float = 0.0
        self._pan_active: bool = False
        self._pan_start_pos = None
        # When True, a plain left-drag on empty canvas pans the view. The tab
        # enables this only while no piece is selected/floating, so left-drag is
        # never ambiguous with placing/moving a piece.
        self._left_pan_enabled: bool = True

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor(_th.BG_CANVAS)))
        # Track the mouse with no button held so a "picked up" piece follows the
        # cursor freely (click-to-move), not only while dragging.
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        # Initial scale: fit ~6000 mm wide into the viewport
        self._apply_initial_scale()

    # ── Public API ────────────────────────────────────────────────────────────

    def zoom_level(self) -> float:
        return self._zoom_factor

    def zoom_percent(self) -> int:
        """Current zoom as a percentage of the fit-to-view scale (fit == 100%)."""
        base = self._fit_scale or self._zoom_factor or 1.0
        return max(1, round(self._zoom_factor / base * 100))

    def _emit_zoom(self) -> None:
        self.zoom_changed.emit(self.zoom_percent())

    def update_theme(self) -> None:
        """Refresh view colors to the current theme."""
        self.setBackgroundBrush(QBrush(QColor(_th.BG_CANVAS)))

    def fit_scene(self) -> None:
        """Fit scene into viewport with uniform scaling for proportional bars.

        This is also the "100%/centre" action: it recomputes the fit scale,
        applies it and centres the content between the side panels.
        """
        sr = self.scene().sceneRect()
        if sr.width() <= 0 or sr.height() <= 0:
            return
        vw = self.viewport().width() or 800
        vh = self.viewport().height() or 600
        sx = vw / sr.width()
        sy = vh / sr.height()
        s = min(sx, sy)
        self.resetTransform()
        self.scale(s, s)
        self._zoom_factor = s
        self._fit_scale = s          # this scale is, by definition, 100%
        self.centerOn(sr.center())
        self._emit_zoom()

    def reset_view(self) -> None:
        self.resetTransform()
        self._zoom_factor = 1.0
        self._apply_initial_scale()

    # ── Events ────────────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        self._zoom_at(event.position(), event.angleDelta().y())
        event.accept()

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint() if hasattr(event.position(), "toPoint") else event.pos()
        scene_pos = self.mapToScene(pos)

        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = True
            self._pan_start_pos = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if (event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._pan_active = True
            self._pan_start_pos = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.scene_right_pressed.emit(scene_pos)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Plain left-drag pans the canvas — but only on empty space and only
            # while nothing is selected/floating (set by the tab), so it never
            # clashes with selecting/placing a piece.
            item = self.itemAt(pos)
            on_piece = item is not None and hasattr(item, "pp_ref")
            if self._left_pan_enabled and not on_piece:
                self._pan_active = True
                self._pan_start_pos = pos
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
            self.scene_pressed.emit(scene_pos)

        super().mousePressEvent(event)

    def set_left_pan(self, enabled: bool) -> None:
        """Enable/disable plain left-drag panning (off while a piece is selected
        or floating)."""
        self._left_pan_enabled = bool(enabled)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position().toPoint() if hasattr(event.position(), "toPoint") else event.pos()
        if self._pan_active and self._pan_start_pos is not None:
            delta = pos - self._pan_start_pos
            self._pan_start_pos = pos
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
            return

        scene_pos = self.mapToScene(pos)
        self.scene_moved.emit(scene_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        pos = event.position().toPoint() if hasattr(event.position(), "toPoint") else event.pos()
        if self._pan_active and event.button() in (
            Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton
        ):
            self._pan_active = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(pos)
            self.scene_released.emit(scene_pos)

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        # Forward all key events to parent — TabNesting handles them
        event.ignore()

    # ── Sticky bar labels ──────────────────────────────────────────────────────

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        # "Sticky" bar labels ("Bar N"): drawn in VIEWPORT space (resetTransform)
        # so they keep a constant 12px bold size at any zoom, but anchored to each
        # bar's scene-Y (mapped to viewport) with a fixed 6px gap above the bar —
        # so they track the bars while panning/zooming instead of scaling with them.
        scene = self._scene_ref
        labels = getattr(scene, "_bar_labels_info", [])
        if not labels:
            return
        painter.save()
        painter.resetTransform()           # paint in pixel space, not scene units
        font = QFont()
        font.setBold(True)
        font.setPixelSize(12)              # constant on-screen label size
        painter.setFont(font)
        painter.setPen(QPen(QColor(_th.TEXT_PRI)))
        # Labels are painted in viewport space (constant pixel size, so they
        # don't scale with zoom) but anchored to each bar's top-left corner
        # with a fixed gap above it — keeping a consistent margin while zooming
        # and panning, instead of sticking to the viewport edge.
        _GAP_PX = 6
        for text, bar_y_scene in labels:
            vp_pt = self.mapFromScene(QPointF(0.0, bar_y_scene))
            x = vp_pt.x() + 2
            y = vp_pt.y() - _GAP_PX  # text baseline sits just above the bar top
            painter.drawText(int(x), int(y), text)
        painter.restore()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _zoom_at(self, viewport_pos, delta_y: int) -> None:
        """Zoom in/out by one _ZOOM_STEP, keeping the point under the cursor fixed.

        Wheel-up zooms in, wheel-down out; the new factor is clamped to
        [_ZOOM_MIN, _ZOOM_MAX]. To anchor the cursor, we record the scene point
        under it before scaling and translate by the drift afterwards."""
        factor = _ZOOM_STEP if delta_y > 0 else 1.0 / _ZOOM_STEP
        new_zoom = self._zoom_factor * factor

        if new_zoom < _ZOOM_MIN or new_zoom > _ZOOM_MAX:
            return

        # Zoom centred at cursor
        scene_before = self.mapToScene(viewport_pos.toPoint()
                                       if hasattr(viewport_pos, "toPoint")
                                       else viewport_pos)
        self.scale(factor, factor)
        self._zoom_factor = new_zoom

        scene_after = self.mapToScene(viewport_pos.toPoint()
                                      if hasattr(viewport_pos, "toPoint")
                                      else viewport_pos)
        delta = scene_after - scene_before
        self.translate(delta.x(), delta.y())
        self._emit_zoom()

    def _apply_initial_scale(self) -> None:
        """Scale so a standard bar fits the viewport width before any content exists.

        target_mm = 6500 (a 6000mm bar plus margin); the scale maps that span to
        the current viewport width, clamped to the zoom limits. Used as the 100%
        baseline until fit_scene() recomputes it for the real content."""
        vw = self.viewport().width() or 800
        target_mm = 6500.0
        scale = vw / target_mm
        scale = max(_ZOOM_MIN, min(_ZOOM_MAX, scale))
        self.resetTransform()
        self.scale(scale, scale)
        self._zoom_factor = scale
        # Treat the initial fit-width scale as the 100% baseline until fit_scene
        # recomputes it for the actual content.
        if not self._fit_scale:
            self._fit_scale = scale
        self._emit_zoom()
