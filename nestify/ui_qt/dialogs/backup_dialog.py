"""
nestify/ui_qt/dialogs/backup_dialog.py
Manage SQLite database backups: list snapshots, make one now, and restore
(from the list or an arbitrary file). Restoring requires an app restart, so it
just swaps the DB file and tells the user to relaunch.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from nestify import backup
from nestify.i18n import t
import nestify.ui_qt.theme_qt as _th


def _human_size(n: int) -> str:
    """Compact human-readable byte size for the snapshot rows."""
    val = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if val < 1024 or unit == "GB":
            return f"{val:.0f} {unit}" if unit == "B" else f"{val:.1f} {unit}"
        val /= 1024
    return f"{n} B"


class BackupDialog(QDialog):
    """List + create + restore backups of nestify_geometry.db."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("backups_title"))
        # Opens at a comfortable list size; the rows are the focus.
        self.resize(520, 460)
        self.setModal(True)
        self._selected: str = ""
        self._build()
        self._refresh_list()

    def _build(self) -> None:
        # Outer column: 12px sides/top, 16px bottom for the action row.
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 16)

        title = QLabel(t("backups_title"))
        title.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold;")
        root.addWidget(title)

        hint = QLabel(t("backups_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:11px;")
        root.addWidget(hint)

        # Scrollable list of snapshot rows on a BG_CARD surface.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background:{_th.BG_CARD}; border:none; }}")
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(3)
        scroll.setWidget(self._list_widget)
        root.addWidget(scroll, 1)

        # Action row: backup-now and restore-from-file on the left, the primary
        # restore-selected on the right.
        actions = QHBoxLayout()
        now_btn = QPushButton(t("backup_now"))
        now_btn.clicked.connect(self._backup_now)
        actions.addWidget(now_btn)

        from_file_btn = QPushButton(t("backup_restore_from_file"))
        from_file_btn.clicked.connect(self._restore_from_file)
        actions.addWidget(from_file_btn)

        actions.addStretch()
        restore_btn = QPushButton(t("backup_restore"))
        restore_btn.setProperty("variant", "accent")
        restore_btn.clicked.connect(self._restore_selected)
        actions.addWidget(restore_btn)
        root.addLayout(actions)

    def _refresh_list(self) -> None:
        # Detach synchronously before deleteLater so a pending-deletion row
        # can't repaint over the rebuilt list.
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        backups = backup.list_backups()
        if not backups:
            empty = QLabel(t("backup_none"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_th.TEXT_DIM}; font-size:11px;")
            self._list_layout.addWidget(empty)
            self._list_layout.addStretch()
            return

        # One 34px row per snapshot: "YYYY-MM-DD HH:MM  ·  size". Selected →
        # ACCENT border + BG_MID fill, otherwise a faint BORDER on transparent.
        for path, mtime, size in backups:
            label = f"{mtime.strftime('%Y-%m-%d %H:%M:%S')}    {_human_size(size)}"
            row = QPushButton(label)
            row.setFixedHeight(34)
            is_sel = (path == self._selected)
            border = _th.ACCENT if is_sel else _th.BORDER
            bg = _th.BG_MID if is_sel else "transparent"
            row.setStyleSheet(
                f"QPushButton {{ text-align:left; padding-left:8px; background:{bg};"
                f" color:{_th.TEXT_PRI}; border:1px solid {border}; border-radius:4px; }}"
                f"QPushButton:hover {{ background:{_th.BG_MID}; }}"
            )
            row.clicked.connect(lambda checked=False, p=path: self._select(p))
            self._list_layout.addWidget(row)
        self._list_layout.addStretch()

    def _select(self, path: str) -> None:
        self._selected = path
        self._refresh_list()

    def _backup_now(self) -> None:
        path = backup.create_backup("manual")
        if path:
            self._selected = path
        self._refresh_list()
        QMessageBox.information(self, t("backups_title"), t("backup_created"))

    def _restore_selected(self) -> None:
        if not self._selected:
            QMessageBox.warning(self, t("backups_title"), t("backup_select_msg"))
            return
        self._do_restore(self._selected)

    def _restore_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("backup_restore_from_file"), backup.backup_dir(),
            "SQLite (*.db);;All (*.*)",
        )
        if path:
            self._do_restore(path)

    def _do_restore(self, path: str) -> None:
        reply = QMessageBox.question(
            self, t("backups_title"), t("backup_restore_confirm"),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if backup.restore_backup(path):
            QMessageBox.information(self, t("backups_title"), t("backup_restored_restart"))
            self.accept()
        else:
            QMessageBox.critical(self, t("backups_title"), t("backup_restore_failed"))
