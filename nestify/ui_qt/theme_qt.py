"""
nestify/ui_qt/theme_qt.py
Color palette and QSS stylesheet for the Qt UI.
Mirrors nestify/theme.py but outputs QSS instead of CTk kwargs.
"""
from __future__ import annotations

# ── Dark palette ──────────────────────────────────────────────────────────────
_DARK = dict(
    BG_APP       = "#161618",
    BG_MID       = "#1E1E20",
    BG_CARD      = "#27272A",
    BG_CANVAS    = "#111113",
    BG_HOVER     = "#333336",
    BG_GHOST_HVR = "#2A2A2D",
    ACCENT       = "#F05A22",
    ACCENT_HVR   = "#FF7043",
    ACCENT_DIM   = "#B84418",
    TEXT_PRI     = "#F2F2F2",
    TEXT_SEC     = "#8A8A8E",
    TEXT_DIM     = "#48484C",
    SUCCESS      = "#34C759",
    WARNING      = "#FF9F0A",
    DANGER       = "#FF3B30",
    DANGER_BG    = "#2A1515",
    DANGER_HVR   = "#3D1818",
    DANGER_BORDER= "#6B2020",
    SUCCESS_BG   = "#1A2E22",
    BORDER       = "#3A3A3C",
    BORDER_LIT   = "#4A4A4E",
)

# ── Light palette ─────────────────────────────────────────────────────────────
_LIGHT = dict(
    BG_APP       = "#F5F5F7",
    BG_MID       = "#EBEBED",
    BG_CARD      = "#FFFFFF",
    BG_CANVAS    = "#E8E8EA",
    BG_HOVER     = "#E0E0E3",
    BG_GHOST_HVR = "#ECECEF",
    ACCENT       = "#E8521A",
    ACCENT_HVR   = "#F06030",
    ACCENT_DIM   = "#A03A10",
    TEXT_PRI     = "#1C1C1E",
    TEXT_SEC     = "#636366",
    TEXT_DIM     = "#86868B",
    SUCCESS      = "#28A745",
    WARNING      = "#E08800",
    DANGER       = "#DC3545",
    DANGER_BG    = "#FFF0F0",
    DANGER_HVR   = "#FFE0E0",
    DANGER_BORDER= "#FFAAAA",
    SUCCESS_BG   = "#F0FFF4",
    BORDER       = "#D1D1D6",
    BORDER_LIT   = "#C0C0C6",
)

# Active palette (module-level, updated by apply_theme)
_palette: dict = dict(_DARK)

# Expose constants at module level for direct import
BG_APP = _DARK["BG_APP"]
BG_MID = _DARK["BG_MID"]
BG_CARD = _DARK["BG_CARD"]
BG_CANVAS = _DARK["BG_CANVAS"]
BG_HOVER = _DARK["BG_HOVER"]
BG_GHOST_HVR = _DARK["BG_GHOST_HVR"]
ACCENT = _DARK["ACCENT"]
ACCENT_HVR = _DARK["ACCENT_HVR"]
ACCENT_DIM = _DARK["ACCENT_DIM"]
TEXT_PRI = _DARK["TEXT_PRI"]
TEXT_SEC = _DARK["TEXT_SEC"]
TEXT_DIM = _DARK["TEXT_DIM"]
SUCCESS = _DARK["SUCCESS"]
WARNING = _DARK["WARNING"]
DANGER = _DARK["DANGER"]
DANGER_BG = _DARK["DANGER_BG"]
DANGER_HVR = _DARK["DANGER_HVR"]
DANGER_BORDER = _DARK["DANGER_BORDER"]
SUCCESS_BG = _DARK["SUCCESS_BG"]
BORDER = _DARK["BORDER"]
BORDER_LIT = _DARK["BORDER_LIT"]

# Selection colors for nesting canvas
COLOR_SELECT_SINGLE = "#00FFFF"
COLOR_SELECT_MULTI  = "#FF00FF"
COLOR_HIGHLIGHT     = "#FFE500"


def _c(key: str) -> str:
    return _palette[key]


def _contrast_color(bg_hex: str) -> str:
    """Return '#000000' or '#FFFFFF', whichever passes WCAG AA contrast on bg_hex."""
    h = bg_hex.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    L = 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
    # Threshold 0.179 is the crossover point where black/white ratios are equal.
    return "#000000" if L > 0.179 else "#FFFFFF"


