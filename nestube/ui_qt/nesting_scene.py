"""
nestube/ui_qt/nesting_scene.py
QGraphicsScene + QGraphicsItems for the interactive nesting canvas.
Scene coordinates: 1 scene unit = 1 mm.  Bar i starts at Y = i * (section_h + BAR_GAP).
Non-uniform view scaling (fit_scene) makes bars visible; text items use
ItemIgnoresTransformations so labels remain readable at any zoom.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsPolygonItem, QGraphicsRectItem,
    QGraphicsScene,
)

import nestube.ui_qt.theme_qt as _th
from nestube import app_config
from nestube.i18n import t

BAR_GAP_MM: float = 500.0  # vertical gap between bars (room for labels + legends)

_RETAL_COLOR = "#2E7D32"
COLOR_SELECT_MULTI = "#FF00FF"  # magenta outline for multi-piece selection


def _outline_pen(width_px: float = 1.0, color: str = "#000000") -> QPen:
    """Thin black cosmetic outline (constant px width at any zoom) — the shared
    'cartoon' edge used by bars, pieces and remnants."""
    pen = QPen(QColor(color), width_px)
    pen.setCosmetic(True)
    return pen


def _srgb_to_linear(c: float) -> float:
    """Linearise one 0–1 sRGB channel (the WCAG relative-luminance transfer curve)."""
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance of a colour: 0.2126·R + 0.7152·G + 0.0722·B on
    linearised channels."""
    c = QColor(hex_color)
    r = _srgb_to_linear(c.redF())
    g = _srgb_to_linear(c.greenF())
    b = _srgb_to_linear(c.blueF())
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(l1: float, l2: float) -> float:
    """WCAG contrast ratio (lighter+0.05)/(darker+0.05) of two luminances."""
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


_LUM_WHITE = 1.0
_LUM_DARK = 0.012  # pre-computed for #1C1C1E


def _text_color_for_bg(hex_color: str) -> str:
    """WCAG 2.1: pick white or dark text for maximum contrast ratio.

    Reference implementation for piece labels: compares white vs near-black
    (#1C1C1E) against the actual piece-fill colour and returns whichever wins,
    so labels stay legible on any cut colour."""
    lum = _relative_luminance(hex_color)
    cr_white = _contrast_ratio(_LUM_WHITE, lum)
    cr_dark = _contrast_ratio(lum, _LUM_DARK)
    return "#FFFFFF" if cr_white >= cr_dark else "#1C1C1E"


def _mm_poly(local_pts: List[Tuple[float, float]], dx: float, dy: float) -> QPolygonF:
    """Build a QPolygonF from local (mm) points translated by (dx, dy) scene units."""
    poly = QPolygonF()
    for x, y in local_pts:
        poly.append(QPointF(x + dx, y + dy))
    return poly


# ── Remnant item ─────────────────────────────────────────────────────────────

class RemantItem(QGraphicsRectItem):
    """Solid green block marking a generated remnant (drawn like a piece)."""

    def __init__(self, bar_y: float, bar_h: float, x_start: float, width: float) -> None:
        super().__init__(x_start, bar_y, width, bar_h)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        # Filled green so the remnant reads as a piece on the bar (not just a
        # faint hatch). A solid darker-green border keeps it distinguishable.
        fill = QColor(_RETAL_COLOR)
        fill.setAlpha(150)
        self.setBrush(QBrush(fill))
        self.setPen(_outline_pen())
        self.setZValue(0.5)


# ── Bar background item ───────────────────────────────────────────────────────

class BarBackground(QGraphicsRectItem):
    """Solid bar rectangle — not interactive."""

    def __init__(self, bar_idx: int, x: float, y: float, w: float, h: float) -> None:
        # Rect = full bar (w = bar length mm, h = section height mm). BG_CARD fill
        # with a thin BORDER edge; z=0 so placed pieces (z=1) sit on top.
        super().__init__(x, y, w, h)
        self.bar_idx = bar_idx
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setPen(_outline_pen())
        self.setBrush(QBrush(QColor(_th.BG_CARD)))
        self.setZValue(0)


# ── Placed piece item ─────────────────────────────────────────────────────────

