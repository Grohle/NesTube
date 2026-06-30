"""
nestify/ui_qt/widgets/profile_tile.py
72×90 tile showing a profile shape (vector or image) with a name label.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

import nestify.ui_qt.theme_qt as _th

_TILE_W = 72
_TILE_H = 90
_DRAW_H = 60   # upper area for shape
_LABEL_H = 30  # lower area for name


class ProfileTile(QWidget):
    """Profile selection tile — click to select."""

    clicked = Signal(str)  # emits profile_key

    def __init__(
        self,
        profile_key: str,
        profile_type: str,
        display_name: str,
        image_path: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._key = profile_key
        self._type = profile_type
        self._name = display_name
        self._image_path = image_path
        self._selected = False
        self._pixmap: QPixmap | None = None

        self.setFixedSize(_TILE_W, _TILE_H)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if image_path:
            px = QPixmap(image_path)
            if not px.isNull():
                self._pixmap = px.scaled(
                    _TILE_W - 8, _DRAW_H - 8,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, v: bool) -> None:
        if self._selected != v:
            self._selected = v
            self.update()

    def profile_key(self) -> str:
        return self._key

    # ── Events ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._key)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        # Tile layout (72×90): BG_CARD fill, shape/image in the top 60px, name in
        # the bottom 30px, and a rounded border (ACCENT 2px if selected, else
        # BORDER 1px). All colours read from _th.* so it follows the theme.
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background fills the whole tile.
        bg = QColor(_th.BG_CARD)
        p.fillRect(0, 0, _TILE_W, _TILE_H, bg)

        # Upper area (0.._DRAW_H): a thumbnail pixmap (centred) if present, else
        # the vector profile shape painted by _draw_profile_shape.
        # Always show the PNG when one has been generated — the user's own thumbnail
        # takes precedence over any vector fallback regardless of the current theme.
        if self._pixmap:
            ox = (_TILE_W - self._pixmap.width()) // 2
            oy = (_DRAW_H - self._pixmap.height()) // 2
            p.drawPixmap(ox, oy, self._pixmap)
        else:
            self._draw_profile_shape(p)

        # Name label: 8px IBM Plex Sans, centred in the lower _LABEL_H band.
        p.setPen(QPen(QColor(_th.TEXT_PRI)))
        f = QFont("IBM Plex Sans", 8)
        p.setFont(f)
        p.drawText(
            QRectF(2, _DRAW_H, _TILE_W - 4, _LABEL_H),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            self._name,
        )

        # Border: ACCENT 2px when selected, BORDER 1px otherwise; 4px corner radius.
        if self._selected:
            pen = QPen(QColor(_th.ACCENT), 2)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(1, 1, _TILE_W - 2, _TILE_H - 2, 4, 4)
        else:
            pen = QPen(QColor(_th.BORDER), 1)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(0, 0, _TILE_W, _TILE_H, 4, 4)

        p.end()

    def _draw_profile_shape(self, p: QPainter) -> None:
        """Draw a filled symbolic shape for the profile type, matching the actual cross-section.

        Everything is laid out inside the tile's drawing band: an 8px pad gives a
        margin, (x0,y0)-(x1,y1) is the usable box, (iw,ih) its size and (cx,cy)
        its centre. Shapes are translucent ACCENT fills (alpha 200) outlined in a
        1.5px ACCENT pen; hollow sections are carved out by overpainting with the
        BG_CARD colour. All colours read from live _th so the tile follows theme.
        """
        pad = 8
        x0, y0 = float(pad), float(pad)
        x1, y1 = float(_TILE_W - pad), float(_DRAW_H - pad)
        iw, ih = x1 - x0, y1 - y0
        cx, cy = _TILE_W / 2.0, _DRAW_H / 2.0

        fill = QColor(_th.ACCENT)
        fill.setAlpha(200)
        bg = QColor(_th.BG_CARD)
        pen = QPen(QColor(_th.ACCENT), 1.5)
        p.setPen(pen)

        typ = self._type.upper().strip()

        if "REDONDO" in typ or "ROUND" in typ or "CIRC" in typ or "PIPE" in typ or "TUB" in typ:
            # Round/pipe: outer disc of radius r (half the smaller dimension),
            # then a concentric BG_CARD disc at 0.55·r carves the bore (hollow).
            r = min(iw, ih) / 2.0
            p.setBrush(QBrush(fill))
            p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
            ri = r * 0.55
            p.setBrush(QBrush(bg))
            p.drawEllipse(QRectF(cx - ri, cy - ri, 2 * ri, 2 * ri))

        elif "RECTANGULAR" in typ or "RECT" in typ or "CUAD" in typ or "SQUARE" in typ:
            # Rectangular tube: full box, then an inner BG_CARD box inset by the
            # wall thickness (0.2 of the smaller side) to show the hollow.
            p.setBrush(QBrush(fill))
            p.drawRect(QRectF(x0, y0, iw, ih))
            wall = min(iw, ih) * 0.2
            p.setBrush(QBrush(bg))
            p.drawRect(QRectF(x0 + wall, y0 + wall, iw - 2 * wall, ih - 2 * wall))

        elif typ in ("L", "ANGLE", "ANG") or "L_" in typ:
            # L/angle: an L-polygon whose two legs are 0.33 of width/height thick.
            pts = QPolygonF([
                QPointF(x0, y0), QPointF(x0 + iw, y0),
                QPointF(x0 + iw, y0 + ih * 0.33), QPointF(x0 + iw * 0.33, y0 + ih * 0.33),
                QPointF(x0 + iw * 0.33, y0 + ih), QPointF(x0, y0 + ih),
            ])
            p.setBrush(QBrush(fill))
            p.drawPolygon(pts)

        elif typ in ("U", "CHANNEL", "CANAL") or "U_" in typ:
            # U/channel: outer box with the centre top notched out — side walls at
            # 0.28 and 0.72 of the width, notch floor at 0.3 of the height.
            pts = QPolygonF([
                QPointF(x0, y0 + ih), QPointF(x0, y0),
                QPointF(x0 + iw, y0), QPointF(x0 + iw, y0 + ih),
                QPointF(x0 + iw * 0.72, y0 + ih), QPointF(x0 + iw * 0.72, y0 + ih * 0.3),
                QPointF(x0 + iw * 0.28, y0 + ih * 0.3), QPointF(x0 + iw * 0.28, y0 + ih),
            ])
            p.setBrush(QBrush(fill))
            p.drawPolygon(pts)

        elif typ in ("H", "I", "VIGA", "BEAM") or "H_" in typ or "I_" in typ:
            # H/I-beam: top + bottom flanges (each 0.22 of height) joined by a
            # central web 0.28 of the width wide.
            flange = ih * 0.22
            web_w = iw * 0.28
            p.setBrush(QBrush(fill))
            p.drawRect(QRectF(x0, y0, iw, flange))
            p.drawRect(QRectF(cx - web_w / 2, y0 + flange, web_w, ih - 2 * flange))
            p.drawRect(QRectF(x0, y0 + ih - flange, iw, flange))

        elif "FLAT" in typ or "PLET" in typ:
            # Flat bar: a thin horizontal strip 0.4 of the height, vertically centred.
            p.setBrush(QBrush(fill))
            p.drawRect(QRectF(x0, cy - ih * 0.2, iw, ih * 0.4))

        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            pen2 = QPen(QColor(_th.ACCENT), 1.0, Qt.PenStyle.DashLine)
            p.setPen(pen2)
            p.drawRect(QRectF(x0, y0, iw, ih))
