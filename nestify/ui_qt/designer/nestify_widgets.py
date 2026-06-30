"""
nestify/ui_qt/designer/nestify_widgets.py
PySide6 Designer plugin registration for all Nestify custom widgets.

Usage:
    PYSIDE_DESIGNER_PLUGINS=/path/to/nestify/ui_qt/designer pyside6-designer
    # or use the bundled launcher:
    python -m nestify.ui_qt.designer.launch

Each widget is registered with QPyDesignerCustomWidgetCollection so it
appears in Designer's widget palette under the "Nestify" group.
Widgets that require positional constructor args are wrapped with a
no-arg subclass suitable for Designer instantiation.
"""
from __future__ import annotations

from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection

from nestify.ui_qt.widgets.pill_switch import PillSwitch
from nestify.ui_qt.widgets.corte_row import CorteRow, ShapePreview
from nestify.ui_qt.widgets.profile_tile import ProfileTile
from nestify.ui_qt.widgets.material_autocomplete import SimpleAutocomplete, MaterialAutocomplete
from nestify.ui_qt.widgets.material_subtabs import MaterialSubTabs
from nestify.ui_qt.tab_jobs import TabJobsExplorer


# ── Designer-safe wrapper classes ─────────────────────────────────────────────
# These exist solely to provide a no-arg (parent-only) constructor.
# Promoted widgets in .ui files use the original class name.

class CorteRowDesigner(CorteRow):
    """CorteRow with default numero=1 for Qt Designer instantiation."""
    def __init__(self, parent=None):
        super().__init__(numero=1, parent=parent)


class ProfileTileDesigner(ProfileTile):
    """ProfileTile with placeholder values for Qt Designer instantiation."""
    def __init__(self, parent=None):
        super().__init__(
            profile_key="rect",
            profile_type="rect",
            display_name="Profile",
            parent=parent,
        )


# ── Registration ──────────────────────────────────────────────────────────────

def _xml(cls_name: str, w: int, h: int) -> str:
    return (
        f'<ui language="c++">'
        f'<widget class="{cls_name}" name="{cls_name[0].lower()}{cls_name[1:]}">'
        f"<property name=\"geometry\"><rect>"
        f"<x>0</x><y>0</y><width>{w}</width><height>{h}</height>"
        f"</rect></property>"
        f"</widget></ui>"
    )


_REGISTRATIONS = [
    (PillSwitch, dict(
        tool_tip="Animated pill toggle switch (emits toggled(str))",
        group="Nestify",
        xml=_xml("PillSwitch", 120, 28),
    )),
    (CorteRowDesigner, dict(
        tool_tip="Cut list row: description, length, qty, bevels, shape preview",
        group="Nestify",
        xml=_xml("CorteRowDesigner", 640, 36),
    )),
    (ShapePreview, dict(
        tool_tip="Bevel shape preview widget (64×32)",
        group="Nestify",
        xml=_xml("ShapePreview", 64, 32),
    )),
    (ProfileTileDesigner, dict(
        tool_tip="Profile selection tile (72×90) with vector shape or image",
        group="Nestify",
        xml=_xml("ProfileTileDesigner", 72, 90),
    )),
    (SimpleAutocomplete, dict(
        tool_tip="QLineEdit with debounced autocomplete dropdown",
        group="Nestify",
        xml=_xml("SimpleAutocomplete", 200, 28),
    )),
    (MaterialAutocomplete, dict(
        tool_tip="Material + quality autocomplete pair with picker button",
        group="Nestify",
        xml=_xml("MaterialAutocomplete", 400, 28),
    )),
    (MaterialSubTabs, dict(
        tool_tip="Dynamic material sub-tab bar (add / rename / remove tabs)",
        group="Nestify",
        xml=_xml("MaterialSubTabs", 400, 34),
    )),
    (TabJobsExplorer, dict(
        tool_tip="Jobs Explorer tab (browse, open, delete saved jobs)",
        group="Nestify Tabs",
        xml=_xml("TabJobsExplorer", 800, 600),
    )),
]

for _cls, _kwargs in _REGISTRATIONS:
    QPyDesignerCustomWidgetCollection.registerCustomWidget(_cls, **_kwargs)