class PlacedPieceItem(QGraphicsPolygonItem):
    """One placed piece in the scene."""

    def __init__(
        self,
        local_pts: List[Tuple[float, float]],
        bar_idx: int,
        x_offset: float,
        bar_y: float,
        color: str,
        parent_scene: "NestingScene",
        pp_ref=None,
    ) -> None:
        poly = _mm_poly(local_pts, x_offset, bar_y)
        super().__init__(poly)
        self.bar_idx = bar_idx
        self.x_offset = x_offset
        self.bar_y = bar_y
        self._color = color
        self._scene_ref = parent_scene
        self.pp_ref = pp_ref
        self._selected = False
        self._multi = False
        self._highlighted = False

        self.setPen(self._base_pen())
        self.setBrush(QBrush(QColor(color)))
        self.setZValue(1)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @staticmethod
    def _base_pen() -> QPen:
        # Thin black cosmetic outline (the shared cartoon edge).
        return _outline_pen()

    def boundingRect(self):  # noqa: N802
        return self._hit_rect()

    def shape(self):  # noqa: N802
        # Enlarge the clickable area vertically (only) so thin, long profiles are
        # still easy to grab. Horizontal extent stays exact.
        path = QPainterPath()
        path.addRect(self._hit_rect())
        return path

    def _hit_rect(self):
        # Polygon bounds padded above/below: ~60% of the piece height each side,
        # min 40 / max 180 scene-units, well inside the inter-bar gap.
        r = self.polygon().boundingRect()
        pad = min(max(r.height() * 0.6, 40.0), 180.0)
        return r.adjusted(0.0, -pad, 0.0, pad)

    def set_selected(self, sel: bool, multi: bool = False) -> None:
        self._selected = sel
        self._multi = multi
        self._update_pen()

    def set_highlighted(self, hi: bool) -> None:
        self._highlighted = hi
        self._update_pen()

    def _update_pen(self) -> None:
        if self._selected:
            # Magenta for multi-selection (>1 piece), accent for a single one,
            # so a block selection reads as distinct from a lone selection.
            color = COLOR_SELECT_MULTI if getattr(self, "_multi", False) else _th.ACCENT
            self.setPen(self._cosmetic_pen(color, 2.0))
        elif self._highlighted:
            self.setPen(self._cosmetic_pen("#FFE500", 1.5))
        else:
            self.setPen(self._base_pen())

    @staticmethod
    def _cosmetic_pen(color: str, width_px: float) -> QPen:
        # Cosmetic pens keep a constant pixel width at any zoom, so the
        # selection/highlight outline stays visible even when the bar is
        # scaled down to fit the viewport.
        pen = QPen(QColor(color), width_px)
        pen.setCosmetic(True)
        return pen

    def hoverEnterEvent(self, event) -> None:
        if not self._selected:
            self.setPen(self._cosmetic_pen(_th.ACCENT, 1.5))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._update_pen()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._scene_ref.piece_pressed.emit(self)
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._scene_ref.piece_right_pressed.emit(self)
            event.accept()
        else:
            super().mousePressEvent(event)


# ── Float preview item ────────────────────────────────────────────────────────

