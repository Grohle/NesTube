"""
nestube/ui_qt/dialogs/nesting_selector_dialog.py
Modal dialog to choose which material nestings to include in a PDF/DXF export.

Each material context with nesting data gets a checkbox row showing its display
name and a brief summary (bar count · piece count). The active nesting uses the
live in-memory bars so unsaved placements are included.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from nestube.i18n import t
from nestube.models import AppState
import nestube.ui_qt.theme_qt as _th


class NestingSelectorDialog(QDialog):
    """Let the user pick which nestings to include in the current export.

    Parameters
    ----------
    state:
        Application state — provides ``material_contexts``.
    active_index:
        Index of the currently active material sub-tab.
    active_bars:
        Live placed-piece bars for the active material (list of lists of
        PlacedPiece). May differ from the stored ``nesting_layout`` if the user
        has placed pieces since the last save.
    active_bar_lengths:
        Bar lengths for the active material.
    active_sh:
        Section height (mm) for the active material.
    """

    def __init__(
        self,
        state: AppState,
        active_index: int,
        active_bars: List[List[Any]],
        active_bar_lengths: List[float],
        active_sh: float,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("select_nestings_title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        self._state = state
        self._active_index = active_index
        self._active_bars = active_bars
        self._active_bar_lengths = active_bar_lengths
        self._active_sh = active_sh

        # Build row data — only contexts that have nesting data.
        self._rows: List[Tuple[int, str, int, int]] = []  # (ctx_idx, name, n_bars, n_pieces)
        contexts = state.material_contexts or []
        for i, ctx in enumerate(contexts):
            if i == active_index:
                n_bars = len([b for b in active_bars if b])
                n_pieces = sum(len(b) for b in active_bars if b)
            else:
                # Count via effective_barras (manual layout OR quick bin-packing)
                # — the SAME source the PDF export uses to decide a context "has
                # data". Counting raw nesting_layout missed contexts that were
                # just quick-packed (barras_necesarias only), so a valid material
                # was silently absent from the selector and the export.
                from nestube.context_sync import effective_barras
                barras = effective_barras(ctx)
                n_bars = len([b for b in barras if b])
                n_pieces = sum(len(b) for b in barras if b)
            if n_bars == 0 and n_pieces == 0:
                continue
            from nestube.naming import context_tab_label
            name = context_tab_label(ctx, i)
            self._rows.append((i, name, n_bars, n_pieces))

        self._checkboxes: List[QCheckBox] = []

        self._build_ui()
        self._apply_styles()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Description
        desc = QLabel(t("select_nestings_desc"))
        desc.setWordWrap(True)
        desc.setObjectName("desc_lbl")
        root.addWidget(desc)

        # Select-all row
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        self._btn_all = QPushButton(t("select_all"))
        self._btn_all.setObjectName("link_btn")
        self._btn_all.setFlat(True)
        self._btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_all.clicked.connect(self._select_all)
        ctrl_row.addWidget(self._btn_all)
        ctrl_row.addStretch()
        root.addLayout(ctrl_row)

        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(280)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(6)

        if self._rows:
            for ctx_idx, name, n_bars, n_pieces in self._rows:
                row_widget = QWidget()
                row_widget.setObjectName("row_widget")
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(4, 2, 4, 2)
                row_layout.setSpacing(8)

                cb = QCheckBox(name)
                cb.setChecked(True)
                cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                self._checkboxes.append(cb)

                stats = QLabel(f"{n_bars} {t('bars')} · {n_pieces} {t('pieces')}")
                stats.setObjectName("stats_lbl")
                stats.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                row_layout.addWidget(cb)
                row_layout.addWidget(stats)
                inner_layout.addWidget(row_widget)
        else:
            empty = QLabel(t("no_nestings_available"))
            empty.setObjectName("empty_lbl")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner_layout.addWidget(empty)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # Button box
        btn_box = QDialogButtonBox()
        self._export_btn = btn_box.addButton(
            t("export_selected"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        cancel_btn = btn_box.addButton(
            t("cancel"), QDialogButtonBox.ButtonRole.RejectRole
        )
        self._export_btn.setEnabled(bool(self._rows))
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

        # Keep export button in sync with checkbox state
        for cb in self._checkboxes:
            cb.toggled.connect(self._update_export_btn)

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {_th.BG_CARD};
            }}
            QLabel {{
                background-color: transparent;
                color: {_th.TEXT_PRI};
            }}
            QLabel#desc_lbl {{
                color: {_th.TEXT_DIM};
                font-size: 12px;
            }}
            QLabel#stats_lbl {{
                color: {_th.TEXT_DIM};
                font-size: 11px;
            }}
            QLabel#empty_lbl {{
                color: {_th.TEXT_DIM};
            }}
            QCheckBox {{
                background-color: transparent;
                color: {_th.TEXT_PRI};
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
            }}
            QPushButton#link_btn {{
                background: transparent;
                color: {_th.ACCENT};
                border: none;
                font-size: 12px;
                padding: 0;
            }}
            QPushButton#link_btn:hover {{
                color: {_th.ACCENT_HVR};
                text-decoration: underline;
            }}
            QWidget#row_widget {{
                background-color: {_th.BG_MID};
                border-radius: 4px;
            }}
            QScrollArea {{
                background-color: {_th.BG_MID};
                border: 1px solid {_th.BORDER};
                border-radius: 4px;
            }}
            QWidget {{
                background-color: transparent;
            }}
        """)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _select_all(self) -> None:
        any_unchecked = any(not cb.isChecked() for cb in self._checkboxes)
        for cb in self._checkboxes:
            cb.setChecked(any_unchecked)
        self._btn_all.setText(t("select_none") if any_unchecked else t("select_all"))

    def _update_export_btn(self) -> None:
        has_selection = any(cb.isChecked() for cb in self._checkboxes)
        self._export_btn.setEnabled(has_selection)
        all_checked = all(cb.isChecked() for cb in self._checkboxes)
        none_checked = not any(cb.isChecked() for cb in self._checkboxes)
        if none_checked or all_checked:
            self._btn_all.setText(t("select_all"))
        else:
            self._btn_all.setText(t("select_all"))

    # ── Result ────────────────────────────────────────────────────────────────

    def selected_context_indices(self) -> List[int]:
        """Return the material-context indices of the checked rows."""
        return [ctx_idx for cb, (ctx_idx, *_) in zip(self._checkboxes, self._rows) if cb.isChecked()]

    def selected_nestings(self) -> List[Dict[str, Any]]:
        """Return nesting dicts for checked rows, ready for multi-nesting export.

        Each dict has keys ``name``, ``bars``, ``bar_lengths``, ``section_height``
        and ``profile_name``. For the active context the live bars are used;
        for others they are rebuilt from the stored serialised layout.
        """
        if not self._rows:
            return []
        from nestube.nesting_export import build_context_export_data, context_section_height
        from nestube.bevel_geom import profile_section_height as _psh

        contexts = self._state.material_contexts or []
        result: List[Dict[str, Any]] = []

        for cb, (ctx_idx, name, _nb, _np) in zip(self._checkboxes, self._rows):
            if not cb.isChecked():
                continue
            if ctx_idx == self._active_index:
                bars = self._active_bars
                bar_lengths = self._active_bar_lengths
                sh = self._active_sh
                pname = name
            else:
                ctx = contexts[ctx_idx]
                bars, bar_lengths, sh, pname = build_context_export_data(ctx)
            result.append({
                "name": name,
                "bars": bars,
                "bar_lengths": bar_lengths,
                "section_height": sh,
                "profile_name": pname,
            })
        return result
