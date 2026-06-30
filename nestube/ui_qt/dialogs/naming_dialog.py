"""
nestube/ui_qt/dialogs/naming_dialog.py
Single-window Name Assignment dialog with tabbed sections and one Save button.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QTabWidget, QVBoxLayout, QWidget,
)

from nestube import app_config
from nestube.i18n import t
import nestube.ui_qt.theme_qt as _th


class NamingDialog(QDialog):
    """Modal dialog for configuring all naming prefixes in a single window."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("name_assignment"))
        self.setMinimumWidth(420)
        self.setModal(True)

        prefs = app_config.get()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {_th.BORDER};
                background: {_th.BG_CARD};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {_th.BG_MID};
                color: {_th.TEXT_SEC};
                padding: 6px 16px;
                border: 1px solid {_th.BORDER};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {_th.BG_CARD};
                color: {_th.TEXT_PRI};
            }}
        """)

        # ── Jobs tab ─────────────────────────────────────────────────────────
        jobs_page = QWidget()
        jobs_layout = QVBoxLayout(jobs_page)
        jobs_layout.setContentsMargins(16, 16, 16, 16)
        jobs_layout.setSpacing(8)

        jobs_desc = QLabel(t("naming_jobs_desc"))
        jobs_desc.setWordWrap(True)
        jobs_desc.setStyleSheet(f"color: {_th.TEXT_DIM}; font-size: 11px;")
        jobs_layout.addWidget(jobs_desc)

        jobs_form = QFormLayout()
        jobs_form.setSpacing(8)
        jobs_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._e_job_prefix = QLineEdit(prefs.job_name_prefix)
        self._e_job_prefix.setPlaceholderText("JOB")
        self._e_job_prefix.setStyleSheet(
            f"background: {_th.BG_MID}; color: {_th.TEXT_PRI};"
            f" border: 1px solid {_th.BORDER}; border-radius: 4px;"
            f" padding: 4px 8px; min-height: 28px;"
        )
        lbl_job = QLabel(t("job_name_prefix") + ":")
        lbl_job.setStyleSheet(f"color: {_th.TEXT_SEC};")
        jobs_form.addRow(lbl_job, self._e_job_prefix)

        self._e_rem_prefix = QLineEdit(prefs.remnant_name_prefix)
        self._e_rem_prefix.setPlaceholderText("RET")
        self._e_rem_prefix.setStyleSheet(
            f"background: {_th.BG_MID}; color: {_th.TEXT_PRI};"
            f" border: 1px solid {_th.BORDER}; border-radius: 4px;"
            f" padding: 4px 8px; min-height: 28px;"
        )
        lbl_rem = QLabel(t("remnant_name_prefix") + ":")
        lbl_rem.setStyleSheet(f"color: {_th.TEXT_SEC};")
        jobs_form.addRow(lbl_rem, self._e_rem_prefix)

        jobs_layout.addLayout(jobs_form)
        jobs_layout.addStretch()

        tabs.addTab(jobs_page, t("tab_jobs"))
        layout.addWidget(tabs)

        # ── Button box ───────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(t("save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        prefs = app_config.get()
        job_prefix = self._e_job_prefix.text().strip()
        rem_prefix = self._e_rem_prefix.text().strip()
        if job_prefix:
            prefs.job_name_prefix = job_prefix
        if rem_prefix:
            prefs.remnant_name_prefix = rem_prefix
        app_config.save(prefs)
        self.accept()