class FloatPreviewItem(QGraphicsPolygonItem):
    """Semi-transparent floating piece that follows the cursor."""

    def __init__(self) -> None:
        super().__init__()
        self.setZValue(10)
        self.setOpacity(0.7)   # mostly opaque so the carried piece reads clearly
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setVisible(False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def update_position(
        self,
        local_pts: List[Tuple[float, float]],
        x_offset: float,
        bar_y: float,
        color: str,
        is_snap: bool,
    ) -> None:
        poly = _mm_poly(local_pts, x_offset, bar_y)
        self.setPolygon(poly)
        self.setBrush(QBrush(QColor(color)))
        # Aggressive, cosmetic outline so the piece being moved is obvious at any
        # zoom: solid ACCENT when snapped into a valid spot, dashed magenta while
        # floating free. Cosmetic → constant ~2.5px width regardless of scale.
        pen = QPen(QColor(_th.ACCENT if is_snap else COLOR_SELECT_MULTI), 2.5)
        pen.setCosmetic(True)
        if not is_snap:
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setVisible(True)


# ── Main scene ────────────────────────────────────────────────────────────────

class NestingScene(QGraphicsScene):
    """Scene for the nesting canvas.  Coordinates are in mm."""

    piece_pressed       = Signal(object)
    piece_right_pressed = Signal(object)
    background_pressed  = Signal(QPointF)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._float_item = FloatPreviewItem()
        self.addItem(self._float_item)
        self._bar_items: List[BarBackground] = []
        self._piece_items: List[PlacedPieceItem] = []
        self._label_items: list = []
        self._section_h: float = 50.0
        self._bar_labels_info: List[Tuple[str, float]] = []
        self._rubber_item: Optional[QGraphicsRectItem] = None

    def rebuild(
        self,
        bars: list,
        bar_lengths: List[float],
        section_h: float,
        selected_pp=None,
        highlighted_pps: list = (),
        show_remnants: bool = False,
        filtered_bar_offset: int = None,
        remnant_margin: float = 0.0,
    ) -> None:
        """Rebuild all bar/piece items from bars list.

        remnant_margin (mm) is the gap left between the last piece and the
        start of the green remnant block (mirrors the piece-to-piece margin;
        it does not affect the bar ends).
        """
        self._section_h = section_h
        self._bar_labels_info = []

        for item in self._bar_items + self._piece_items + self._label_items:
            self.removeItem(item)
        self._bar_items.clear()
        self._piece_items.clear()
        self._label_items.clear()

        # Precompute expected view scale factors so text with
        # ItemIgnoresTransformations can be positioned correctly.
        if bars:
            n = len(bars)
            last_y = (n - 1) * (section_h + BAR_GAP_MM) + section_h + BAR_GAP_MM
            max_len = max(bar_lengths[:n]) if bar_lengths else 6000.0
        else:
            last_y = section_h + BAR_GAP_MM
            max_len = 6000.0

        sr_w = max_len + 20
        sr_h = last_y + 60

        views = self.views()
        if views:
            vw = views[0].viewport().width() or 800
            vh = views[0].viewport().height() or 600
        else:
            vw, vh = 800, 600

        sx = max(vw / sr_w, 0.01)
        sy = max(vh / sr_h, 0.01)
        # Uniform scale that fit_scene will apply (min of x/y to preserve ratio)
        s = min(sx, sy)

        _IGT = QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
        _use_colors = app_config.get().nesting_use_cut_colors  # hoisted out of loop

        for bar_idx, bar_pieces in enumerate(bars):
            bar_len = bar_lengths[bar_idx] if bar_idx < len(bar_lengths) else 6000.0
            bar_y = bar_idx * (section_h + BAR_GAP_MM)

            # ── Bar label: placed at bar top-left, renders into the gap above
            #   when zoomed out the bar is only a few px tall; the label
            #   extends below into the canvas gap which is fine — it is
            #   always within the sceneRect and readable.
            display_idx = (filtered_bar_offset if filtered_bar_offset is not None else bar_idx) + 1
            self._bar_labels_info.append((t("bar_n", n=display_idx), bar_y))

            # ── Bar background ───────────────────────────────────────
            bg = BarBackground(bar_idx, 0, bar_y, bar_len, section_h)
            self.addItem(bg)
            self._bar_items.append(bg)

            # ── Placed pieces ────────────────────────────────────────
            for pp in bar_pieces:
                poly_pts = pp.poly_local or [
                    (0, 0), (pp.corte.largo, 0),
                    (pp.corte.largo, section_h), (0, section_h),
                ]
                fill_color = pp.color if _use_colors else _th.BORDER_LIT
                item = PlacedPieceItem(
                    poly_pts, bar_idx, pp.x_offset, bar_y,
                    fill_color, self, pp_ref=pp,
                )
                if selected_pp is not None and (
                    pp is selected_pp
                    or (isinstance(selected_pp, (set, list, tuple)) and pp in selected_pp)
                ):
                    is_multi = (isinstance(selected_pp, (set, list, tuple))
                                and len(selected_pp) > 1)
                    item.set_selected(True, multi=is_multi)
                if pp in highlighted_pps:
                    item.set_highlighted(True)

                if pp.corte.largo > 8:
                    lbl2 = self.addText(
                        f"{pp.corte.largo:.0f}", self._piece_label_font()
                    )
                    lbl2.setDefaultTextColor(QColor(_text_color_for_bg(pp.color)))
                    lbl2.setFlag(_IGT)
                    # Remove the QTextDocument's default ~4px margin so the bounding
                    # box matches the glyphs: this makes both the fit test and the
                    # centring accurate (otherwise the label reads off-centre and
                    # the fit check is too permissive, clipping the text).
                    lbl2.document().setDocumentMargin(0)
                    br = lbl2.boundingRect()
                    tw = br.width()
                    th = br.height()
                    piece_px_w = pp.corte.largo * s
                    piece_px_h = section_h * s
                    # Only show if the label fits inside the piece in BOTH
                    # dimensions (with a small pixel padding); otherwise hide it —
                    # the legend below the bar carries the same information.
                    if tw + 6 <= piece_px_w and th + 4 <= piece_px_h:
                        # IgnoresTransformations → the item renders at constant
                        # pixel size; its pos is a scene point, so offset by half
                        # the pixel size converted to scene units (÷ s) to centre.
                        cx = pp.x_offset + pp.corte.largo / 2
                        cy = bar_y + section_h / 2
                        lbl2.setPos(cx - (tw / 2) / s, cy - (th / 2) / s)
                        lbl2.setZValue(2)
                        self._label_items.append(lbl2)
                    else:
                        self.removeItem(lbl2)

                self.addItem(item)
                self._piece_items.append(item)

            # ── Remnant area ─────────────────────────────────────────
            if show_remnants and bar_pieces:
                used = max(pp.x_offset + pp.corte.largo for pp in bar_pieces)
                start = used + max(remnant_margin, 0.0)
                retal_w = bar_len - start
                if retal_w > 0.5:
                    ritem = RemantItem(bar_y, section_h, start, retal_w)
                    self.addItem(ritem)
                    self._bar_items.append(ritem)

            # ── Piece legend below bar ───────────────────────────────
            # One [swatch][desc + length] entry per distinct cut on the bar,
            # laid out left→right and wrapping to a new row when the next entry
            # would overflow the bar width. Sizes are in PIXELS (swatch 10px,
            # gaps 6/20px) converted to scene units via the current scale `s`,
            # because legend items use ItemIgnoresTransformations (constant size).
            if bar_pieces:
                seen: dict = {}
                for pp in bar_pieces:
                    key = (pp.corte.descripcion, pp.corte.largo)
                    if key not in seen:
                        seen[key] = pp.color

                legend_y = bar_y + section_h + 80   # 80 scene-units below the bar
                legend_x = 4.0
                swatch_px = 10        # legend colour square (px)
                gap_px = 6            # swatch→text gap (px)
                entry_gap_px = 20     # gap between entries (px)
                row_h_px = swatch_px + 6   # row pitch when wrapping (px)
                max_legend_x = bar_len     # wrap once an entry passes the bar end

                from PySide6.QtGui import QFontMetricsF
                _legend_fm = QFontMetricsF(self._legend_font())
                for (desc, largo), color in seen.items():
                    txt = (
                        f"{desc} {largo:.0f}mm" if desc else f"{largo:.0f}mm"
                    )
                    # Measure text width directly with font metrics instead of
                    # creating + inserting + removing a throwaway QGraphicsTextItem
                    # per legend entry on every scene rebuild.
                    text_w = _legend_fm.horizontalAdvance(f" {txt}")
                    entry_w = (swatch_px + gap_px + text_w + entry_gap_px) / s

                    if legend_x + entry_w > max_legend_x and legend_x > 4.0:
                        legend_x = 4.0
                        legend_y += row_h_px / s

                    swatch = QGraphicsRectItem(0, 0, swatch_px, swatch_px)
                    swatch.setPos(legend_x, legend_y)
                    swatch.setBrush(QBrush(QColor(color)))
                    swatch.setPen(QPen(Qt.PenStyle.NoPen))
                    swatch.setFlag(_IGT)
                    swatch.setZValue(1)
                    self.addItem(swatch)
                    self._label_items.append(swatch)

                    lbl3 = self.addText(f" {txt}", self._legend_font())
                    lbl3.setDefaultTextColor(QColor(_th.TEXT_SEC))
                    lbl3.setFlag(_IGT)
                    text_x = legend_x + (swatch_px + gap_px) / s
                    lbl3.setPos(text_x, legend_y - 2)
                    lbl3.setZValue(1)
                    self._label_items.append(lbl3)

                    tw = lbl3.boundingRect().width()
                    legend_x += (swatch_px + gap_px + tw + entry_gap_px) / s

        # Ensure float preview is always on top
        if self._float_item.scene() is None:
            self.addItem(self._float_item)
        self._float_item.setZValue(10)

        self.setSceneRect(-10, -40, max_len + 20, last_y + 60)

    def set_float_preview(
        self,
        local_pts: Optional[List[Tuple[float, float]]],
        x_offset: float,
        bar_y: float,
        color: str,
        is_snap: bool,
    ) -> None:
        if local_pts is None:
            self._float_item.setVisible(False)
            return
        self._float_item.update_position(local_pts, x_offset, bar_y, color, is_snap)

    def hide_float_preview(self) -> None:
        self._float_item.setVisible(False)

    # ── Rubber-band selection ──────────────────────────────────────────────
    def show_rubber_band(self, rect: QRectF) -> None:
        """Draw/update the marquee selection rectangle (scene coords)."""
        if self._rubber_item is None:
            self._rubber_item = QGraphicsRectItem()
            pen = QPen(QColor(COLOR_SELECT_MULTI), 0.0)
            pen.setCosmetic(True)  # constant 1px width regardless of zoom
            pen.setStyle(Qt.PenStyle.DashLine)
            self._rubber_item.setPen(pen)
            fill = QColor(COLOR_SELECT_MULTI)
            fill.setAlpha(40)
            self._rubber_item.setBrush(QBrush(fill))
            self._rubber_item.setZValue(20)
            self.addItem(self._rubber_item)
        self._rubber_item.setRect(rect.normalized())
        self._rubber_item.setVisible(True)

    def hide_rubber_band(self) -> None:
        if self._rubber_item is not None:
            self._rubber_item.setVisible(False)

    def pieces_in_rect(self, rect: QRectF) -> list:
        """Return pp_ref objects whose piece item intersects the given rect."""
        r = rect.normalized()
        return [it.pp_ref for it in self._piece_items
                if it.pp_ref is not None and it.sceneBoundingRect().intersects(r)]

    def bar_y_for(self, bar_idx: int) -> float:
        return bar_idx * (self._section_h + BAR_GAP_MM)

    def bar_idx_at_y(self, scene_y: float) -> Optional[int]:
        """Return bar index at a given scene Y, or None if in a gap."""
        sh = self._section_h
        gap = BAR_GAP_MM
        idx = int(scene_y / (sh + gap))
        y_top = idx * (sh + gap)
        if y_top <= scene_y <= y_top + sh:
            return idx
        return None

    def mousePressEvent(self, event) -> None:
        _tf = self.views()[0].transform() if self.views() else QTransform()
        item = self.itemAt(event.scenePos(), _tf)
        if isinstance(item, PlacedPieceItem):
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.background_pressed.emit(event.scenePos())
        super().mousePressEvent(event)

    # ── Font factories ──────────────────────────────────────────────────────
    # Point sizes are deliberately fixed per role so the scene's text hierarchy
    # stays consistent at any zoom (the items use cosmetic/ignore-transform text
    # where needed). Mono fonts (DejaVu Sans Mono) are used for numeric/measure
    # labels so digits align; IBM Plex Sans for prose labels.

    @staticmethod
    def _bar_label_font():
        """Bold 11pt IBM Plex Sans — the "Bar N" heading above each bar."""
        from PySide6.QtGui import QFont
        f = QFont("IBM Plex Sans", 11)
        f.setBold(True)
        return f

    @staticmethod
    def _piece_label_font():
        """9pt DejaVu Sans Mono — the measurement label centred inside a piece."""
        from PySide6.QtGui import QFont
        return QFont("DejaVu Sans Mono", 9)

    @staticmethod
    def _legend_font():
        """9pt IBM Plex Sans — legend entries (swatch + description) below a bar."""
        from PySide6.QtGui import QFont
        return QFont("IBM Plex Sans", 9)

    @staticmethod
    def _tiny_font():
        """6pt DejaVu Sans Mono — smallest numeric annotations (e.g. tight pieces)."""
        from PySide6.QtGui import QFont
        return QFont("DejaVu Sans Mono", 6)

    @staticmethod
    def _small_font():
        """7pt IBM Plex Sans — secondary captions."""
        from PySide6.QtGui import QFont
        return QFont("IBM Plex Sans", 7)
