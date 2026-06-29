"""
nestify/ui_qt/dialogs/pdf_template_editor.py
Visual PDF template editor — WYSIWYG page layout with draggable fields.
Uses QGraphicsScene for interactive A4 page editing.
"""
from __future__ import annotations

import json
import os
import sys
import subprocess
from typing import Dict, Optional

from PySide6.QtCore import QPointF, Qt, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QPen
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QGraphicsItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsTextItem, QGraphicsView, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from nestify.i18n import t
import nestify.ui_qt.theme_qt as _th

AVAILABLE_FIELDS = [
    ("material", "{material}"),
    ("quality", "{quality}"),
    ("order_number", "{order}"),
    ("offer_number", "{offer}"),
    ("client", "{client}"),
    ("custom_fields", "{custom_fields}"),
    ("cuts_table", "{cuts_table}"),
    ("nesting_diagram", "{nesting}"),
    ("total_cost", "{total}"),
    ("total_weight", "{weight}"),
    ("bars_summary", "{bars}"),
    ("efficiency", "{efficiency}"),
    ("date", "{date}"),
    ("page_number", "{page}"),
    ("company_logo", "{logo}"),
]

PAGE_W = 420.0
PAGE_H = 594.0
MARGIN = 20.0

_FR_DOWNLOAD_URL = "https://www.fast-report.com/en/download/"


class _FieldBlock(QGraphicsRectItem):
    """Draggable field block on the PDF page."""

    def __init__(self, key: str, data: dict, editor: "PdfTemplatePane") -> None:
        x = data.get("x", MARGIN)
        y = data.get("y", MARGIN)
        w = data.get("w", 180)
        h = data.get("h", 24)
        super().__init__(x, y, w, h)

        self.key = key
        self.data = data
        self._editor = editor

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Field caption drawn inside the block: small 7pt so a long
        # "label: {placeholder}" fits within the block, inset 3px right / 2px down
        # from the block's top-left corner. Dark grey reads on the white page.
        self._label = QGraphicsTextItem(self)
        label_text = t(key) if key in [f[0] for f in AVAILABLE_FIELDS] else key
        placeholder = data.get("placeholder", f"{{{key}}}")
        self._label.setPlainText(f"{label_text}: {placeholder}")
        self._label.setFont(QFont("IBM Plex Sans", 7))
        self._label.setDefaultTextColor(QColor("#333333"))
        self._label.setPos(x + 3, y + 2)

        self._update_style(False)

    def _update_style(self, selected: bool) -> None:
        if selected:
            self.setPen(QPen(QColor(_th.ACCENT), 2))
            self.setBrush(QBrush(QColor("#FFF5F0")))
        else:
            self.setPen(QPen(QColor("#888888"), 1))
            self.setBrush(QBrush(QColor("#F8F8FA")))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_style(bool(value))
            if value:
                self._editor._selected_key = self.key
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = value
            new_x = max(0, min(pos.x(), PAGE_W - self.rect().width()))
            new_y = max(0, min(pos.y(), PAGE_H - self.rect().height()))
            if pos.x() != new_x or pos.y() != new_y:
                self.setPos(new_x, new_y)
                return QPointF(new_x, new_y)
            self.data["x"] = new_x + self.rect().x()
            self.data["y"] = new_y + self.rect().y()
        return super().itemChange(change, value)


