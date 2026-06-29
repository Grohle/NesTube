"""
nestify/ui_qt/dialogs/profile_creator.py
Interactive profile shape creator — CAD-like drawing tools with snap system,
ortho mode, multi-select, window selection, trim, extend, and arc tools.
Ported from tkinter Canvas to QWidget + QPainter.
"""
from __future__ import annotations

import math
import tempfile
from typing import Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QImage, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent,
)
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from nestify.i18n import t
from nestify import app_config, units
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.icons import themed_icon

SNAP_RADIUS = 10
CLOSE_RADIUS = 10


class ProfileShape:
    """A shape element in the profile cross-section."""

    def __init__(self, shape_type: str, points: List[Tuple[float, float]],
                 is_void: bool = False, dim_name: str = "",
                 closed: bool = False, thickness: float = 0.0):
        self.shape_type = shape_type
        self.points = points
        self.is_void = is_void
        self.dim_name = dim_name
        self.closed = closed
        self.thickness = thickness

    def bounds(self) -> Tuple[float, float, float, float]:
        if self.shape_type == "circle":
            cx, cy = self.points[0]
            r = self._radius()
            return cx - r, cy - r, cx + r, cy + r
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def area(self) -> float:
        x0, y0, x1, y1 = self.bounds()
        return (x1 - x0) * (y1 - y0)

    def _radius(self) -> float:
        if self.shape_type == "circle" and len(self.points) >= 2:
            cx, cy = self.points[0]
            rx, ry = self.points[1]
            return math.hypot(rx - cx, ry - cy)
        return 0.0

    def vertices(self) -> List[Tuple[float, float]]:
        if self.shape_type == "rect" and len(self.points) == 2:
            (x0, y0), (x1, y1) = self.points
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        elif self.shape_type == "circle":
            cx, cy = self.points[0]
            r = self._radius()
            return [(cx, cy), (cx + r, cy), (cx - r, cy),
                    (cx, cy + r), (cx, cy - r)]
        return list(self.points)

    def midpoints(self) -> List[Tuple[float, float]]:
        verts = self.vertices()
        if self.shape_type == "circle":
            return []
        mids = []
        n = len(verts)
        if n < 2:
            return mids
        segments = n if (self.closed or self.shape_type == "rect") else n - 1
        for i in range(segments):
            p1 = verts[i]
            p2 = verts[(i + 1) % n]
            mids.append(((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))
        return mids

    def segments(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        verts = self.vertices()
        if self.shape_type == "circle":
            return []
        segs = []
        n = len(verts)
        if n < 2:
            return segs
        loop = n if (self.closed or self.shape_type == "rect") else n - 1
        for i in range(loop):
            segs.append((verts[i], verts[(i + 1) % n]))
        return segs

    def hit_test(self, x: float, y: float, tolerance: float = 5.0) -> bool:
        if self.shape_type == "rect":
            (x0, y0), (x1, y1) = self.points
            lx, rx = min(x0, x1), max(x0, x1)
            ly, ry = min(y0, y1), max(y0, y1)
            return (lx - tolerance <= x <= rx + tolerance and
                    ly - tolerance <= y <= ry + tolerance)
        elif self.shape_type == "circle":
            cx, cy = self.points[0]
            r = self._radius()
            return math.hypot(x - cx, y - cy) <= r + tolerance
        elif self.shape_type in ("polygon", "line"):
            for seg in self.segments():
                if _point_to_segment_dist(x, y, seg[0], seg[1]) <= tolerance:
                    return True
            if self.closed and len(self.points) >= 3:
                return _point_in_polygon(x, y, self.points)
        return False

    def fully_inside_rect(self, rx0, ry0, rx1, ry1) -> bool:
        lx, rx = min(rx0, rx1), max(rx0, rx1)
        ly, ry = min(ry0, ry1), max(ry0, ry1)
        for vx, vy in self.vertices():
            if not (lx <= vx <= rx and ly <= vy <= ry):
                return False
        return True

    def crosses_rect(self, rx0, ry0, rx1, ry1) -> bool:
        lx, rx = min(rx0, rx1), max(rx0, rx1)
        ly, ry = min(ry0, ry1), max(ry0, ry1)
        for vx, vy in self.vertices():
            if lx <= vx <= rx and ly <= vy <= ry:
                return True
        if self.shape_type == "circle":
            cx, cy = self.points[0]
            r = self._radius()
            closest_x = max(lx, min(cx, rx))
            closest_y = max(ly, min(cy, ry))
            return math.hypot(closest_x - cx, closest_y - cy) <= r
        rect_segs = [((lx, ly), (rx, ly)), ((rx, ly), (rx, ry)),
                     ((rx, ry), (lx, ry)), ((lx, ry), (lx, ly))]
        for seg in self.segments():
            for rseg in rect_segs:
                if _segments_intersect(seg[0], seg[1], rseg[0], rseg[1]) is not None:
                    return True
        if self.closed and len(self.points) >= 3:
            mid_x = (lx + rx) / 2
            mid_y = (ly + ry) / 2
            if _point_in_polygon(mid_x, mid_y, self.vertices()):
                return True
        return False

    def to_dict(self) -> dict:
        d = {"type": self.shape_type, "points": self.points,
             "is_void": self.is_void, "dim_name": self.dim_name, "closed": self.closed}
        if self.thickness:
            d["thickness"] = self.thickness
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ProfileShape":
        return cls(shape_type=d.get("type", "rect"), points=d.get("points", []),
                   is_void=d.get("is_void", False), dim_name=d.get("dim_name", ""),
                   closed=d.get("closed", False), thickness=d.get("thickness", 0.0))


def _point_to_segment_dist(px, py, a, b) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)
    t_val = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t_val * dx), py - (ay + t_val * dy))


def _point_in_polygon(px, py, polygon) -> bool:
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py) and
                px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _segments_intersect(p1, p2, p3, p4):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None
    t_val = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u_val = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    if 0 <= t_val <= 1 and 0 <= u_val <= 1:
        return (x1 + t_val * (x2 - x1), y1 + t_val * (y2 - y1))
    return None


def _line_intersect_ray(p1, p2, ray_origin, ray_dir):
    x1, y1 = ray_origin; dx, dy = ray_dir
    x3, y3 = p1; x4, y4 = p2
    sx, sy = x4 - x3, y4 - y3
    denom = dx * sy - dy * sx
    if abs(denom) < 1e-10:
        return None
    qx, qy = x3 - x1, y3 - y1
    t_val = (qx * sy - qy * sx) / denom
    u_val = (qx * dy - qy * dx) / denom
    if t_val > 1e-6 and 0 <= u_val <= 1:
        return (x1 + t_val * dx, y1 + t_val * dy)
    return None


def _segment_intersection(a1, a2, b1, b2):
    """Intersection point of segments A(a1→a2) and B(b1→b2), or None if they
    don't cross within both segments (parallel/collinear → None)."""
    (x1, y1), (x2, y2) = a1, a2
    (x3, y3), (x4, y4) = b1, b2
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def _perpendicular_foot(rx, ry, ax, ay, bx, by):
    """Foot of the perpendicular from (rx,ry) onto segment AB, or None if it
    falls outside the segment."""
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom <= 1e-9:
        return None
    tparam = ((rx - ax) * dx + (ry - ay) * dy) / denom
    if tparam < 0.0 or tparam > 1.0:
        return None
    return ax + tparam * dx, ay + tparam * dy


def _project_point_on_segment(px, py, ax, ay, bx, by):
    """Closest point to (px,py) on segment AB (clamped to the segment ends)."""
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom <= 1e-9:
        return ax, ay
    tparam = ((px - ax) * dx + (py - ay) * dy) / denom
    tparam = max(0.0, min(1.0, tparam))
    return ax + tparam * dx, ay + tparam * dy


def _generate_arc_points(start, end, mid, num_segments=20):
    x1, y1 = start; x2, y2 = end; x3, y3 = mid
    ax = x1 - x3; ay = y1 - y3; bx = x2 - x3; by = y2 - y3
    D = 2 * (ax * by - ay * bx)
    if abs(D) < 1e-10:
        return [start, mid, end]
    ux = (by * (ax * ax + ay * ay) - ay * (bx * bx + by * by)) / D
    uy = (ax * (bx * bx + by * by) - bx * (ax * ax + ay * ay)) / D
    cx = x3 + ux; cy = y3 + uy
    r = math.hypot(x1 - cx, y1 - cy)
    a1 = math.atan2(y1 - cy, x1 - cx)
    a2 = math.atan2(y2 - cy, x2 - cx)
    am = math.atan2(y3 - cy, x3 - cx)
    def _n(a):
        while a < 0: a += 2 * math.pi
        while a >= 2 * math.pi: a -= 2 * math.pi
        return a
    a1 = _n(a1); a2 = _n(a2); am = _n(am)
    ss, se = a1, a2
    if a1 <= a2:
        if not (a1 <= am <= a2):
            ss, se = a2, a1 + 2 * math.pi
    else:
        if a2 <= am <= a1:
            ss, se = a1, a2 + 2 * math.pi
        else:
            ss, se = a1, a2
    mc = _n((ss + se) / 2)
    if abs(mc - am) > 0.1:
        ss, se = se, ss + 2 * math.pi
    pts = []
    for i in range(num_segments + 1):
        f = i / num_segments
        a = ss + f * (se - ss)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _generate_arc_cse_points(center, start, end, num_segments=20):
    cx, cy = center
    r = math.hypot(start[0] - cx, start[1] - cy)
    if r < 1e-6:
        return [start, end]
    a_s = math.atan2(start[1] - cy, start[0] - cx)
    a_e = math.atan2(end[1] - cy, end[0] - cx)
    sweep = a_e - a_s
    if sweep <= 0:
        sweep += 2 * math.pi
    pts = []
    for i in range(num_segments + 1):
        f = i / num_segments
        a = a_s + f * sweep
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