def build_palette(mode: str = "dark"):
    """Build a QPalette mapping our design tokens to Qt semantic color roles."""
    from PySide6.QtGui import QPalette, QColor
    pal = dict(_LIGHT if mode == "light" else _DARK)
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(pal["BG_APP"]))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(pal["TEXT_PRI"]))
    p.setColor(QPalette.ColorRole.Base,            QColor(pal["BG_CARD"]))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(pal["BG_MID"]))
    p.setColor(QPalette.ColorRole.Text,            QColor(pal["TEXT_PRI"]))
    p.setColor(QPalette.ColorRole.BrightText,      QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.Button,          QColor(pal["BG_MID"]))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(pal["TEXT_PRI"]))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(pal["ACCENT"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(_contrast_color(pal["ACCENT"])))
    p.setColor(QPalette.ColorRole.Link,            QColor(pal["ACCENT"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(pal["TEXT_DIM"]))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(pal["BG_CARD"]))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(pal["TEXT_PRI"]))
    return p


def apply_theme(mode: str) -> None:
    """Switch active palette to 'dark' or 'light'. Updates module-level constants."""
    global _palette
    global BG_APP, BG_MID, BG_CARD, BG_CANVAS, BG_HOVER, BG_GHOST_HVR
    global ACCENT, ACCENT_HVR, ACCENT_DIM, TEXT_PRI, TEXT_SEC, TEXT_DIM
    global SUCCESS, WARNING, DANGER, DANGER_BG, DANGER_HVR, DANGER_BORDER
    global SUCCESS_BG, BORDER, BORDER_LIT

    _palette = dict(_LIGHT if mode == "light" else _DARK)

    BG_APP = _palette["BG_APP"]
    BG_MID = _palette["BG_MID"]
    BG_CARD = _palette["BG_CARD"]
    BG_CANVAS = _palette["BG_CANVAS"]
    BG_HOVER = _palette["BG_HOVER"]
    BG_GHOST_HVR = _palette["BG_GHOST_HVR"]
    ACCENT = _palette["ACCENT"]
    ACCENT_HVR = _palette["ACCENT_HVR"]
    ACCENT_DIM = _palette["ACCENT_DIM"]
    TEXT_PRI = _palette["TEXT_PRI"]
    TEXT_SEC = _palette["TEXT_SEC"]
    TEXT_DIM = _palette["TEXT_DIM"]
    SUCCESS = _palette["SUCCESS"]
    WARNING = _palette["WARNING"]
    DANGER = _palette["DANGER"]
    DANGER_BG = _palette["DANGER_BG"]
    DANGER_HVR = _palette["DANGER_HVR"]
    DANGER_BORDER = _palette["DANGER_BORDER"]
    SUCCESS_BG = _palette["SUCCESS_BG"]
    BORDER = _palette["BORDER"]
    BORDER_LIT = _palette["BORDER_LIT"]


def build_stylesheet(mode: str = "dark", font_family: str = "IBM Plex Sans",
                     mono_family: str = "DejaVu Sans Mono",
                     font_size_offset: int = 0) -> str:
    """Return full QSS stylesheet for the given mode."""
    import os
    import tempfile
    apply_theme(mode)
    p = _palette
    accent_fg = _contrast_color(p["ACCENT"])
    # Clamp to >=1: a sufficiently negative saved offset would otherwise yield a
    # zero/negative QSS font-size, which Qt rejects with
    # "QFont::setPointSize: Point size <= 0 (-1)".
    base_size = max(1, 12 + font_size_offset)
    small_size = max(1, 10 + font_size_offset)
    caption_size = max(1, 9 + font_size_offset)

    # Write theme-colored chevron SVGs to temp files so QSS can reference them.
    _chevron_tpl = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
        ' width="12" height="12" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round"'
        ' stroke-linejoin="round"><polyline points="{pts}"/></svg>'
    )
    _tmp = tempfile.gettempdir()
    _chev_down = os.path.join(_tmp, "nestify_chevron_down.svg")
    _chev_up   = os.path.join(_tmp, "nestify_chevron_up.svg")
    try:
        with open(_chev_down, "w") as _f:
            _f.write(_chevron_tpl.format(color=p["TEXT_SEC"], pts="6 9 12 15 18 9"))
        with open(_chev_up, "w") as _f:
            _f.write(_chevron_tpl.format(color=p["TEXT_SEC"], pts="18 15 12 9 6 15"))
    except OSError:
        _chev_down = _chev_up = ""
    _chev_down_url = _chev_down.replace("\\", "/")
    _chev_up_url   = _chev_up.replace("\\", "/")

    return f"""
/* ── Base ── */
QWidget {{
    background-color: {p["BG_APP"]};
    color: {p["TEXT_PRI"]};
    font-family: "{font_family}";
    font-size: {base_size}px;
    border: none;
    outline: none;
}}

QMainWindow {{
    background-color: {p["BG_APP"]};
}}

/* ── Frames / Panels ── */
QFrame {{
    background-color: transparent;
}}
QFrame[role="card"] {{
    background-color: {p["BG_CARD"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 8px;
}}
QFrame[role="card-bar"] {{
    background-color: {p["BG_CARD"]};
    border: none;
    border-bottom: 1px solid {p["BORDER"]};
    border-radius: 0px;
}}
QFrame[role="mid"] {{
    background-color: {p["BG_MID"]};
}}
QFrame[role="toolbar"] {{
    background-color: {p["BG_MID"]};
    border-bottom: 1px solid {p["BORDER"]};
}}
QFrame[role="separator"] {{
    background-color: {p["BORDER"]};
    max-width: 1px;
    min-width: 1px;
}}
QFrame[role="transparent"], QWidget[role="transparent"] {{
    background-color: transparent;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: {base_size}px;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {p["BG_HOVER"]};
    border-color: {p["BORDER_LIT"]};
}}
QPushButton:pressed {{
    background-color: {p["BG_MID"]};
}}
QPushButton:disabled {{
    color: {p["TEXT_DIM"]};
    border-color: {p["BORDER"]};
    background-color: {p["BG_MID"]};
}}

QPushButton[variant="accent"] {{
    background-color: {p["ACCENT"]};
    color: #FFFFFF;
    border: none;
    font-weight: bold;
    min-height: 20px;
    border-radius: 6px;
}}
QPushButton[variant="accent"]:hover {{
    background-color: {p["ACCENT_HVR"]};
}}
QPushButton[variant="accent"]:pressed {{
    background-color: {p["ACCENT_DIM"]};
}}
QPushButton[variant="accent"]:disabled {{
    background-color: {p["ACCENT_DIM"]};
    color: #FFFFFF;
    opacity: 0.5;
}}

QPushButton[variant="danger"] {{
    background-color: {p["DANGER_BG"]};
    color: {p["DANGER"]};
    border: 1px solid {p["DANGER_BORDER"]};
    border-radius: 4px;
    font-size: {caption_size}px;
    min-height: 20px;
}}
QPushButton[variant="danger"]:hover {{
    background-color: {p["DANGER_HVR"]};
}}

QPushButton[variant="ghost"] {{
    background-color: transparent;
    color: {p["TEXT_SEC"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 4px;
    font-size: {small_size}px;
    min-height: 20px;
}}
QPushButton[variant="ghost"]:hover {{
    background-color: {p["BG_GHOST_HVR"]};
    color: {p["TEXT_PRI"]};
}}

QPushButton[variant="icon"] {{
    background-color: {p["BG_MID"]};
    color: {p["TEXT_SEC"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 4px;
    min-width: 28px;
    min-height: 28px;
    padding: 0px;
    font-size: 16px;
}}
QPushButton[variant="icon"]:hover {{
    background-color: {p["ACCENT"]};
    color: {accent_fg};
    border-color: {p["ACCENT"]};
}}

/* ── Line Edits ── */
QLineEdit {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: {base_size}px;
    min-height: 20px;
    selection-background-color: {p["ACCENT"]};
    selection-color: {accent_fg};
}}
QLineEdit:focus {{
    border-color: {p["ACCENT"]};
}}
QLineEdit:disabled {{
    color: {p["TEXT_DIM"]};
    background-color: {p["BG_MID"]};
}}
QLineEdit[mono="true"] {{
    font-family: "{mono_family}";
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 20px;
    font-size: {base_size}px;
}}
QComboBox:hover {{
    border-color: {p["BORDER_LIT"]};
}}
QComboBox:focus {{
    border-color: {p["ACCENT"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    image: url({_chev_down_url});
    width: 12px;
    height: 12px;
}}
QComboBox::down-arrow:on {{
    image: url({_chev_up_url});
    width: 12px;
    height: 12px;
}}
/* Generic item views (QCompleter popup, bare list/tree views) so they
   follow the theme in light mode instead of falling back to a dark default. */
QAbstractItemView {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 4px;
    selection-background-color: {p["ACCENT"]};
    selection-color: {accent_fg};
    outline: none;
}}
QAbstractItemView::item {{
    min-height: 24px;
    padding: 2px 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 4px;
    selection-background-color: {p["ACCENT"]};
    selection-color: {accent_fg};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 2px 8px;
}}

/* ── CheckBox ── */
QCheckBox {{
    color: {p["TEXT_PRI"]};
    spacing: 6px;
    font-size: {small_size}px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p["BORDER"]};
    border-radius: 3px;
    background-color: {p["BG_CARD"]};
}}
QCheckBox::indicator:checked {{
    background-color: {p["ACCENT"]};
    border-color: {p["ACCENT"]};
    image: none;
}}
QCheckBox::indicator:hover {{
    border-color: {p["ACCENT"]};
}}

/* ── Tab Widget ── */
QTabWidget::pane {{
    border: none;
    background-color: {p["BG_APP"]};
}}
QTabWidget::tab-bar {{
    alignment: left;
}}
QTabBar {{
    background-color: {p["BG_MID"]};
    border-bottom: 1px solid {p["BORDER"]};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {p["TEXT_SEC"]};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: {base_size}px;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    color: {p["ACCENT"]};
    border-bottom: 2px solid {p["ACCENT"]};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    color: {p["TEXT_PRI"]};
    background-color: {p["BG_HOVER"]};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {p["BORDER"]};
}}
QSplitter::handle:horizontal {{
    width: 6px;
}}
QSplitter::handle:vertical {{
    height: 6px;
}}
QSplitter::handle:hover {{
    background-color: {p["ACCENT"]};
}}

/* ── Scroll Bars ── */
QScrollBar:vertical {{
    background-color: {p["BG_MID"]};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {p["BORDER_LIT"]};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p["ACCENT"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: {p["BG_MID"]};
    height: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {p["BORDER_LIT"]};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {p["ACCENT"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Menu Bar ── */
QMenuBar {{
    background-color: {p["BG_MID"]};
    color: {p["TEXT_PRI"]};
    border-bottom: 1px solid {p["BORDER"]};
    padding: 2px 4px;
    font-size: {base_size}px;
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {p["BG_HOVER"]};
    color: {p["TEXT_PRI"]};
}}
QMenuBar::item:pressed {{
    background-color: {p["ACCENT"]};
    color: {accent_fg};
}}

/* ── Menus ── */
QMenu {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 6px;
    padding: 4px;
    font-size: {base_size}px;
}}
QMenu::item {{
    padding: 5px 24px 5px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {p["ACCENT"]};
    color: {accent_fg};
}}
QMenu::item:disabled {{
    color: {p["TEXT_DIM"]};
}}
QMenu::separator {{
    height: 1px;
    background-color: {p["BORDER"]};
    margin: 4px 8px;
}}
QMenu::indicator {{
    width: 16px;
    height: 16px;
}}
QMenu::indicator:checked {{
    color: {p["ACCENT"]};
}}

/* ── Scroll Area ── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ── Dialog ── */
QDialog {{
    background-color: {p["BG_MID"]};
}}

/* ── Message Box ── */
QMessageBox {{
    background-color: {p["BG_CARD"]};
}}
QMessageBox QLabel {{
    color: {p["TEXT_PRI"]};
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: {caption_size}px;
}}

/* ── Table Widget ── */
QTableWidget {{
    background-color: {p["BG_CARD"]};
    gridline-color: {p["BORDER"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 4px;
    selection-background-color: {p["ACCENT"]};
    selection-color: {accent_fg};
    font-size: {small_size}px;
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {p["ACCENT"]};
    color: {accent_fg};
}}
QHeaderView::section {{
    background-color: {p["BG_MID"]};
    color: {p["TEXT_SEC"]};
    border: none;
    border-bottom: 1px solid {p["BORDER"]};
    padding: 4px 8px;
    font-size: {caption_size}px;
}}

/* ── Labels ── */
QLabel[role="title"] {{
    color: {p["ACCENT"]};
    font-weight: bold;
    font-size: {base_size}px;
}}
QLabel[role="section"] {{
    color: {p["ACCENT"]};
    font-size: {caption_size}px;
    font-weight: bold;
}}
QLabel[role="field"] {{
    color: {p["TEXT_SEC"]};
    font-size: {small_size}px;
}}
QLabel[role="dim"] {{
    color: {p["TEXT_DIM"]};
    font-size: {small_size}px;
}}
QLabel[role="num"] {{
    font-family: "{mono_family}";
    font-size: 11px;
}}

/* ── GroupBox ── */
QGroupBox {{
    color: {p["TEXT_SEC"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 4px;
    font-size: {small_size}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {p["TEXT_SEC"]};
}}

/* ── Spin Box ── */
QDoubleSpinBox, QSpinBox {{
    background-color: {p["BG_CARD"]};
    color: {p["TEXT_PRI"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 6px;
    padding: 3px 8px;
    min-height: 22px;
    font-family: "{mono_family}";
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {p["ACCENT"]};
}}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    width: 16px;
    border: none;
    background-color: {p["BG_MID"]};
}}

/* ── Dialog Button Box ── */
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: {p["BG_MID"]};
    color: {p["TEXT_SEC"]};
    border-top: 1px solid {p["BORDER"]};
    font-size: {caption_size}px;
}}
"""