class PdfTemplatePane(QWidget):
    """Embeddable PDF template editor pane (no dialog chrome).

    Args:
        layout_path: JSON file path where the field layout is saved/loaded.
        fastreport_pref_key: AppPreferences attribute name for the .frx path
            (``"pdf_fastreport_path"`` for nesting, ``"pdf_cuts_fastreport_path"``
            for cuts/quote).
    """

    def __init__(
        self,
        parent: QWidget,
        layout_path: str,
        fastreport_pref_key: str = "pdf_fastreport_path",
    ) -> None:
        super().__init__(parent)
        self._layout_path = layout_path
        self._fr_key = fastreport_pref_key
        self._fields: Dict[str, dict] = {}
        self._selected_key: Optional[str] = None
        self._field_items: Dict[str, _FieldBlock] = {}

        self._build()
        self._load()
        self._rebuild_scene()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        left.setContentsMargins(10, 12, 10, 12)

        title = QLabel(t("pdf_add_field").upper())
        title.setStyleSheet(f"color: {_th.ACCENT}; font-weight: bold;")
        left.addWidget(title)

        hint = QLabel(t("pdf_editor_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {_th.TEXT_SEC}; font-size: 11px;")
        left.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(220)
        btn_widget = QWidget()
        btn_layout = QVBoxLayout(btn_widget)
        btn_layout.setContentsMargins(4, 4, 4, 4)
        btn_layout.setSpacing(2)

        for field_key, placeholder in AVAILABLE_FIELDS:
            label = t(field_key) if field_key != "company_logo" else "Logo"
            btn = QPushButton(f"+ {label}")
            btn.clicked.connect(
                lambda checked=False, k=field_key, p=placeholder: self._add_field(k, p)
            )
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        scroll.setWidget(btn_widget)
        left.addWidget(scroll, 1)

        # FastReport section
        fr_title = QLabel(t("fr_template"))
        fr_title.setStyleSheet(
            f"color: {_th.ACCENT}; font-weight: bold; font-size: 11px;"
        )
        left.addWidget(fr_title)
        self._fr_path_lbl = QLabel()
        self._fr_path_lbl.setWordWrap(True)
        self._fr_path_lbl.setStyleSheet(
            f"color: {_th.TEXT_SEC}; font-size: 10px;"
        )
        left.addWidget(self._fr_path_lbl)
        fr_row = QHBoxLayout()
        fr_browse = QPushButton(t("fr_browse"))
        fr_browse.clicked.connect(self._browse_fastreport)
        fr_row.addWidget(fr_browse)
        fr_open = QPushButton(t("fr_open"))
        fr_open.clicked.connect(self._open_fastreport_designer)
        fr_row.addWidget(fr_open)
        left.addLayout(fr_row)
        self._refresh_fr_label()

        action_row = QHBoxLayout()
        remove_btn = QPushButton(t("pdf_remove_field"))
        remove_btn.clicked.connect(self._remove_selected)
        action_row.addWidget(remove_btn)
        save_btn = QPushButton(t("pdf_save_template"))
        save_btn.setProperty("variant", "accent")
        save_btn.clicked.connect(self._save)
        action_row.addWidget(save_btn)
        left.addLayout(action_row)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(240)
        layout.addWidget(left_widget)

        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._view.setBackgroundBrush(QBrush(QColor("#E0E0E4")))
        layout.addWidget(self._view, 1)

    def _rebuild_scene(self) -> None:
        self._scene.clear()
        self._field_items.clear()

        page = self._scene.addRect(
            0, 0, PAGE_W, PAGE_H,
            QPen(QColor("#888888"), 1),
            QBrush(QColor("#FFFFFF")),
        )
        page.setZValue(0)

        self._scene.addRect(
            MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN,
            QPen(QColor("#CCCCCC"), 1, Qt.PenStyle.DashLine),
        )

        header = self._scene.addText("— NESTIFY PDF —", QFont("IBM Plex Sans", 6))
        header.setDefaultTextColor(QColor("#AAAAAA"))
        header.setPos(PAGE_W / 2 - header.boundingRect().width() / 2, 4)

        footer = self._scene.addText("{page}", QFont("IBM Plex Sans", 6))
        footer.setDefaultTextColor(QColor("#AAAAAA"))
        footer.setPos(PAGE_W / 2 - footer.boundingRect().width() / 2, PAGE_H - 14)

        for key, data in self._fields.items():
            block = _FieldBlock(key, data, self)
            self._scene.addItem(block)
            self._field_items[key] = block

        self._scene.setSceneRect(-10, -10, PAGE_W + 20, PAGE_H + 20)

    def _add_field(self, key: str, placeholder: str) -> None:
        if key in self._fields:
            return
        y_offset = MARGIN + len(self._fields) * 30
        h = 24
        if key in ("cuts_table", "nesting_diagram"):
            h = 120
        elif key == "company_logo":
            h = 50

        self._fields[key] = {
            "x": MARGIN,
            "y": y_offset,
            "w": PAGE_W - 2 * MARGIN,
            "h": h,
            "placeholder": placeholder,
        }
        self._rebuild_scene()

    def _remove_selected(self) -> None:
        if self._selected_key and self._selected_key in self._fields:
            del self._fields[self._selected_key]
            self._selected_key = None
            self._rebuild_scene()

    # FastReport designer integration

    def _refresh_fr_label(self) -> None:
        from nestify import app_config
        path = getattr(app_config.get(), self._fr_key, "") or ""
        self._fr_path_lbl.setText(path or t("fr_none"))

    def _browse_fastreport(self) -> None:
        from nestify import app_config
        path, _ = QFileDialog.getOpenFileName(
            self, t("fr_template"), "", "FastReport (*.frx *.fr3);;All (*)")
        if not path:
            return
        prefs = app_config.get()
        setattr(prefs, self._fr_key, path)
        app_config.save(prefs)
        self._refresh_fr_label()

    def _open_fastreport_designer(self) -> None:
        """Open the configured .frx in the OS-associated FastReport designer.

        If the designer is not installed or the OS handler fails, offer a
        direct download link so the user can install FastReport.
        """
        from nestify import app_config
        path = getattr(app_config.get(), self._fr_key, "") or ""
        if not path:
            QMessageBox.information(self, t("fr_template"), t("fr_none"))
            return
        if not os.path.isfile(path):
            QMessageBox.warning(self, t("fr_template"), t("fr_missing"))
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            mb = QMessageBox(
                QMessageBox.Icon.Warning,
                t("fr_template"),
                f"{t('fr_install_hint')}\n\n{exc}",
                parent=self,
            )
            dl_btn = mb.addButton(t("fr_download"), QMessageBox.ButtonRole.ActionRole)
            mb.addButton(QMessageBox.StandardButton.Close)
            mb.exec()
            if mb.clickedButton() is dl_btn:
                QDesktopServices.openUrl(QUrl(_FR_DOWNLOAD_URL))

    def _save(self) -> None:
        for key, item in self._field_items.items():
            pos = item.pos()
            self._fields[key]["x"] = pos.x() + item.rect().x()
            self._fields[key]["y"] = pos.y() + item.rect().y()

        try:
            with open(self._layout_path, "w", encoding="utf-8") as fh:
                json.dump(self._fields, fh, ensure_ascii=False, indent=2)
            QMessageBox.information(
                self, t("pdf_edit_template"), t("pdf_template_saved_ok")
            )
        except OSError as exc:
            QMessageBox.critical(self, t("save_error"), str(exc))

    def _load(self) -> None:
        self._fields.clear()
        try:
            with open(self._layout_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, dict) and "x" in val and "y" in val:
                        self._fields[key] = val
                    else:
                        self._fields[key] = {
                            "x": float(val.get("x", MARGIN)),
                            "y": float(val.get("y", MARGIN)),
                            "w": 180, "h": 24,
                            "placeholder": f"{{{key}}}",
                        }
        except FileNotFoundError:
            for key, placeholder in AVAILABLE_FIELDS[:6]:
                self._add_field(key, placeholder)
        except (OSError, ValueError):
            pass


class PdfTemplateEditor(QDialog):
    """Single-template dialog wrapper (backward-compatible entry point)."""

    def __init__(self, parent: QWidget, layout_path: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("pdf_editor_title"))
        self.resize(1000, 700)
        self.setMinimumSize(800, 550)
        self.setModal(True)

        pane = PdfTemplatePane(self, layout_path)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(pane)


class EditTemplatesDialog(QDialog):
    """Multi-template editor with one tab per PDF report type."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("edit_templates"))
        self.resize(1060, 720)
        self.setMinimumSize(860, 560)
        self.setModal(True)

        from nestify import app_config
        prefs = app_config.get()
        config_dir = os.path.dirname(app_config.get_config_path())

        nesting_path = prefs.pdf_template_layout_path or os.path.join(
            config_dir, "nestify_pdf_template_layout.json"
        )
        cuts_path = prefs.pdf_cuts_layout_path or os.path.join(
            config_dir, "nestify_pdf_cuts_layout.json"
        )
        # Persist resolved paths so they survive the next open
        if not prefs.pdf_template_layout_path:
            prefs.pdf_template_layout_path = nesting_path
        if not prefs.pdf_cuts_layout_path:
            prefs.pdf_cuts_layout_path = cuts_path
        app_config.save(prefs)

        tabs = QTabWidget()
        tabs.addTab(
            PdfTemplatePane(self, nesting_path, "pdf_fastreport_path"),
            t("tpl_nesting_pdf"),
        )
        tabs.addTab(
            PdfTemplatePane(self, cuts_path, "pdf_cuts_fastreport_path"),
            t("tpl_cuts_pdf"),
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(tabs)
