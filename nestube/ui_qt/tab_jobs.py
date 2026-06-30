"""
nestube/ui_qt/tab_jobs.py
Jobs Explorer tab — browse, open, and delete saved jobs from SQLite.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QMessageBox,
    QPushButton, QSizePolicy, QTableWidgetItem, QVBoxLayout, QWidget,
)

import logging

from PySide6.QtCore import QSize
from nestube.i18n import t
import nestube.ui_qt.theme_qt as _th
from nestube.ui_qt.icons import themed_icon

_log = logging.getLogger(__name__)
from nestube.ui_qt.forms.ui_tab_jobs import Ui_TabJobsExplorer


# ── Job tile widget ───────────────────────────────────────────────────────────

class _JobTile(QWidget):
    """Single job entry in the list panel."""

    def __init__(self, job: dict, selected: bool, parent=None) -> None:
        super().__init__(parent)
        self._job = job
        self._selected = selected
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(52)   # row height fits the name + sub lines
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)   # inner padding
        layout.setSpacing(2)

        # Line 1: job name (or description / "Job #id" fallback). ACCENT + bold
        # when this tile is the selected one, otherwise normal primary text.
        name = job.get("name") or job.get("description") or f"Job #{job['id']}"
        self._name_lbl = QLabel(name)
        self._name_lbl.setStyleSheet(f"color:{_th.ACCENT if selected else _th.TEXT_PRI}; font-weight:{'bold' if selected else 'normal'};")
        layout.addWidget(self._name_lbl)

        # Line 2: "<client>  <updated date>" in 9px dim text (omitted if empty).
        client = job.get("client", "")
        updated = (job.get("updated_at") or job.get("created_at") or "")[:16]
        sub = f"{client}  {updated}".strip()
        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:9px;")
            layout.addWidget(sub_lbl)

    def _apply_style(self) -> None:
        # Card-like tile, 6px rounded. Selected → BG_CARD fill + ACCENT border;
        # unselected → transparent + BORDER, with a BG_CARD hover in both cases.
        # The "_JobTile { }" selector scopes the QSS to this widget type only.
        if self._selected:
            self.setStyleSheet(
                f"_JobTile {{ background:{_th.BG_CARD}; border:1px solid {_th.ACCENT}; border-radius:6px; }}"
                f"_JobTile:hover {{ background:{_th.BG_CARD}; }}"
            )
        else:
            self.setStyleSheet(
                f"_JobTile {{ background:transparent; border:1px solid {_th.BORDER}; border-radius:6px; }}"
                f"_JobTile:hover {{ background:{_th.BG_CARD}; }}"
            )

    def job_id(self) -> int:
        return self._job["id"]


# ── Main tab ──────────────────────────────────────────────────────────────────

class TabJobsExplorer(QWidget):
    """Left-most tab: browse, reopen, and delete saved jobs."""

    _SEARCH_FIELDS = [
        ("name",     lambda: t("jobs_search_name")),
        ("client",   lambda: t("jobs_search_client")),
        ("profile",  lambda: t("profile_tube_label")),
        ("material", lambda: t("jobs_search_material")),
        ("order",    lambda: t("jobs_search_order")),
        ("offer",    lambda: t("jobs_search_offer")),
    ]
    _SEARCH_FIELD_MAP = {
        "name":     "name",
        "client":   "client",
        "profile":  "profile_name",   # json_extract virtual column from list_jobs_summary
        "material": "mat_name",       # json_extract virtual column from list_jobs_summary
        "order":    "order_ref",
        "offer":    "offer",
    }

    def __init__(self, app_ref, parent=None) -> None:
        super().__init__(parent)
        self._app = app_ref
        self._selected_job_id: Optional[int] = None
        self._jobs: list[dict] = []
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self._run_search)

        # ── Set up UI from .ui form ──────────────────────────────────────
        self.ui = Ui_TabJobsExplorer()
        self.ui.setupUi(self)

        # Fix 4: Move detail_card before the spacer so it sits at the TOP of
        # the right panel when visible (default layout had spacer before card,
        # pushing the card to the bottom of the panel).
        self.ui.detail_outer_layout.removeWidget(self.ui.detail_card)
        self.ui.detail_outer_layout.insertWidget(0, self.ui.detail_card)

        # Fix 6: Full-width "Create new job" accent button above the search bar.
        self._create_job_btn = QPushButton()
        self._create_job_btn.setProperty("variant", "accent")
        self._create_job_btn.setFixedHeight(30)
        self._create_job_btn.clicked.connect(self._new_job)
        self.ui.list_panel_layout.insertWidget(1, self._create_job_btn)

        # §27: "New Job" (ui.new_btn) duplicated "Create new job" — remove the
        # old one so there is a single, unambiguous way to start a job.
        self.ui.new_btn.hide()

        # ── Convenience aliases ──────────────────────────────────────────
        self._list_panel = self.ui.list_panel
        self._search_field = self.ui.search_field
        self._search_entry = self.ui.search_entry
        self._list_container = self.ui.list_container
        self._list_layout = self.ui.list_layout
        self._detail_placeholder = self.ui.detail_placeholder
        self._detail_card = self.ui.detail_card
        self._detail_name_lbl = self.ui.detail_name_lbl
        self._detail_date_lbl = self.ui.detail_date_lbl
        self._detail_client_lbl = self.ui.detail_client_lbl
        self._detail_offer_lbl = self.ui.detail_offer_lbl
        self._detail_order_lbl = self.ui.detail_order_lbl
        self._detail_desc_lbl = self.ui.detail_desc_lbl
        self._pieces_table = self.ui.pieces_table

        # Stock-used info label — inserted between pieces_table and btn_row.
        self._stock_info_lbl = QLabel("")
        self._stock_info_lbl.setWordWrap(True)
        self._stock_info_lbl.setVisible(False)
        # detail_card_layout: 0=hdr, 1=meta, 2=pieces_table, 3=btn_row
        self.ui.detail_card_layout.insertWidget(3, self._stock_info_lbl)

        # Retales-generated info label — inserted right after stock_info_lbl.
        self._retal_info_lbl = QLabel("")
        self._retal_info_lbl.setWordWrap(True)
        self._retal_info_lbl.setVisible(False)
        self.ui.detail_card_layout.insertWidget(4, self._retal_info_lbl)

        # ── Trailing stretch in the job list layout ──────────────────────
        self._list_layout.addStretch()

        # ── Splitter initial sizes ───────────────────────────────────────
        self.ui.splitter.setSizes([260, 600])
        self.ui.splitter.setStretchFactor(0, 0)
        self.ui.splitter.setStretchFactor(1, 1)

        # ── Style / property fixups not expressible in .ui ───────────────
        self._list_panel.setStyleSheet(f"background:{_th.BG_CARD};")
        self.ui.header.setStyleSheet("#header{background:transparent;}")
        self.ui.search_widget.setStyleSheet("#search_widget{background:transparent;}")

        self.ui.title.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold; font-size:13px;")

        self.ui.new_btn.setProperty("variant", "accent")
        self.ui.new_btn.style().polish(self.ui.new_btn)

        self._detail_placeholder.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:11px;")

        self._detail_card.setProperty("role", "card")
        self._detail_card.style().polish(self._detail_card)

        self._detail_name_lbl.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold; font-size:13px;")
        # The job name is the auto-generated job number and is never editable —
        # no override is allowed anywhere in the app.
        self._detail_name_lbl.setReadOnly(True)
        self._detail_name_lbl.setToolTip(t("job_name_auto_tip"))
        self._detail_date_lbl.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:9px;")

        # Meta key labels
        self.ui.key_client.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        self.ui.key_offer.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        self.ui.key_order.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        self.ui.key_desc.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")

        # Meta value labels
        self._detail_client_lbl.setStyleSheet(f"color:{_th.TEXT_PRI}; font-size:11px;")
        self._detail_offer_lbl.setStyleSheet(f"color:{_th.TEXT_PRI}; font-size:11px;")
        self._detail_order_lbl.setStyleSheet(f"color:{_th.TEXT_PRI}; font-size:11px;")
        self._detail_desc_lbl.setStyleSheet(f"color:{_th.TEXT_PRI}; font-size:11px;")

        self._stock_info_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        self._retal_info_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")

        # Meta grid column stretches
        self.ui.meta_grid.setColumnStretch(1, 1)
        self.ui.meta_grid.setColumnStretch(3, 1)

        # Pieces table: col 1 (description) stretches to fill; the rest are fixed
        # — col 0 "#" index = 36px, col 2 length = 80px, col 3 qty = 48px. The
        # row-number gutter is hidden so col 0 is the only index shown.
        self._pieces_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._pieces_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self._pieces_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )
        self._pieces_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Fixed
        )
        self._pieces_table.setColumnWidth(0, 36)
        self._pieces_table.setColumnWidth(2, 80)
        self._pieces_table.setColumnWidth(3, 48)
        self._pieces_table.verticalHeader().setVisible(False)
        self._pieces_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._pieces_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )

        # Action button properties
        self.ui.open_btn.setProperty("variant", "accent")
        self.ui.open_btn.style().polish(self.ui.open_btn)
        self.ui.del_btn.setProperty("variant", "danger")
        self.ui.del_btn.style().polish(self.ui.del_btn)

        # ── i18n: override text with t() calls ──────────────────────────
        self.ui.title.setText(t("tab_jobs"))
        self.ui.new_btn.setText(t("new_job"))
        self._search_entry.setPlaceholderText(t("jobs_search_placeholder"))
        self._detail_placeholder.setText(t("jobs_no_selection"))
        self.ui.key_client.setText(f"{t('client')}:")
        self.ui.key_offer.setText(f"{t('offer_number')}:")
        self.ui.key_order.setText(f"{t('order_number')}:")
        self.ui.key_desc.setText(f"{t('profile_tube_label')}:")
        # The description field now shows profile/material/quality (auto-filled
        # from the job's state) — not a user-editable free-text field.
        self._detail_desc_lbl.setReadOnly(True)
        # Fix 6: Set text/icon for the "Create new job" button.
        self._create_job_btn.setText(t("create_new_job"))
        self._create_job_btn.setIcon(themed_icon("plus", "#FFFFFF", 14))
        self._create_job_btn.setIconSize(QSize(14, 14))
        self._create_job_btn.style().polish(self._create_job_btn)
        self._pieces_table.setHorizontalHeaderLabels(
            ["#", t("description"), t("bar_length", u="mm"), t("stock_qty")]
        )
        self.ui.save_changes_btn.setText(t("save_changes"))
        self.ui.open_btn.setText(t("jobs_open"))
        self.ui.del_btn.setText(t("jobs_delete"))

        # Replace generated-file emoji/unicode text with themed SVG icons.
        self.ui.search_btn.setText("")
        self.ui.search_btn.setIcon(themed_icon("search"))
        self.ui.search_btn.setIconSize(QSize(16, 16))
        self.ui.search_btn.setFixedSize(30, 30)
        self.ui.search_btn.setToolTip(t("jobs_search_placeholder"))
        self.ui.clear_btn.setText("")
        self.ui.clear_btn.setIcon(themed_icon("x", _th.TEXT_SEC))
        self.ui.clear_btn.setIconSize(QSize(14, 14))
        self.ui.clear_btn.setFixedSize(30, 30)
        self.ui.clear_btn.setToolTip(t("clear"))

        # ── Populate search field combo ──────────────────────────────────
        for key, label_fn in self._SEARCH_FIELDS:
            self._search_field.addItem(label_fn(), key)

        # ── Connect signals ──────────────────────────────────────────────
        self.ui.new_btn.clicked.connect(self._new_job)
        self._search_field.currentIndexChanged.connect(lambda _: self._run_search())
        self._search_entry.textChanged.connect(lambda _: self._search_timer.start())
        self._search_entry.returnPressed.connect(self._run_search)
        self.ui.search_btn.clicked.connect(self._run_search)
        self.ui.clear_btn.clicked.connect(self._clear_search)
        self.ui.open_btn.clicked.connect(self._open_selected)
        self.ui.del_btn.clicked.connect(self._delete_selected)

        # Job metadata is edited in the detail panel but only committed when the
        # user clicks "Save changes" (next to Open/Delete) — no silent auto-save.
        self.ui.save_changes_btn.clicked.connect(self._save_detail_meta)

        # ── Load initial data ────────────────────────────────────────────
        self.refresh_list()

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh_list(self) -> None:
        try:
            from nestube.database import get_geometry_db
            self._jobs = get_geometry_db().list_jobs_summary()
        except Exception:
            self._jobs = []

        self._render_job_list(self._jobs)

        if self._selected_job_id is not None:
            if any(j["id"] == self._selected_job_id for j in self._jobs):
                self._show_detail(self._selected_job_id)
            else:
                self._selected_job_id = None
                self._hide_detail()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _render_job_list(self, jobs: list) -> None:
        # Remove all tiles (keep the trailing stretch). Detach synchronously
        # (hide + setParent(None)) before deleteLater: a tile pending deletion
        # keeps its old geometry and repaints over the rebuilt list, leaving a
        # ghost duplicate when the list is refreshed (e.g. after saving a job).
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        if not jobs:
            empty = QLabel(t("jobs_no_jobs"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:11px;")
            empty.setContentsMargins(0, 20, 0, 0)
            self._list_layout.insertWidget(0, empty)
            return

        for job in jobs:
            tile = _JobTile(job, selected=(job["id"] == self._selected_job_id))
            tile.mousePressEvent = lambda e, jid=job["id"]: self._select(jid)
            tile.mouseDoubleClickEvent = lambda e, jid=job["id"]: self._open_job(jid)
            self._list_layout.insertWidget(self._list_layout.count() - 1, tile)

    def _select(self, job_id: int) -> None:
        self._selected_job_id = job_id
        # Refresh tiles to update selection highlight
        query = self._search_entry.text().strip()
        if query:
            self._run_search()
        else:
            self._render_job_list(self._jobs)
        self._show_detail(job_id)

    def _show_detail(self, job_id: int) -> None:
        job = next((j for j in self._jobs if j["id"] == job_id), None)
        if job is None:
            return

        self._detail_placeholder.setVisible(False)
        self._detail_card.setVisible(True)

        name = job.get("name") or job.get("description") or f"Job #{job['id']}"
        # Fix 3: show creation date (non-editable) rather than last-updated date.
        created = (job.get("created_at") or "")[:10]
        self._detail_name_lbl.setText(name)
        self._detail_date_lbl.setText(f"{t('created')}: {created}" if created else "")

        for fld, val in (
            (self._detail_client_lbl, job.get("client")),
            (self._detail_offer_lbl, job.get("offer")),
            (self._detail_order_lbl, job.get("order_ref")),
        ):
            fld.setText(val or "")
            fld.setPlaceholderText("—")

        try:
            from nestube.database import get_geometry_db
            state_dict = get_geometry_db().get_job_state(job_id)
        except Exception:
            _log.exception("Failed to load state for job %s", job_id)
            state_dict = None

        # Fix 2: populate profile/material/quality from material_contexts. A job
        # may carry several material sub-tabs; show each as "profile · material ·
        # quality". Empty placeholder contexts (e.g. an untouched "Nesting 1") are
        # skipped so the panel never shows a blank line instead of the real data.
        from nestube.naming import format_full_name
        mcs = (state_dict or {}).get("material_contexts") or []
        parts = []
        for mc in mcs:
            label = format_full_name(
                mc.get("profile_name", ""),
                mc.get("material", ""),
                mc.get("quality", ""),
            ).strip(" ·")
            if label:
                parts.append(label)
        self._detail_desc_lbl.setText("   |   ".join(parts) if parts else "—")
        self._detail_desc_lbl.setToolTip("\n".join(parts) if parts else "")

        self._populate_pieces(state_dict)
        self._populate_stock_info(state_dict)
        self._populate_retal_info(name)

    def _save_detail_meta(self) -> None:
        """Persist the detail-panel metadata to the DB and refresh the list."""
        if self._selected_job_id is None:
            return
        name = self._detail_name_lbl.text().strip() or f"Job #{self._selected_job_id}"
        reply = QMessageBox.question(
            self, t("save_changes"),
            t("confirm_save_job", name=name),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply != QMessageBox.StandardButton.Save:
            return
        try:
            from nestube.database import get_geometry_db
            # The job name is never updated here — it is the auto-generated job
            # number and may not be overridden. Only the editable metadata
            # (client/offer/order) is persisted; description is now auto-filled
            # from the job's profile/material/quality and is read-only.
            get_geometry_db().update_job_meta(
                self._selected_job_id,
                client=self._detail_client_lbl.text().strip(),
                offer=self._detail_offer_lbl.text().strip(),
                order_ref=self._detail_order_lbl.text().strip(),
            )
        except Exception:
            _log.exception("Could not update job metadata")
            return
        self.refresh_list()

    def _hide_detail(self) -> None:
        self._detail_card.setVisible(False)
        self._detail_placeholder.setVisible(True)

    def _populate_pieces(self, state_dict: Optional[dict]) -> None:
        self._pieces_table.setRowCount(0)
        if not state_dict:
            return

        cortes = state_dict.get("cortes", [])
        for i, corte in enumerate(cortes):
            row = self._pieces_table.rowCount()
            self._pieces_table.insertRow(row)
            largo = corte.get("largo", 0)
            qty   = corte.get("cantidad", 1)
            desc  = (corte.get("descripcion") or corte.get("nombre")
                     or f"{t('pieces')} {i + 1}")

            for col, val, align in [
                (0, str(i + 1), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                (1, desc,       Qt.AlignmentFlag.AlignLeft  | Qt.AlignmentFlag.AlignVCenter),
                (2, str(largo), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                (3, str(qty),   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            ]:
                item = QTableWidgetItem(val)
                item.setTextAlignment(int(align))
                self._pieces_table.setItem(row, col, item)

        self._pieces_table.resizeRowsToContents()

    def _populate_stock_info(self, state_dict: Optional[dict]) -> None:
        """Show stock-used summary for the selected job (§11)."""
        self._stock_info_lbl.setVisible(False)
        self._stock_info_lbl.setText("")
        if not state_dict:
            return

        lines = []
        for ctx in state_dict.get("material_contexts", []):
            if not ctx.get("use_stock"):
                continue
            bar_name = ctx.get("linked_stock_bar_name", "")
            n_deducted = int(ctx.get("nesting_bars_deducted", 0))
            if n_deducted > 0 and bar_name:
                lines.append(t("jobs_stock_used_line", name=bar_name, count=n_deducted))

        if lines:
            self._stock_info_lbl.setText(
                f"<b>{t('jobs_stock_used_title')}</b><br>" + "<br>".join(lines)
            )
            self._stock_info_lbl.setVisible(True)

    def _populate_retal_info(self, job_name: str) -> None:
        """Show remnants generated by this job in the detail panel (§11)."""
        self._retal_info_lbl.setVisible(False)
        self._retal_info_lbl.setText("")
        if not job_name:
            return
        try:
            from nestube.stock_db import get_bars_by_creation_job
            bars = get_bars_by_creation_job(job_name)
        except Exception:
            return
        retales = [b for b in bars if b.is_retal]
        if not retales:
            return
        lines = [
            t("jobs_retal_line", name=b.profile_name or b.display_name,
              length=b.retal_length)
            for b in retales
        ]
        self._retal_info_lbl.setText(
            f"<b>{t('jobs_retales_title')}</b><br>" + "<br>".join(lines)
        )
        self._retal_info_lbl.setVisible(True)

    # ── Search ────────────────────────────────────────────────────────────────

    def _run_search(self) -> None:
        query = self._search_entry.text().strip()
        if not query:
            self._render_job_list(self._jobs)
            return
        field_key = self._search_field.currentData() or "name"
        db_field = self._SEARCH_FIELD_MAP.get(field_key, "name")
        q_lower = query.lower()
        filtered = [j for j in self._jobs if q_lower in (j.get(db_field) or "").lower()]
        self._render_job_list(filtered)

    def _clear_search(self) -> None:
        self._search_entry.clear()
        self._render_job_list(self._jobs)

    def select_job_by_name(self, name: str) -> None:
        """Show and select the job matching *name* (called from the Stock tab §11)."""
        self._search_entry.setText(name)
        self._run_search()
        match = next((j for j in self._jobs if j.get("name") == name), None)
        if match:
            self._select(match["id"])

    # ── Actions ───────────────────────────────────────────────────────────────

    def _new_job(self) -> None:
        from nestube.models import AppState
        from nestube.context_sync import ensure_material_contexts
        app = self._app
        new_state = AppState(
            language=app._state.language,
            calc_system=app._state.calc_system,
            currency=app._state.currency,
        )
        app._state.reset_from(new_state)
        # New job has no DB row yet.
        app._current_job_id = None
        ensure_material_contexts(app._state)
        # Seed the global cost defaults (§24) into the fresh job's contexts so
        # operator cost / cut time / mitre % / margin start at the user's chosen
        # values instead of the hardcoded dataclass fallbacks.
        from nestube import app_config as _ac
        _ac.apply_cost_defaults(app._state.perfil)
        for _ctx in app._state.material_contexts:
            _ac.apply_cost_defaults(_ctx.perfil)
        if hasattr(app, "_tab_cortes"):
            app._tab_cortes.load_state(app._state)
        if hasattr(app, "_tab_nesting"):
            app._tab_nesting.load_state(app._state)
        if hasattr(app, "_tab_perfiles"):
            app._tab_perfiles.set_values(app._state.perfil.to_dict())
        # §27: persist the new (empty) job to the DB right away so it exists as a
        # real record and shows in the list — no need to reach Ctrl+S first.
        if hasattr(app, "_save_job_to_db"):
            app._save_job_to_db(silent=True)
        if hasattr(app, "_tabs"):
            app._tabs.setCurrentWidget(app._tab_cortes)
        if hasattr(app, "_mark_clean"):
            app._mark_clean()

    def _open_selected(self) -> None:
        if self._selected_job_id is None:
            QMessageBox.warning(self, t("warning"), t("jobs_no_selection"))
            return
        self._open_job(self._selected_job_id)

    def _open_job(self, job_id: int) -> None:
        try:
            from nestube.database import get_geometry_db
            from nestube.models import AppState
            state_dict = get_geometry_db().get_job_state(job_id)
        except Exception as exc:
            QMessageBox.critical(self, t("open_error"), str(exc))
            return

        if not state_dict:
            QMessageBox.critical(self, t("open_error"), t("jobs_no_jobs"))
            return

        try:
            loaded = AppState.from_dict(state_dict)
        except Exception as exc:
            QMessageBox.critical(self, t("open_error"), str(exc))
            return

        app = self._app
        app._state.reset_from(loaded)
        # Remember which DB row this is so Ctrl+S updates the same row, not a new one.
        app._current_job_id = job_id
        if hasattr(app, "_tab_cortes"):
            app._tab_cortes.load_state(app._state)
        if hasattr(app, "_tab_nesting"):
            app._tab_nesting.load_state(app._state)
        if hasattr(app, "_tab_perfiles"):
            app._tab_perfiles.set_values(app._state.perfil.to_dict())
        if hasattr(app, "_tabs"):
            # Return the user to the tab they saved the job on (default Cuts).
            # _refresh_main_tab() repopulates that tab's UI from the new state.
            target = getattr(app._state, "active_tab", 1) or 1
            target = max(1, min(target, app._tabs.count() - 1))
            app._last_main_tab = target
            app._tabs.setCurrentIndex(target)
            if hasattr(app, "_refresh_main_tab"):
                app._refresh_main_tab(target)
        # The freshly opened job is the new clean baseline for the dirty guard.
        if hasattr(app, "_mark_clean"):
            app._mark_clean()

    def _delete_selected(self) -> None:
        if self._selected_job_id is None:
            QMessageBox.warning(self, t("warning"), t("jobs_no_selection"))
            return

        job = next((j for j in self._jobs if j["id"] == self._selected_job_id), None)
        name = job.get("name", "") if job else ""
        reply = QMessageBox.question(
            self, t("jobs_delete"), t("jobs_confirm_delete", name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from nestube.database import get_geometry_db
            get_geometry_db().delete_job(self._selected_job_id)
        except Exception as exc:
            QMessageBox.critical(self, t("save_error"), str(exc))
            return

        self._selected_job_id = None
        self._hide_detail()   # Fix 5: clear right panel immediately on delete
        self.refresh_list()

    def refresh_theme(self) -> None:
        """Re-apply background to the list panel after theme switch."""
        if hasattr(self, "_list_panel"):
            self._list_panel.setStyleSheet(f"background:{_th.BG_CARD};")
        if hasattr(self, "_stock_info_lbl"):
            self._stock_info_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
        if hasattr(self, "_retal_info_lbl"):
            self._retal_info_lbl.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:9px;")