class _DrawCanvas(QWidget):
    """Custom widget that draws shapes with QPainter."""

    GRID_SIZE = 20   # grid spacing in WORLD units (scaled by _view_scale on screen)

    def __init__(self, creator: "ProfileCreator", parent=None) -> None:
        super().__init__(parent)
        self._creator = creator
        self.setMinimumSize(400, 400)   # min canvas size
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)     # hover updates (snap indicator, rubber-band)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event) -> None:
        # Paint order: white drawing surface → grid → shapes (delegated to the
        # creator). This is a CAD-style white canvas (fixed colours, not themed).
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#FFFFFF"))
        self._draw_grid(p)
        self._creator._paint_shapes(p)
        p.end()

    def _draw_grid(self, p: QPainter) -> None:
        # Light-grey 1px grid. Spacing on screen = GRID_SIZE × current zoom, so
        # the grid densifies/loosens as you zoom.
        gs = self.GRID_SIZE * self._creator._view_scale
        pen = QPen(QColor("#E8E8EC"), 1)
        p.setPen(pen)
        w, h = self.width(), self.height()
        # Start the grid at the pan offset (mod spacing) so lines stay anchored to
        # world coordinates as the view pans during cursor-zoom.
        ox, oy = self._creator._view_offset
        x = ox % gs if gs > 0 else 0.0
        while x <= w:
            p.drawLine(QPointF(x, 0), QPointF(x, h))
            x += gs
        y = oy % gs if gs > 0 else 0.0
        while y <= h:
            p.drawLine(QPointF(0, y), QPointF(w, y))
            y += gs

    # Mouse handlers are routed through _with_undo so any operation that ends
    # up mutating the drawing (create/erase/trim/extend/finish-poly…) records
    # an undo checkpoint automatically; no-op clicks push nothing.
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._creator._with_undo(self._creator._on_press, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._creator._on_motion(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._creator._with_undo(self._creator._on_release, event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self._creator._with_undo(self._creator._on_double_click, event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self._creator._on_wheel(event)


class ProfileCreator(QDialog):
    """Interactive profile cross-section creator with CAD-like tools."""

    def __init__(self, parent, on_save=None, initial_shapes=None,
                 initial_meta=None, initial_manual_sides=None) -> None:
        super().__init__(parent)
        self._initial_meta = dict(initial_meta or {})
        self._initial_manual_sides = list(initial_manual_sides or [])
        # Always titled as the drawing module (never "New …") per the product
        # naming; the edit/add distinction is implicit from the loaded shapes.
        self.setWindowTitle(t("profile_creator_tools"))
        # Size to the available screen so the window never opens clipped/off-screen
        # (the old fixed 1060x700 + min 900x600 overflowed smaller displays, so the
        # window manager cut it off and the user had to shrink+resize it by hand).
        # Use up to 90% of the available work area, capped at the comfortable
        # design size, and floor the minimum so it still fits a small laptop.
        try:
            from PySide6.QtGui import QGuiApplication
            screen = self.screen() or QGuiApplication.primaryScreen()
            avail = screen.availableGeometry()
            w = min(1060, int(avail.width() * 0.9))
            h = min(700, int(avail.height() * 0.9))
            self.setMinimumSize(min(900, w), min(600, h))
            self.resize(max(w, min(900, w)), max(h, min(600, h)))
        except Exception:
            self.resize(1060, 700)
            self.setMinimumSize(900, 600)
        self.setModal(True)
        self._imported_image_path: str = ""

        self._on_save = on_save
        self._shapes: List[ProfileShape] = [
            ProfileShape.from_dict(s) if isinstance(s, dict) else s
            for s in (initial_shapes or [])
        ]
        # Catalogue profiles carry their geometry parametrically (meta +
        # geometry_type) with drawing_shapes:[] → a blank canvas. Seed editable
        # polygons from section_contours so they can be fully edited (§21.5).
        if not self._shapes and self._initial_meta.get("geometry_type"):
            self._shapes = self._shapes_from_geometry(self._initial_meta)
        self._current_tool = "rect"
        self._drawing = False
        self._start_pos: Optional[Tuple[float, float]] = None
        self._drag_pos: Optional[Tuple[float, float]] = None
        self._selected_shapes: Set[int] = set()
        self._ortho_mode = False
        self._poly_points: List[Tuple[float, float]] = []
        self._snap_pos: Optional[Tuple[float, float]] = None
        self._snap_type: Optional[str] = None
        self._sel_drag_start: Optional[Tuple[float, float]] = None
        self._sel_drag_end: Optional[Tuple[float, float]] = None
        self._trim_drag_start: Optional[Tuple[float, float]] = None
        self._trim_drag_end: Optional[Tuple[float, float]] = None
        self._arc_points: List[Tuple[float, float]] = []
        self._view_scale: float = 1.0
        self._view_offset: Tuple[float, float] = (0.0, 0.0)  # pan (px) for cursor-zoom
        self._mouse_pos: Optional[Tuple[float, float]] = None
        # Undo/redo: stacks of serialized shape snapshots (max 50). A snapshot
        # is pushed whenever an operation actually changes the drawing.
        self._undo_stack: List[list] = []
        self._redo_stack: List[list] = []
        # Dynamic numeric input (AutoCAD-style): while drawing a polyline, typed
        # digits set the exact segment length and/or angle; Tab switches the
        # active field (length ↔ angle); Enter commits in that direction.
        self._dim_input: str = ""        # length field
        self._dim_angle: str = ""        # angle field (deg, CCW from +x, screen-up)
        self._dim_field: str = "len"     # which field digits go to

        self._build()
        self._set_tool("line")
        self._prefill_data()

    @staticmethod
    def _shapes_from_geometry(meta: dict) -> List["ProfileShape"]:
        """Build editable ProfileShapes from a parametric catalogue section so a
        catalogue profile opens as real geometry rather than a blank canvas."""
        try:
            from nestify.profile_geometry import section_contours
            outer, holes = section_contours(
                meta.get("geometry_type", ""),
                float(meta.get("h", 0) or 0), float(meta.get("b", 0) or 0),
                float(meta.get("tw", 0) or 0), float(meta.get("tf", 0) or 0),
                macizo=bool(meta.get("macizo", False)),
            )
        except Exception:
            return []
        shapes: List[ProfileShape] = []
        if outer:
            shapes.append(ProfileShape("polygon", [tuple(p) for p in outer], closed=True))
        for hole in holes or []:
            shapes.append(ProfileShape("polygon", [tuple(p) for p in hole],
                                       is_void=True, closed=True))
        return shapes

    def _prefill_data(self) -> None:
        """Populate the data panel from initial_meta / initial_manual_sides (edit)."""
        for key, edit in getattr(self, "_meta", {}).items():
            if self._initial_meta.get(key):
                edit.setText(str(self._initial_meta[key]))
        for m in self._initial_manual_sides:
            if isinstance(m, dict) and m.get("name"):
                self._manual_sides.append({
                    "name": m.get("name", ""),
                    "length": float(m.get("length", 0) or 0),
                    "thickness": float(m.get("thickness", 0) or 0),
                })
        if self._initial_manual_sides or self._shapes:
            self._refresh_sides_list()

    def _build(self) -> None:
        # Three-pane layout, all visible on open:
        #   LEFT  = narrow icon tool bar (52px, glyph buttons + hover tooltips)
        #   CENTER= white drawing canvas + a one-line hint
        #   RIGHT = data panel (profile image, generate/import, dims, file ops)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_tool_icons(root)

        center = QVBoxLayout()
        center.setContentsMargins(8, 8, 8, 8)
        self._canvas = _DrawCanvas(self)
        center.addWidget(self._canvas, 1)
        self._info_lbl = QLabel(t("profile_creator_hint"))
        self._info_lbl.setStyleSheet(f"color: {_th.TEXT_SEC}; background: {_th.BG_MID}; padding: 4px;")
        center.addWidget(self._info_lbl)
        root.addLayout(center, 1)

        self._build_data_panel(root)

    # ── Left icon tool bar ────────────────────────────────────────────────────
    def _icon_button(self, glyph: str, tooltip: str,
                     svg_name: str = "") -> QPushButton:
        """A 40×34 glyph-only tool button; the name shows as a hover tooltip."""
        b = QPushButton()
        b.setFixedSize(40, 34)
        b.setToolTip(tooltip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if svg_name:
            b.setIcon(themed_icon(svg_name, _th.TEXT_PRI, 20))
            b.setIconSize(QSize(20, 20))
        else:
            b.setText(glyph)
            b.setStyleSheet("font-size:16px;")
        return b

    def _build_tool_icons(self, root: QHBoxLayout) -> None:
        bar = QFrame()
        bar.setFixedWidth(52)
        bar.setStyleSheet(f"QFrame {{ background: {_th.BG_CARD}; border-right:1px solid {_th.BORDER}; }}")
        col = QVBoxLayout(bar)
        col.setContentsMargins(6, 8, 6, 8)
        col.setSpacing(4)

        def _sep():
            s = QFrame(); s.setFixedHeight(1)
            s.setStyleSheet(f"background: {_th.BORDER};")
            col.addWidget(s)

        self._tool_buttons: Dict[str, QPushButton] = {}
        # All tool buttons are themed SVG glyphs with a hover tooltip (no text
        # symbols), consistent with the rest of the app.
        draw_tools = [
            ("line", t("tool_line"), "tool-line"),
            ("polygon", t("tool_polygon"), "tool-polygon"),
            ("rect", t("tool_rectangle"), "tool-rect"),
            ("circle", t("tool_circle"), "tool-circle"),
            ("arc_3pt", t("tool_arc_3pt"), "tool-arc3"),
            ("arc_cse", t("tool_arc_cse"), "tool-arccse"),
        ]
        for tool_id, name, svg in draw_tools:
            b = self._icon_button("", name, svg)
            b.clicked.connect(lambda checked=False, tid=tool_id: self._set_tool(tid))
            col.addWidget(b)
            self._tool_buttons[tool_id] = b

        ae = self._icon_button("", t("tool_arc_exact"), "tool-arcexact")
        ae.clicked.connect(lambda: self._with_undo(self._open_arc_exact_dialog))
        col.addWidget(ae)

        _sep()
        edit_tools = [
            ("select", t("tool_select"), "cursor"),
            ("eraser", t("tool_eraser"), "x"),
            ("void", t("tool_void"), "tool-void"),
            ("trim", t("tool_trim"), "tool-trim"),
            ("extend", t("tool_extend"), "tool-extend"),
        ]
        for tool_id, name, svg in edit_tools:
            b = self._icon_button("", name, svg)
            b.clicked.connect(lambda checked=False, tid=tool_id: self._set_tool(tid))
            col.addWidget(b)
            self._tool_buttons[tool_id] = b

        _sep()
        self._ortho_btn = self._icon_button("", t("ortho_mode"), "tool-ortho")
        self._ortho_btn.clicked.connect(self._toggle_ortho)
        col.addWidget(self._ortho_btn)

        # Undo / redo (also on Ctrl+Z / Ctrl+Y).
        _sep()
        undo_btn = self._icon_button("", t("nesting_undo_tip"), "undo2")
        undo_btn.clicked.connect(self._undo)
        col.addWidget(undo_btn)
        redo_btn = self._icon_button("", t("nesting_redo_tip"), "redo")
        redo_btn.clicked.connect(self._redo)
        col.addWidget(redo_btn)

        col.addStretch()
        root.addWidget(bar)

    # ── Right data panel ──────────────────────────────────────────────────────
    def _build_data_panel(self, root: QHBoxLayout) -> None:
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setFixedWidth(252)
        panel.setStyleSheet(f"QScrollArea {{ background: {_th.BG_CARD}; border-left:1px solid {_th.BORDER}; }}")
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Profile image preview at the very top.
        self._profile_img = QLabel(t("profile_no_image"))
        self._profile_img.setFixedHeight(120)
        self._profile_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Preview backdrop is BG_MID (theme-aware), not a hardcoded white box:
        # a bright white rectangle clashed in dark mode. BG_MID reads as a
        # recessed inset against the BG_CARD panel in both themes, and the
        # thumbnail (light-grey fill + dark outline) stays legible on it.
        self._profile_img.setStyleSheet(
            f"background:{_th.BG_MID}; border:1px solid {_th.BORDER}; border-radius:4px; color:{_th.TEXT_SEC};"
        )
        layout.addWidget(self._profile_img)

        gen_btn = QPushButton(t("profile_generate_from_drawing"))
        gen_btn.setProperty("variant", "accent")
        gen_btn.clicked.connect(self._generate_preview)
        layout.addWidget(gen_btn)

        img_btn = QPushButton(t("profile_import_image"))
        img_btn.clicked.connect(self._import_image)
        layout.addWidget(img_btn)

        self._build_data_fields(layout)

        layout.addStretch()
        panel.setWidget(inner)
        root.addWidget(panel)

    def _build_data_fields(self, layout: QVBoxLayout) -> None:
        # (kept compatible with the old toolbar widget names used elsewhere)
        def _sep():
            s = QFrame(); s.setFixedHeight(1)
            s.setStyleSheet(f"background: {_th.BORDER};")
            layout.addWidget(s)

        _sep()
        dim_lbl = QLabel(t("profile_creator_dims"))
        dim_lbl.setStyleSheet(f"color: {_th.ACCENT}; font-weight:bold; font-size:10px;")
        layout.addWidget(dim_lbl)

        self._dim_name = QLineEdit()
        self._dim_name.setPlaceholderText(t("field_name"))
        layout.addWidget(self._dim_name)
        assign_btn = QPushButton(t("profile_creator_assign"))
        assign_btn.clicked.connect(lambda: self._with_undo(self._assign_dim))
        layout.addWidget(assign_btn)

        thick_row = QHBoxLayout()
        self._thickness_entry = QLineEdit()
        self._thickness_entry.setPlaceholderText(t("thickness") + " 0.0")
        thick_row.addWidget(self._thickness_entry, 1)
        thick_btn = QPushButton()
        thick_btn.setIcon(themed_icon("return-left", _th.TEXT_PRI, 16))
        thick_btn.setIconSize(QSize(16, 16))
        thick_btn.setFixedWidth(34)
        thick_btn.setToolTip(t("profile_assign_thickness"))
        thick_btn.clicked.connect(lambda: self._with_undo(self._assign_thickness))
        thick_row.addWidget(thick_btn)
        layout.addLayout(thick_row)

        self._sel_info = QLabel(t("selection_info_title", n=0))
        self._sel_info.setWordWrap(True)
        self._sel_info.setStyleSheet(f"color: {_th.TEXT_SEC}; font-size:9px;")
        layout.addWidget(self._sel_info)

        # Live list of every assigned side (dim_name) + its thickness, so the
        # parametric data being built is always visible (mirrors a stock entry).
        _sep()
        sides_hdr = QLabel(t("profile_sides_section"))
        sides_hdr.setStyleSheet(f"color: {_th.ACCENT}; font-weight:bold; font-size:10px;")
        layout.addWidget(sides_hdr)
        self._sides_lbl = QLabel(t("profile_no_sides"))
        self._sides_lbl.setWordWrap(True)
        self._sides_lbl.setStyleSheet(f"color: {_th.TEXT_PRI}; font-size:9px; font-family:'DejaVu Sans Mono';")
        layout.addWidget(self._sides_lbl)

        # Manual side entry: add sides by hand (name + length + thickness)
        # without assigning them on the drawing — useful for declaring the
        # parametric dims before/without sketching every edge.
        self._manual_sides: List[Dict[str, float]] = []
        man_row = QHBoxLayout()
        man_row.setSpacing(3)
        self._man_name = QLineEdit(); self._man_name.setPlaceholderText(t("field_name"))
        self._man_len = QLineEdit();  self._man_len.setPlaceholderText(t("placeholder_length", u=units.u_len()))
        self._man_len.setFixedWidth(58)
        self._man_thick = QLineEdit(); self._man_thick.setPlaceholderText("t")
        self._man_thick.setFixedWidth(34)
        man_add = QPushButton()
        man_add.setIcon(themed_icon("plus", _th.TEXT_PRI, 14))
        man_add.setIconSize(QSize(14, 14))
        man_add.setFixedSize(26, 26)
        man_add.setToolTip(t("profile_add_manual_side"))
        man_add.clicked.connect(self._add_manual_side)
        for w in (self._man_name, self._man_len, self._man_thick):
            w.setFixedHeight(26)
        man_row.addWidget(self._man_name, 1)
        man_row.addWidget(self._man_len)
        man_row.addWidget(self._man_thick)
        man_row.addWidget(man_add)
        layout.addLayout(man_row)
        man_del = QPushButton(t("profile_remove_last_side"))
        man_del.setFixedHeight(22)
        man_del.setStyleSheet(f"font-size:9px; color:{_th.TEXT_SEC};")
        man_del.clicked.connect(self._remove_last_manual_side)
        layout.addWidget(man_del)

        # Material data sheet — the same data you'd enter when saving to stock,
        # here only to describe/save the material. Stored in self._meta.
        _sep()
        data_hdr = QLabel(t("profile_data_section"))
        data_hdr.setStyleSheet(f"color: {_th.ACCENT}; font-weight:bold; font-size:10px;")
        layout.addWidget(data_hdr)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(6)
        form.setVerticalSpacing(4)
        _sym = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CNY": "¥"}.get(
            app_config.get().currency, app_config.get().currency)
        self._meta: Dict[str, QLineEdit] = {}
        for key, label in (
            ("profile_name", t("stock_profile")),
            ("material", t("stock_material")),
            ("quality", t("placeholder_quality")),
            # Canonical geometric parameters (§21.5) — these back the catalogue
            # meta (h/b/tw/tf/seccion_cm2/peso_lineal_kg_m) and the Costs tab.
            ("h", f"h ({units.u_len()})"),
            ("b", f"b ({units.u_len()})"),
            ("tw", f"tw ({units.u_len()})"),
            ("tf", f"tf ({units.u_len()})"),
            ("seccion_cm2", t("section") + " (cm²)"),
            ("peso_lineal_kg_m", t("weight_per_meter")),
            ("kg_por_m", t("kg_per_meter", u_wpm=units.u_linear_weight())),
            ("precio_kg", t("price_kg", sym=_sym)),
            ("precio_m", t("price_m", sym=_sym)),
            ("peso_especifico", t("specific_weight", u_density=units.u_density())),
        ):
            e = QLineEdit()
            e.setFixedHeight(24)
            self._meta[key] = e
            cap = QLabel(label)
            cap.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
            form.addRow(cap, e)
        self._meta["peso_especifico"].setText("7.85")
        layout.addLayout(form)

        _sep()
        file_lbl = QLabel("DXF / PNG")
        file_lbl.setStyleSheet(f"color: {_th.ACCENT}; font-weight:bold; font-size:10px;")
        layout.addWidget(file_lbl)
        for text, slot in (
            (t("profile_import_dxf"), self._import_dxf),
            (t("profile_export_dxf"), self._export_dxf),
            (t("profile_export_png"), self._export_png_transparent),
        ):
            b = QPushButton(text)
            b.clicked.connect(lambda checked=False, fn=slot: self._with_undo(fn))
            layout.addWidget(b)

        _sep()
        clear_btn = QPushButton(t("clear"))
        clear_btn.clicked.connect(lambda: self._with_undo(self._clear_all))
        layout.addWidget(clear_btn)
        save_btn = QPushButton(t("save"))
        save_btn.setProperty("variant", "accent")
        save_btn.clicked.connect(self._save_profile)
        layout.addWidget(save_btn)

    # ── Tool management ──────────────────────────────────────────────────────

    def _set_tool(self, tool: str) -> None:
        self._finish_poly()
        self._arc_points.clear()
        self._current_tool = tool
        from nestify.ui_qt.nesting_scene import _text_color_for_bg
        _accent_text = _text_color_for_bg(_th.ACCENT)
        for tid, btn in self._tool_buttons.items():
            if tid == tool:
                btn.setStyleSheet(f"background: {_th.ACCENT}; color: {_accent_text};")
            else:
                btn.setStyleSheet("")
        hints = {
            "line": t("hint_line"), "rect": t("hint_rect"),
            "circle": t("hint_circle"), "polygon": t("hint_polygon"),
            "eraser": t("hint_eraser"), "void": t("hint_void"),
            "select": t("hint_select"), "trim": t("hint_trim"),
            "extend": t("hint_extend"), "arc_3pt": t("hint_arc_3pt"),
            "arc_cse": t("hint_arc_cse"),
        }
        self._info_lbl.setText(hints.get(tool, ""))

    def _toggle_ortho(self) -> None:
        self._ortho_mode = not self._ortho_mode
        if self._ortho_mode:
            from nestify.ui_qt.nesting_scene import _text_color_for_bg
            self._ortho_btn.setStyleSheet(f"background: {_th.ACCENT}; color: {_text_color_for_bg(_th.ACCENT)};")
        else:
            self._ortho_btn.setStyleSheet("")

    # ── Coordinate transforms ────────────────────────────────────────────────
    # World (model) units ↔ canvas pixels via the single _view_scale zoom factor.
    # _to_world maps a pixel position back to model coords (for hit-testing /
    # placing); _to_canvas maps model coords to pixels (for drawing).
    def _to_world(self, x: float, y: float) -> Tuple[float, float]:
        ox, oy = self._view_offset
        return (x - ox) / self._view_scale, (y - oy) / self._view_scale

    def _to_canvas(self, lx: float, ly: float) -> Tuple[float, float]:
        ox, oy = self._view_offset
        return lx * self._view_scale + ox, ly * self._view_scale + oy

    def _on_wheel(self, event: QWheelEvent) -> None:
        # Wheel zoom: ±15% per notch, clamped to 0.2×–10×, anchored at the
        # cursor — the world point under the pointer stays put as you zoom.
        pos = event.position()
        cx, cy = pos.x(), pos.y()
        wx, wy = self._to_world(cx, cy)
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self._view_scale = max(0.2, min(10.0, self._view_scale * factor))
        self._view_offset = (cx - wx * self._view_scale, cy - wy * self._view_scale)
        self._canvas.update()

    # ── Undo / redo ──────────────────────────────────────────────────────────

    def _snapshot(self) -> list:
        return [s.to_dict() for s in self._shapes]

    def _checkpoint(self, before: list) -> None:
        """Push `before` onto the undo stack if the drawing actually changed."""
        if before != self._snapshot():
            self._undo_stack.append(before)
            if len(self._undo_stack) > 50:
                self._undo_stack.pop(0)
            self._redo_stack.clear()

    def _with_undo(self, fn, *args) -> None:
        """Run a possibly-mutating operation, recording an undo checkpoint."""
        before = self._snapshot()
        try:
            fn(*args)
        finally:
            self._checkpoint(before)

    def _restore(self, snap: list) -> None:
        self._shapes = [ProfileShape.from_dict(d) for d in snap]
        self._selected_shapes.clear()
        self._poly_points.clear()
        self._arc_points.clear()
        self._update_selection_info()
        self._refresh_sides_list()
        self._canvas.update()

    def _undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())

    def _redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())

    # ── Snap ─────────────────────────────────────────────────────────────────

    def _draw_ref(self) -> Optional[Tuple[float, float]]:
        """Reference point for perpendicular snap = the point the current line
        segment is being drawn FROM (last poly vertex or the line start)."""
        if self._poly_points:
            return self._poly_points[-1]
        if self._drawing and self._start_pos and self._current_tool in ("line", "polygon"):
            return self._start_pos
        return None

    def _snap(self, x: float, y: float,
              ref: Optional[Tuple[float, float]] = None) -> Tuple[float, float, Optional[str]]:
        # AutoCAD-style object snap, in priority order: endpoint/vertex →
        # midpoint → centre (circles/arcs) → intersection → perpendicular →
        # grid → nearest point on an edge.
        for shape in self._shapes:
            for vx, vy in shape.vertices():
                if math.hypot(x - vx, y - vy) <= SNAP_RADIUS:
                    return vx, vy, "vertex"
        for shape in self._shapes:
            for mx, my in shape.midpoints():
                if math.hypot(x - mx, y - my) <= SNAP_RADIUS:
                    return mx, my, "midpoint"
        # Centre snap: circles/arcs expose their centre as points[0].
        for shape in self._shapes:
            if shape.shape_type in ("circle", "arc_3pt", "arc_cse") and shape.points:
                cx, cy = shape.points[0]
                if math.hypot(x - cx, y - cy) <= SNAP_RADIUS:
                    return cx, cy, "center"
        # Intersection snap: where two segments (of any shapes) cross.
        segs = [seg for sh in self._shapes for seg in sh.segments()]
        best_ix = None
        best_ixd = SNAP_RADIUS
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                pt = _segment_intersection(segs[i][0], segs[i][1], segs[j][0], segs[j][1])
                if pt is None:
                    continue
                d = math.hypot(x - pt[0], y - pt[1])
                if d < best_ixd:
                    best_ixd = d
                    best_ix = pt
        if best_ix is not None:
            return best_ix[0], best_ix[1], "intersection"
        # Perpendicular snap: when drawing from a reference point, snap to the
        # foot of the perpendicular dropped onto a segment.
        if ref is not None:
            best_pp = None
            best_ppd = SNAP_RADIUS
            for sh in self._shapes:
                for (ax, ay), (bx, by) in sh.segments():
                    foot = _perpendicular_foot(ref[0], ref[1], ax, ay, bx, by)
                    if foot is None:
                        continue
                    d = math.hypot(x - foot[0], y - foot[1])
                    if d < best_ppd:
                        best_ppd = d
                        best_pp = foot
            if best_pp is not None:
                return best_pp[0], best_pp[1], "perpendicular"
        gs = 20
        gx, gy = round(x / gs) * gs, round(y / gs) * gs
        if math.hypot(x - gx, y - gy) <= SNAP_RADIUS:
            return gx, gy, "grid"
        # Nearest point on a segment (lowest priority) so you can latch onto an
        # edge anywhere along it, not just at its vertices/midpoint.
        best = None
        best_d = SNAP_RADIUS
        for shape in self._shapes:
            for (ax, ay), (bx, by) in shape.segments():
                px, py = _project_point_on_segment(x, y, ax, ay, bx, by)
                d = math.hypot(x - px, y - py)
                if d < best_d:
                    best_d = d
                    best = (px, py)
        if best is not None:
            return best[0], best[1], "edge"
        return x, y, None

    def _apply_ortho(self, x, y, ref):
        if not self._ortho_mode:
            return x, y
        rx, ry = ref
        if abs(x - rx) >= abs(y - ry):
            return x, ry
        return rx, y

    # ── Mouse events ─────────────────────────────────────────────────────────

    def _on_press(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        pos = event.position()
        x, y = self._to_world(pos.x(), pos.y())
        sx, sy, stype = self._snap(x, y, ref=self._draw_ref())

        if self._current_tool == "eraser":
            self._erase_at(x, y); return
        if self._current_tool == "select":
            self._sel_drag_start = (x, y)
            self._select_at(x, y, multi=shift); return
        if self._current_tool == "void":
            self._toggle_void_at(x, y); return
        if self._current_tool == "trim":
            self._trim_drag_start = (x, y)
            self._trim_at(x, y); return
        if self._current_tool == "extend":
            self._extend_at(x, y); return
        if self._current_tool in ("arc_3pt", "arc_cse"):
            self._add_arc_point(sx, sy); return
        if self._current_tool in ("line", "polygon"):
            if self._ortho_mode and self._poly_points:
                sx, sy = self._apply_ortho(sx, sy, self._poly_points[-1])
            self._add_poly_point(sx, sy); return

        self._drawing = True
        self._start_pos = (sx, sy)

    def _on_motion(self, event: QMouseEvent) -> None:
        pos = event.position()
        x, y = self._to_world(pos.x(), pos.y())
        sx, sy, stype = self._snap(x, y, ref=self._draw_ref())
        self._snap_pos = (sx, sy)
        self._snap_type = stype
        self._mouse_pos = (x, y)

        if self._drawing and self._start_pos:
            if self._ortho_mode:
                sx, sy = self._apply_ortho(sx, sy, self._start_pos)
            self._drag_pos = (sx, sy)
            self._canvas.update()
            return

        if self._current_tool == "select" and self._sel_drag_start:
            self._sel_drag_end = (x, y)
            self._canvas.update()
            return

        if self._current_tool == "trim" and self._trim_drag_start:
            self._trim_drag_end = (x, y)
            self._canvas.update()
            return

        self._canvas.update()

    def _on_release(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        x, y = self._to_world(pos.x(), pos.y())

        if self._current_tool == "select" and self._sel_drag_start:
            sx, sy = self._sel_drag_start
            self._sel_drag_start = None
            self._sel_drag_end = None
            if abs(x - sx) > 5 or abs(y - sy) > 5:
                self._window_select(sx, sy, x, y)
            self._canvas.update()
            return

        if self._current_tool == "trim" and self._trim_drag_start:
            sx, sy = self._trim_drag_start
            self._trim_drag_start = None
            self._trim_drag_end = None
            if abs(x - sx) > 5 or abs(y - sy) > 5:
                self._trim_fence(sx, sy, x, y)
            self._canvas.update()
            return

        if not self._drawing or not self._start_pos:
            return
        self._drawing = False
        sxs, sys, _ = self._snap(x, y)
        if self._ortho_mode:
            sxs, sys = self._apply_ortho(sxs, sys, self._start_pos)
        sx0, sy0 = self._start_pos
        self._drag_pos = None
        if abs(sxs - sx0) < 5 and abs(sys - sy0) < 5:
            return
        if self._current_tool == "rect":
            self._shapes.append(ProfileShape("rect", [(sx0, sy0), (sxs, sys)], closed=True))
        elif self._current_tool == "circle":
            self._shapes.append(ProfileShape("circle", [(sx0, sy0), (sxs, sys)], closed=True))
        self._canvas.update()

    def _on_double_click(self, event: QMouseEvent) -> None:
        if self._current_tool in ("line", "polygon") and self._poly_points:
            self._finish_poly()

    # ── Painting ─────────────────────────────────────────────────────────────

    def _paint_shapes(self, p: QPainter) -> None:
        for shape in self._shapes:
            self._draw_shape(p, shape)

        # Poly progress
        if self._poly_points:
            pen = QPen(QColor(_th.ACCENT), 2)
            p.setPen(pen)
            pts = self._poly_points
            for i in range(len(pts) - 1):
                c0 = self._to_canvas(*pts[i])
                c1 = self._to_canvas(*pts[i + 1])
                p.drawLine(QPointF(*c0), QPointF(*c1))
            for px, py in pts:
                cx, cy = self._to_canvas(px, py)
                p.setBrush(QBrush(QColor(_th.ACCENT)))
                p.drawEllipse(QPointF(cx, cy), 3, 3)
            # Preview line to mouse
            if self._mouse_pos:
                mx, my = self._mouse_pos
                smx, smy, _ = self._snap(mx, my)
                if self._ortho_mode:
                    smx, smy = self._apply_ortho(smx, smy, pts[-1])
                last = self._to_canvas(*pts[-1])
                cur = self._to_canvas(smx, smy)
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setWidth(1)
                p.setPen(pen)
                p.drawLine(QPointF(*last), QPointF(*cur))

                # Dimension HUD next to the cursor (AutoCAD-style dynamic input):
                # shows the live length+angle, or the typed values. Tab switches
                # the active field (marked _), Enter commits.
                import math as _m
                live_len = _m.hypot(smx - pts[-1][0], smy - pts[-1][1])
                live_ang = -_m.degrees(_m.atan2(smy - pts[-1][1], smx - pts[-1][0]))
                typing = bool(self._dim_input or self._dim_angle)
                len_s = self._dim_input or f"{live_len:.0f}"
                ang_s = self._dim_angle or f"{live_ang:.0f}"
                if typing and self._dim_field == "len":
                    len_s += "_"
                if typing and self._dim_field == "ang":
                    ang_s += "_"
                label = f"L {len_s}  ∠ {ang_s}°"
                p.save()
                f = p.font(); f.setPixelSize(12); f.setBold(typing); p.setFont(f)
                fm = p.fontMetrics()
                tw = fm.horizontalAdvance(label) + 10
                th = fm.height() + 2
                bx, by = cur[0] + 12, cur[1] - th - 4
                bg_hex = _th.ACCENT if typing else "#333333"
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(bg_hex)))
                p.drawRoundedRect(QRectF(bx, by, tw, th), 3, 3)
                from nestify.ui_qt.nesting_scene import _text_color_for_bg
                p.setPen(QPen(QColor(_text_color_for_bg(bg_hex))))
                p.drawText(QRectF(bx, by, tw, th), Qt.AlignmentFlag.AlignCenter, label)
                p.restore()

        # Arc progress dots
        if self._arc_points:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#FF6600")))
            for px, py in self._arc_points:
                cx, cy = self._to_canvas(px, py)
                p.drawEllipse(QPointF(cx, cy), 4, 4)

        # Temp rect/circle preview
        if self._drawing and self._start_pos and self._drag_pos:
            pen = QPen(QColor(_th.ACCENT), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            s = self._to_canvas(*self._start_pos)
            e = self._to_canvas(*self._drag_pos)
            if self._current_tool == "rect":
                p.drawRect(QRectF(QPointF(*s), QPointF(*e)))
            elif self._current_tool == "circle":
                r = math.hypot(e[0] - s[0], e[1] - s[1])
                p.drawEllipse(QPointF(*s), r, r)

        # Selection rect
        if self._sel_drag_start and self._sel_drag_end:
            sx, sy = self._sel_drag_start
            ex, ey = self._sel_drag_end
            color = "#3399FF" if ex >= sx else "#33CC66"
            pen = QPen(QColor(color), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            c0 = self._to_canvas(sx, sy)
            c1 = self._to_canvas(ex, ey)
            p.drawRect(QRectF(QPointF(*c0), QPointF(*c1)))

        # Trim fence
        if self._trim_drag_start and self._trim_drag_end:
            pen = QPen(QColor(_th.DANGER), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            c0 = self._to_canvas(*self._trim_drag_start)
            c1 = self._to_canvas(*self._trim_drag_end)
            p.drawLine(QPointF(*c0), QPointF(*c1))

        # Snap indicator
        if self._snap_pos and self._snap_type:
            sx, sy = self._to_canvas(*self._snap_pos)
            if self._snap_type == "vertex":
                pen = QPen(QColor("#0066FF"), 2)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(QRectF(sx - 4, sy - 4, 8, 8))
            elif self._snap_type == "midpoint":
                pen = QPen(QColor("#00AA44"), 2)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                from PySide6.QtGui import QPolygonF
                tri = QPolygonF([QPointF(sx, sy - 5), QPointF(sx - 5, sy + 5), QPointF(sx + 5, sy + 5)])
                p.drawPolygon(tri)
            elif self._snap_type == "center":
                # Circle marker (like AutoCAD's centre snap).
                pen = QPen(QColor("#AA00CC"), 2)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(sx, sy), 5, 5)
            elif self._snap_type == "intersection":
                # Bold blue X (AutoCAD's intersection osnap marker).
                pen = QPen(QColor("#0066FF"), 2)
                p.setPen(pen)
                p.drawLine(QPointF(sx - 6, sy - 6), QPointF(sx + 6, sy + 6))
                p.drawLine(QPointF(sx - 6, sy + 6), QPointF(sx + 6, sy - 6))
            elif self._snap_type == "perpendicular":
                # AutoCAD perpendicular marker: a small right-angle square.
                pen = QPen(QColor("#00AA44"), 2)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawLine(QPointF(sx - 6, sy + 6), QPointF(sx - 6, sy - 6))
                p.drawLine(QPointF(sx - 6, sy + 6), QPointF(sx + 6, sy + 6))
                p.drawLine(QPointF(sx - 6, sy), QPointF(sx, sy))
                p.drawLine(QPointF(sx, sy), QPointF(sx, sy + 6))
            elif self._snap_type == "edge":
                # Orange X marker for nearest-point-on-edge.
                pen = QPen(QColor("#FF8800"), 2)
                p.setPen(pen)
                p.drawLine(QPointF(sx - 5, sy - 5), QPointF(sx + 5, sy + 5))
                p.drawLine(QPointF(sx - 5, sy + 5), QPointF(sx + 5, sy - 5))

    def _draw_shape(self, p: QPainter, shape: ProfileShape) -> None:
        is_selected = id(shape) in self._selected_shapes
        if shape.is_void:
            fill = QColor("#FFFFFF")
            outline = QColor(_th.DANGER)
        else:
            fill = QColor("#FFB380") if is_selected else QColor("#D4D8E0")
            outline = QColor("#FF6600") if is_selected else QColor("#333333")
        width = 3 if is_selected else 1

        pen = QPen(outline, width)
        p.setPen(pen)
        p.setBrush(QBrush(fill))

        if shape.shape_type == "rect":
            c0 = self._to_canvas(*shape.points[0])
            c1 = self._to_canvas(*shape.points[1])
            p.drawRect(QRectF(QPointF(*c0), QPointF(*c1)))
        elif shape.shape_type == "circle":
            cx, cy = shape.points[0]
            r = shape._radius() * self._view_scale
            ccx, ccy = self._to_canvas(cx, cy)
            p.drawEllipse(QPointF(ccx, ccy), r, r)
        elif shape.shape_type == "polygon" and shape.closed and len(shape.points) >= 3:
            from PySide6.QtGui import QPolygonF
            poly = QPolygonF()
            for px, py in shape.points:
                cx, cy = self._to_canvas(px, py)
                poly.append(QPointF(cx, cy))
            p.drawPolygon(poly)
        elif shape.shape_type in ("line", "polygon"):
            p.setBrush(Qt.BrushStyle.NoBrush)
            pts = shape.points
            for i in range(len(pts) - 1):
                c0 = self._to_canvas(*pts[i])
                c1 = self._to_canvas(*pts[i + 1])
                p.drawLine(QPointF(*c0), QPointF(*c1))
            if shape.closed and len(pts) >= 3:
                c0 = self._to_canvas(*pts[-1])
                c1 = self._to_canvas(*pts[0])
                p.drawLine(QPointF(*c0), QPointF(*c1))

        if shape.dim_name or shape.thickness:
            bounds = shape.bounds()
            mx = (bounds[0] + bounds[2]) / 2
            my = (bounds[1] + bounds[3]) / 2
            cmx, cmy = self._to_canvas(mx, my)
            parts = []
            if shape.dim_name:
                parts.append(shape.dim_name)
            if shape.thickness:
                parts.append(f"t={shape.thickness}")
            p.setPen(QPen(QColor("#000000")))
            p.setFont(QFont("IBM Plex Sans", 8, QFont.Weight.Bold))
            p.drawText(QPointF(cmx, cmy), " | ".join(parts))

    # ── Line / Polygon drawing ───────────────────────────────────────────────

    def _add_poly_point(self, x: float, y: float) -> None:
        if self._poly_points:
            first = self._poly_points[0]
            if (math.hypot(x - first[0], y - first[1]) <= CLOSE_RADIUS
                    and len(self._poly_points) >= 3):
                self._finish_poly(close=True)
                return
        self._poly_points.append((x, y))
        self._canvas.update()

    def _finish_poly(self, close: bool = False) -> None:
        pts = self._poly_points
        self._poly_points = []
        if len(pts) < 2:
            self._canvas.update()
            return
        if self._current_tool == "polygon":
            close = True
        is_closed = close and len(pts) >= 3
        shape = ProfileShape("polygon" if is_closed else "line", pts, closed=is_closed)
        self._shapes.append(shape)
        self._canvas.update()
        self._try_merge_closed_contours()

    def _try_merge_closed_contours(self) -> None:
        tol = CLOSE_RADIUS
        open_lines = [s for s in self._shapes if s.shape_type == "line" and not s.closed]
        if len(open_lines) < 2:
            return
        dist = lambda p1, p2: math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        for start_shape in open_lines:
            chain = [start_shape]; rev = [False]; used = {id(start_shape)}
            current_end = start_shape.points[-1]
            chain_start = start_shape.points[0]
            while True:
                found = False
                for s in open_lines:
                    if id(s) in used:
                        continue
                    if dist(current_end, s.points[0]) <= tol:
                        chain.append(s); rev.append(False); used.add(id(s))
                        current_end = s.points[-1]; found = True; break
                    elif dist(current_end, s.points[-1]) <= tol:
                        chain.append(s); rev.append(True); used.add(id(s))
                        current_end = s.points[0]; found = True; break
                if not found:
                    break
            if len(chain) >= 2 and dist(current_end, chain_start) <= tol:
                all_pts = []
                for shape, r in zip(chain, rev):
                    p = list(reversed(shape.points)) if r else list(shape.points)
                    if all_pts and dist(all_pts[-1], p[0]) <= tol:
                        p = p[1:]
                    all_pts.extend(p)
                if len(all_pts) > 1 and dist(all_pts[-1], all_pts[0]) <= tol:
                    all_pts = all_pts[:-1]
                first = chain[0]
                self._shapes = [s for s in self._shapes if id(s) not in used]
                self._selected_shapes -= used
                merged = ProfileShape("polygon", all_pts, is_void=first.is_void,
                                      dim_name=first.dim_name, closed=True,
                                      thickness=first.thickness)
                self._shapes.append(merged)
                self._canvas.update()
                return

    # ── Arc drawing ──────────────────────────────────────────────────────────

    def _add_arc_point(self, x: float, y: float) -> None:
        self._arc_points.append((x, y))
        if self._current_tool == "arc_3pt" and len(self._arc_points) == 3:
            start, end, mid = self._arc_points
            pts = _generate_arc_points(start, end, mid)
            if len(pts) >= 2:
                self._shapes.append(ProfileShape("line", pts, closed=False))
            self._arc_points.clear()
        elif self._current_tool == "arc_cse" and len(self._arc_points) == 3:
            center, start, end = self._arc_points
            pts = _generate_arc_cse_points(center, start, end)
            if len(pts) >= 2:
                self._shapes.append(ProfileShape("line", pts, closed=False))
            self._arc_points.clear()
        self._canvas.update()

    def _open_arc_exact_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(t("arc_exact_dialog_title"))
        dlg.resize(320, 340)
        dlg.setModal(True)

        form = QFormLayout(dlg)
        entries = {}
        for key, label, default in [
            ("cx", t("arc_exact_cx"), "200"), ("cy", t("arc_exact_cy"), "200"),
            ("r", t("arc_exact_r"), "50"), ("a0", t("arc_exact_a0"), "0"),
            ("a1", t("arc_exact_a1"), "180"),
        ]:
            e = QLineEdit(default)
            form.addRow(label, e)
            entries[key] = e

        ccw_cb = QCheckBox(t("arc_exact_ccw"))
        ccw_cb.setChecked(True)
        form.addRow(ccw_cb)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton(t("save"))
        ok_btn.setProperty("variant", "accent")
        cancel_btn = QPushButton(t("cancel"))

        def _apply():
            try:
                cx = float(entries["cx"].text()); cy = float(entries["cy"].text())
                r = float(entries["r"].text()); a0 = float(entries["a0"].text())
                a1 = float(entries["a1"].text())
            except ValueError:
                return
            if r <= 0:
                return
            a0r = math.radians(a0); a1r = math.radians(a1)
            sweep = a1r - a0r
            if ccw_cb.isChecked():
                if sweep <= 0: sweep += 2 * math.pi
            else:
                if sweep >= 0: sweep -= 2 * math.pi
            n = max(8, int(abs(sweep) / math.radians(5)))
            pts = [(cx + r * math.cos(a0r + i / n * sweep),
                     cy + r * math.sin(a0r + i / n * sweep)) for i in range(n + 1)]
            if len(pts) >= 2:
                self._shapes.append(ProfileShape("line", pts, closed=False))
                self._canvas.update()
            dlg.accept()

        ok_btn.clicked.connect(_apply)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)
        dlg.exec()

    # ── Selection / Window select ────────────────────────────────────────────

    def _select_at(self, x, y, multi=False) -> None:
        hit = None
        for shape in reversed(self._shapes):
            if shape.hit_test(x, y):
                hit = shape; break
        if not multi:
            self._selected_shapes.clear()
        if hit is not None:
            sid = id(hit)
            if sid in self._selected_shapes:
                self._selected_shapes.discard(sid)
            else:
                self._selected_shapes.add(sid)
        sel = self._get_selected_shapes()
        if sel:
            self._dim_name.setText(sel[0].dim_name or "")
            self._thickness_entry.setText(str(sel[0].thickness) if sel[0].thickness else "")
        self._update_selection_info()
        self._canvas.update()

    def _window_select(self, x0, y0, x1, y1) -> None:
        lr = x1 >= x0
        self._selected_shapes.clear()
        for shape in self._shapes:
            if lr:
                if shape.fully_inside_rect(x0, y0, x1, y1):
                    self._selected_shapes.add(id(shape))
            else:
                if shape.crosses_rect(x0, y0, x1, y1):
                    self._selected_shapes.add(id(shape))
        sel = self._get_selected_shapes()
        if sel:
            self._dim_name.setText(sel[0].dim_name or "")
            self._thickness_entry.setText(str(sel[0].thickness) if sel[0].thickness else "")
        self._update_selection_info()
        self._canvas.update()

    # ── Tool actions ─────────────────────────────────────────────────────────

    def _erase_at(self, x, y) -> None:
        for shape in self._shapes[:]:
            if shape.hit_test(x, y):
                self._shapes.remove(shape)
                self._selected_shapes.discard(id(shape))
                break
        self._update_selection_info()
        self._canvas.update()

    def _toggle_void_at(self, x, y) -> None:
        sel = self._get_selected_shapes()
        if sel:
            for s in sel:
                s.is_void = not s.is_void
        else:
            cands = [s for s in self._shapes if s.hit_test(x, y)]
            if cands:
                smallest = min(cands, key=lambda s: s.area())
                smallest.is_void = not smallest.is_void
        self._canvas.update()

    def _trim_at(self, x, y) -> None:
        best_shape = None; best_idx = -1; best_d = float("inf")
        for shape in self._shapes:
            for i, (a, b) in enumerate(shape.segments()):
                d = _point_to_segment_dist(x, y, a, b)
                if d < best_d and d <= 8:
                    best_d = d; best_shape = shape; best_idx = i
        if best_shape is None:
            return
        seg_a, seg_b = best_shape.segments()[best_idx]
        inters = []
        for other in self._shapes:
            if other is best_shape:
                continue
            for oseg in other.segments():
                pt = _segments_intersect(seg_a, seg_b, oseg[0], oseg[1])
                if pt is not None:
                    dx = seg_b[0] - seg_a[0]; dy = seg_b[1] - seg_a[1]
                    lsq = dx * dx + dy * dy
                    tp = ((pt[0] - seg_a[0]) * dx + (pt[1] - seg_a[1]) * dy) / lsq if lsq > 0 else 0
                    inters.append((pt[0], pt[1], tp))
        if not inters or best_shape.shape_type in ("rect", "circle"):
            self._shapes.remove(best_shape)
            self._selected_shapes.discard(id(best_shape))
        else:
            dx = seg_b[0] - seg_a[0]; dy = seg_b[1] - seg_a[1]
            lsq = dx * dx + dy * dy
            ct = ((x - seg_a[0]) * dx + (y - seg_a[1]) * dy) / lsq if lsq > 0 else 0
            inters.sort(key=lambda i: i[2])
            lt, ut = 0.0, 1.0
            for _, _, it in inters:
                if it < ct: lt = max(lt, it)
                elif it > ct: ut = min(ut, it)
            self._trim_segment_between(best_shape, best_idx, lt, ut)
        self._canvas.update()

    def _trim_segment_between(self, shape, seg_idx, t_start, t_end) -> None:
        pts = list(shape.points); n = len(pts)
        self._shapes.remove(shape)
        self._selected_shapes.discard(id(shape))
        verts = shape.vertices()
        seg_a = verts[seg_idx]; seg_b = verts[(seg_idx + 1) % len(verts)]
        pt_s = (seg_a[0] + t_start * (seg_b[0] - seg_a[0]),
                seg_a[1] + t_start * (seg_b[1] - seg_a[1]))
        pt_e = (seg_a[0] + t_end * (seg_b[0] - seg_a[0]),
                seg_a[1] + t_end * (seg_b[1] - seg_a[1]))
        def ok(pl):
            if len(pl) < 2: return False
            if len(pl) == 2 and math.hypot(pl[1][0]-pl[0][0], pl[1][1]-pl[0][1]) < 1: return False
            return True
        if shape.closed and n >= 3:
            np_ = pts[seg_idx+1:] + pts[:seg_idx+1]
            np_.insert(0, pt_e); np_.append(pt_s)
            if ok(np_):
                self._shapes.append(ProfileShape("line", np_, closed=False,
                    is_void=shape.is_void, dim_name=shape.dim_name, thickness=shape.thickness))
        else:
            p1 = pts[:seg_idx+1] + [pt_s]
            p2 = [pt_e] + pts[seg_idx+1:]
            if ok(p1):
                self._shapes.append(ProfileShape("line", p1, closed=False,
                    is_void=shape.is_void, dim_name=shape.dim_name, thickness=shape.thickness))
            if ok(p2):
                self._shapes.append(ProfileShape("line", p2, closed=False,
                    is_void=shape.is_void, dim_name=shape.dim_name, thickness=shape.thickness))

    def _trim_fence(self, x0, y0, x1, y1) -> None:
        fence = ((x0, y0), (x1, y1))
        to_trim = []
        for shape in self._shapes:
            for i, (a, b) in enumerate(shape.segments()):
                pt = _segments_intersect(a, b, fence[0], fence[1])
                if pt is not None:
                    to_trim.append((shape, i, pt)); break
        for shape, seg_idx, ipt in to_trim:
            if shape not in self._shapes:
                continue
            if shape.shape_type in ("rect", "circle"):
                self._shapes.remove(shape)
                self._selected_shapes.discard(id(shape))
            else:
                verts = shape.vertices()
                sa = verts[seg_idx]; sb = verts[(seg_idx+1) % len(verts)]
                dx = sb[0]-sa[0]; dy = sb[1]-sa[1]; lsq = dx*dx+dy*dy
                if lsq < 1e-10: continue
                th = ((ipt[0]-sa[0])*dx+(ipt[1]-sa[1])*dy)/lsq
                th = max(0.01, min(0.99, th))
                self._trim_segment_between(shape, seg_idx, th-0.01, th+0.01)
        self._canvas.update()

    def _extend_at(self, x, y) -> None:
        best = None; bidx = -1; bd = float("inf")
        for shape in self._shapes:
            if shape.shape_type in ("rect", "circle"): continue
            pts = shape.points
            if len(pts) < 2: continue
            ds = math.hypot(x-pts[0][0], y-pts[0][1])
            de = math.hypot(x-pts[-1][0], y-pts[-1][1])
            d = min(ds, de)
            if d < bd and d <= 15:
                bd = d; best = shape; bidx = 0 if ds <= de else -1
        if best is None: return
        pts = best.points
        if bidx == 0:
            ep = pts[0]; d = (pts[0][0]-pts[1][0], pts[0][1]-pts[1][1])
        else:
            ep = pts[-1]; d = (pts[-1][0]-pts[-2][0], pts[-1][1]-pts[-2][1])
        dl = math.hypot(d[0], d[1])
        if dl < 1e-6: return
        d = (d[0]/dl, d[1]/dl)
        bh = None; bhd = float("inf")
        for other in self._shapes:
            if other is best: continue
            for seg in other.segments():
                hit = _line_intersect_ray(seg[0], seg[1], ep, d)
                if hit:
                    hd = math.hypot(hit[0]-ep[0], hit[1]-ep[1])
                    if hd < bhd and hd > 1e-6:
                        bhd = hd; bh = hit
        if bh:
            np_ = list(pts)
            if bidx == 0: np_.insert(0, bh)
            else: np_.append(bh)
            best.points = np_
            self._canvas.update()

    # ── Assign dimension / thickness ─────────────────────────────────────────

    def _assign_dim(self) -> None:
        for s in self._get_selected_shapes():
            s.dim_name = self._dim_name.text().strip()
        self._update_selection_info()
        self._refresh_sides_list()
        self._canvas.update()

    def _assign_thickness(self) -> None:
        try:
            val = float(self._thickness_entry.text().strip())
        except (ValueError, TypeError):
            val = 0.0
        for s in self._get_selected_shapes():
            s.thickness = val
        self._update_selection_info()
        self._refresh_sides_list()
        self._canvas.update()

    def _add_manual_side(self) -> None:
        """Add a side declared by hand (not tied to any drawn shape)."""
        name = self._man_name.text().strip()
        if not name:
            return
        try:
            length = float(self._man_len.text().strip() or "0")
        except ValueError:
            length = 0.0
        try:
            thick = float(self._man_thick.text().strip() or "0")
        except ValueError:
            thick = 0.0
        self._manual_sides.append({"name": name, "length": length, "thickness": thick})
        self._man_name.clear(); self._man_len.clear(); self._man_thick.clear()
        self._refresh_sides_list()

    def _remove_last_manual_side(self) -> None:
        if self._manual_sides:
            self._manual_sides.pop()
            self._refresh_sides_list()

    def _refresh_sides_list(self) -> None:
        """Update the right-panel list of named sides and their thicknesses.

        Merges sides assigned on the drawing (shape dim_name/thickness) with the
        manually declared ones (marked with *)."""
        rows = []
        for s in self._shapes:
            if not s.dim_name and not s.thickness:
                continue
            name = s.dim_name or s.shape_type
            length = s.length() if hasattr(s, "length") else 0.0
            txt = f"{name}"
            if length:
                txt += f"  {length:.1f}"
            if s.thickness:
                txt += f"  t={s.thickness:g}"
            rows.append(txt)
        for m in getattr(self, "_manual_sides", []):
            txt = f"* {m['name']}"
            if m.get("length"):
                txt += f"  {m['length']:.1f}"
            if m.get("thickness"):
                txt += f"  t={m['thickness']:g}"
            rows.append(txt)
        self._sides_lbl.setText("\n".join(rows) if rows else t("profile_no_sides"))

    def _get_selected_shapes(self) -> List[ProfileShape]:
        return [s for s in self._shapes if id(s) in self._selected_shapes]

    def _update_selection_info(self) -> None:
        sel = self._get_selected_shapes()
        parts = [t("selection_info_title", n=len(sel))]
        for s in sel:
            info = [s.shape_type]
            if s.dim_name: info.append(s.dim_name)
            if s.thickness: info.append(f"t={s.thickness}")
            parts.append("  ".join(info))
        self._sel_info.setText("\n".join(parts))

    # ── Actions ──────────────────────────────────────────────────────────────

    def _clear_all(self) -> None:
        self._shapes.clear()
        self._selected_shapes.clear()
        self._poly_points.clear()
        self._arc_points.clear()
        self._update_selection_info()
        self._canvas.update()

    def _save_profile(self) -> None:
        if not self._shapes:
            return
        if self._on_save:
            material_shapes = [s for s in self._shapes if not s.is_void]
            void_shapes = [s for s in self._shapes if s.is_void]
            fields = [s.dim_name for s in self._shapes if s.dim_name]
            # Prefer an explicitly imported image as the profile thumbnail;
            # otherwise render one from the current drawing.
            thumbnail_path = self._imported_image_path or self._generate_thumbnail()
            wkt_str = self._generate_wkt()
            meta = {k: e.text().strip() for k, e in getattr(self, "_meta", {}).items()}
            # Coerce the canonical numeric params to floats and drop blanks so
            # downstream (Costs, catalogue) reads numbers, not strings.
            for nk in ("h", "b", "tw", "tf", "seccion_cm2", "peso_lineal_kg_m",
                       "kg_por_m", "precio_kg", "precio_m", "peso_especifico"):
                raw = meta.get(nk, "")
                if raw == "":
                    meta.pop(nk, None)
                    continue
                try:
                    meta[nk] = float(raw)
                except (ValueError, TypeError):
                    meta.pop(nk, None)
            # Carry hidden/parametric keys (geometry_type, macizo) from the
            # source profile so a catalogue edit keeps producing its section.
            for ck in ("geometry_type", "macizo"):
                if ck in self._initial_meta and ck not in meta:
                    meta[ck] = self._initial_meta[ck]
            # field_defaults keyed by canonical "<token> (mm)" labels so the
            # Manage-profiles value column is populated (§21.4/§21.5).
            field_defaults: Dict[str, float] = {}
            for token in ("h", "b", "tw", "tf"):
                if token in meta:
                    label = f"{token} ({units.u_len()})"
                    field_defaults[label] = meta[token]
                    if label not in fields:
                        fields.append(label)
            manual = list(getattr(self, "_manual_sides", []))
            fields = fields + [m["name"] for m in manual if m.get("name")]
            self._on_save({
                "shapes": [s.to_dict() for s in self._shapes],
                "manual_sides": manual,
                "fields": fields if fields else ["A (mm)", "B (mm)"],
                "field_defaults": field_defaults,
                "material_count": len(material_shapes),
                "void_count": len(void_shapes),
                "thumbnail_path": thumbnail_path,
                "wkt": wkt_str,
                "meta": meta,
            })
        self.accept()

    def _generate_wkt(self) -> str:
        try:
            from nestify.geometry_engine import polygon_from_profile_shapes
            shape_dicts = [s.to_dict() for s in self._shapes]
            poly = polygon_from_profile_shapes(shape_dicts)
            if poly is not None:
                return poly.wkt
        except Exception:
            pass
        return ""

    def _generate_thumbnail(self, size: int = 128) -> str:
        # Renders the current shapes onto a transparent (RGBA) square PNG and
        # returns its temp-file path. Used for the saved-profile thumbnail, the
        # right-panel preview, and the transparent-PNG export (larger size).
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            if not self._shapes:
                return ""
            all_pts = []
            for s in self._shapes:
                all_pts.extend(s.points)
            if not all_pts:
                return ""
            xs = [p[0] for p in all_pts]; ys = [p[1] for p in all_pts]
            mn_x, mx_x = min(xs), max(xs); mn_y, mx_y = min(ys), max(ys)
            w = mx_x - mn_x or 1; h = mx_y - mn_y or 1
            pad = 8; scale = min((size-2*pad)/w, (size-2*pad)/h)
            ox = pad + ((size-2*pad)-w*scale)/2; oy = pad + ((size-2*pad)-h*scale)/2
            tx = lambda x, y: (ox+(x-mn_x)*scale, oy+(y-mn_y)*scale)
            for s in self._shapes:
                color = (200, 200, 210) if not s.is_void else (255, 255, 255)
                outline = (80, 80, 85) if not s.is_void else (220, 60, 50)
                pts = [tx(*p) for p in s.points]
                if s.shape_type == "circle" and len(pts) >= 2:
                    c = pts[0]; rx = abs(pts[1][0]-pts[0][0])
                    draw.ellipse([c[0]-rx, c[1]-rx, c[0]+rx, c[1]+rx],
                                 fill=color, outline=outline, width=2)
                elif len(pts) >= 3:
                    draw.polygon(pts, fill=color, outline=outline)
                elif len(pts) == 2:
                    draw.rectangle([pts[0], pts[1]], fill=color, outline=outline, width=2)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="profile_")
            img.save(tmp.name, "PNG")
            return tmp.name
        except Exception:
            return ""

    def _import_dxf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import DXF", "", "DXF (*.dxf);;All (*.*)",
        )
        if not path:
            return
        try:
            import ezdxf
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()
            for entity in msp:
                if entity.dxftype() == "LINE":
                    s = entity.dxf.start; e = entity.dxf.end
                    self._shapes.append(ProfileShape("line", [(s.x, s.y), (e.x, e.y)]))
                elif entity.dxftype() == "LWPOLYLINE":
                    pts = [(p[0], p[1]) for p in entity.get_points()]
                    st = "polygon" if entity.closed else "line"
                    self._shapes.append(ProfileShape(st, pts, closed=entity.closed))
                elif entity.dxftype() == "CIRCLE":
                    cx, cy = entity.dxf.center.x, entity.dxf.center.y
                    r = entity.dxf.radius
                    self._shapes.append(ProfileShape("circle", [(cx, cy), (cx+r, cy)]))
                elif entity.dxftype() == "ARC":
                    cx, cy = entity.dxf.center.x, entity.dxf.center.y
                    r = entity.dxf.radius
                    sa = math.radians(entity.dxf.start_angle)
                    ea = math.radians(entity.dxf.end_angle)
                    if ea < sa: ea += 2*math.pi
                    pts = [(cx+r*math.cos(sa+(ea-sa)*i/20),
                            cy+r*math.sin(sa+(ea-sa)*i/20)) for i in range(21)]
                    self._shapes.append(ProfileShape("line", pts))
            self._canvas.update()
        except Exception as exc:
            QMessageBox.critical(self, "DXF Import", str(exc))

    def _generate_preview(self) -> None:
        """Render the current drawing into the top profile-image preview."""
        if not self._shapes:
            self._profile_img.setText(t("profile_no_image"))
            return
        path = self._generate_thumbnail(size=300)
        pm = QPixmap(path) if path else QPixmap()
        if not pm.isNull():
            self._profile_img.setPixmap(pm.scaled(
                self._profile_img.width() - 4, self._profile_img.height() - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        else:
            self._profile_img.setText(t("profile_no_image"))

    def _import_image(self) -> None:
        """Load an external image into the profile preview (stored on save)."""
        path, _ = QFileDialog.getOpenFileName(
            self, t("profile_import_image"), "",
            "Images (*.png *.jpg *.jpeg *.bmp *.svg);;All (*.*)",
        )
        if not path:
            return
        pm = QPixmap(path)
        if pm.isNull():
            QMessageBox.warning(self, t("profile_import_image"), t("profile_no_image"))
            return
        self._imported_image_path = path
        self._profile_img.setPixmap(pm.scaled(
            self._profile_img.width() - 4, self._profile_img.height() - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def _export_dxf(self) -> None:
        """Write the current shapes to a DXF file (lines, polylines, circles)."""
        if not self._shapes:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("profile_export_dxf"), "profile.dxf", "DXF (*.dxf)",
        )
        if not path:
            return
        try:
            import ezdxf
            doc = ezdxf.new()
            msp = doc.modelspace()
            for s in self._shapes:
                pts = s.points
                if s.shape_type == "circle" and len(pts) >= 2:
                    cx, cy = pts[0]
                    r = math.hypot(pts[1][0] - cx, pts[1][1] - cy)
                    msp.add_circle((cx, cy), r)
                elif s.closed and len(pts) >= 3:
                    msp.add_lwpolyline(pts, close=True)
                elif len(pts) >= 2:
                    msp.add_lwpolyline(pts, close=False)
            doc.saveas(path)
        except Exception as exc:
            QMessageBox.critical(self, t("profile_export_dxf"), str(exc))

    def _export_png_transparent(self) -> None:
        """Export the drawing as a PNG with a transparent background."""
        if not self._shapes:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("profile_export_png"), "profile.png", "PNG (*.png)",
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        # _generate_thumbnail already paints onto a transparent RGBA canvas.
        src = self._generate_thumbnail(size=800)
        try:
            if src:
                QImage(src).save(path, "PNG")
        except Exception as exc:
            QMessageBox.critical(self, t("profile_export_png"), str(exc))

    def keyPressEvent(self, event) -> None:
        # Ctrl+Z / Ctrl+Y — undo / redo of drawing operations.
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self._undo()
                return
            if event.key() == Qt.Key.Key_Y:
                self._redo()
                return
        # Dynamic numeric entry (length / angle) while drawing a polyline.
        if self._poly_points:
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._commit_dim_length():
                    return
            if key == Qt.Key.Key_Tab:
                # Toggle the active field; '<' also jumps straight to angle.
                self._dim_field = "ang" if self._dim_field == "len" else "len"
                self._canvas.update()
                return
            txt = event.text()
            if txt == "<":
                self._dim_field = "ang"
                self._canvas.update()
                return
            if txt and (txt.isdigit() or txt in ".-"):
                if self._dim_field == "ang":
                    self._dim_angle += txt
                else:
                    self._dim_input += txt
                self._canvas.update()
                return
            if key == Qt.Key.Key_Backspace:
                if self._dim_field == "ang" and self._dim_angle:
                    self._dim_angle = self._dim_angle[:-1]
                elif self._dim_input:
                    self._dim_input = self._dim_input[:-1]
                self._canvas.update()
                return
        if event.key() == Qt.Key.Key_Escape:
            self._dim_input = ""; self._dim_angle = ""; self._dim_field = "len"
            if self._poly_points:
                self._with_undo(self._finish_poly)
            elif self._arc_points:
                self._arc_points.clear()
                self._canvas.update()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def _commit_dim_length(self) -> bool:
        """Place the next polyline vertex from the typed length and/or angle.

        Length + angle → exact polar point. Length only → current cursor
        direction. Angle only → cursor distance at that angle. Angle is degrees
        CCW from +x (screen-up). Returns True if it consumed the input."""
        if not self._poly_points or self._mouse_pos is None:
            return False
        len_txt, ang_txt = self._dim_input, self._dim_angle
        if not len_txt and not ang_txt:
            return False
        ax, ay = self._poly_points[-1]
        mx, my = self._mouse_pos
        if self._ortho_mode:
            mx, my = self._apply_ortho(mx, my, (ax, ay))
        dx, dy = mx - ax, my - ay
        cur_dist = math.hypot(dx, dy)
        try:
            length = float(len_txt) if len_txt else cur_dist
        except ValueError:
            length = cur_dist
        self._dim_input = ""; self._dim_angle = ""; self._dim_field = "len"
        if length <= 0:
            return True
        if ang_txt:
            try:
                ang = math.radians(float(ang_txt))
                nx, ny = ax + length * math.cos(ang), ay - length * math.sin(ang)
            except ValueError:
                return True
        else:
            if cur_dist < 1e-6:
                return True
            nx, ny = ax + dx / cur_dist * length, ay + dy / cur_dist * length
        self._add_poly_point(nx, ny)
        self._canvas.update()
        return True
