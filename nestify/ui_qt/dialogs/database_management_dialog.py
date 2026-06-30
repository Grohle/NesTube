"""
nestify/ui_qt/dialogs/database_management_dialog.py

File > Database management. Configures where the single SQLite database lives
(so it can sit on a shared/server path), the backup directory and how often a
startup snapshot is taken, lets the user run a backup now, and switch the active
database to another file. Changing the active DB requires an app restart (caches
reload from the new file), mirroring the restore flow.
"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QVBoxLayout,
)

from nestify import backup, db_settings
from nestify.i18n import t
import nestify.ui_qt.theme_qt as _th

# Interval combo options: label key → hours (0 every launch, -1 disabled).
_INTERVALS = [
    ("db_backup_every_launch", 0.0),
    ("db_backup_daily", 24.0),
    ("db_backup_weekly", 168.0),
    ("db_backup_disabled", -1.0),
]


class DatabaseManagementDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("db_management_title"))
        self.resize(620, 360)
        self.setModal(True)
        self._build()
        self._refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel(t("db_management_title"))
        title.setStyleSheet(f"color:{_th.ACCENT}; font-weight:bold;")
        root.addWidget(title)
        hint = QLabel(t("db_management_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{_th.TEXT_SEC}; font-size:11px;")
        root.addWidget(hint)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        # ── Active database location ───────────────────────────────────────
        self._db_path_lbl = QLabel()
        self._db_path_lbl.setStyleSheet(f"color:{_th.TEXT_PRI};")
        self._db_path_lbl.setWordWrap(True)
        db_row = QHBoxLayout()
        db_row.addWidget(self._db_path_lbl, 1)
        change_btn = QPushButton(t("db_change_location"))
        change_btn.clicked.connect(self._change_location)
        db_row.addWidget(change_btn)
        load_btn = QPushButton(t("db_load"))
        load_btn.clicked.connect(self._load_database)
        db_row.addWidget(load_btn)
        _w = QFrame(); _w.setLayout(db_row)
        form.addRow(t("db_location_label"), _w)

        # ── Backup directory ───────────────────────────────────────────────
        self._backup_dir_lbl = QLabel()
        self._backup_dir_lbl.setStyleSheet(f"color:{_th.TEXT_PRI};")
        self._backup_dir_lbl.setWordWrap(True)
        bd_row = QHBoxLayout()
        bd_row.addWidget(self._backup_dir_lbl, 1)
        bd_btn = QPushButton(t("db_browse"))
        bd_btn.clicked.connect(self._change_backup_dir)
        bd_row.addWidget(bd_btn)
        _bw = QFrame(); _bw.setLayout(bd_row)
        form.addRow(t("db_backup_dir_label"), _bw)

        # ── Backup interval ────────────────────────────────────────────────
        self._interval_combo = QComboBox()
        for key, hours in _INTERVALS:
            self._interval_combo.addItem(t(key), hours)
        self._interval_combo.currentIndexChanged.connect(self._save_interval)
        form.addRow(t("db_backup_interval_label"), self._interval_combo)

        # ── Last backup ────────────────────────────────────────────────────
        self._last_backup_lbl = QLabel()
        self._last_backup_lbl.setStyleSheet(f"color:{_th.TEXT_SEC};")
        form.addRow(t("db_last_backup_label"), self._last_backup_lbl)

        root.addLayout(form)
        root.addStretch(1)

        actions = QHBoxLayout()
        now_btn = QPushButton(t("backup_now"))
        now_btn.clicked.connect(self._backup_now)
        actions.addWidget(now_btn)
        manage_btn = QPushButton(t("db_manage_backups"))
        manage_btn.clicked.connect(self._open_backups)
        actions.addWidget(manage_btn)
        actions.addStretch(1)
        close_btn = QPushButton(t("close"))
        close_btn.setProperty("variant", "accent")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        root.addLayout(actions)

    # ── Refresh ────────────────────────────────────────────────────────────
    def _refresh(self) -> None:
        s = db_settings.get()
        self._db_path_lbl.setText(s.resolved_db_path())
        self._backup_dir_lbl.setText(s.resolved_backup_dir())
        # Select the interval entry matching the saved value.
        idx = next((i for i, (_, h) in enumerate(_INTERVALS)
                    if h == s.backup_interval_hours), 0)
        self._interval_combo.blockSignals(True)
        self._interval_combo.setCurrentIndex(idx)
        self._interval_combo.blockSignals(False)
        if s.last_backup_ts > 0:
            from datetime import datetime
            self._last_backup_lbl.setText(
                datetime.fromtimestamp(s.last_backup_ts).strftime("%Y-%m-%d %H:%M"))
        else:
            self._last_backup_lbl.setText(t("db_backup_never"))

    # ── Actions ────────────────────────────────────────────────────────────
    def _save_interval(self) -> None:
        s = db_settings.get()
        s.backup_interval_hours = float(self._interval_combo.currentData())
        db_settings.save(s)

    def _change_backup_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, t("db_backup_dir_label"), db_settings.get().resolved_backup_dir())
        if d:
            s = db_settings.get()
            s.backup_dir = d
            db_settings.save(s)
            self._refresh()

    def _change_location(self) -> None:
        """Choose where the active database file should live (e.g. a server share)."""
        cur = db_settings.get().resolved_db_path()
        path, _ = QFileDialog.getSaveFileName(
            self, t("db_change_location"), cur, "SQLite (*.db);;All (*.*)")
        if not path:
            return
        self._set_db_path_and_restart(path, copy_current=not os.path.isfile(path))

    def _load_database(self) -> None:
        """Point the app at an existing database file."""
        path, _ = QFileDialog.getOpenFileName(
            self, t("db_load"), db_settings.get().resolved_db_path(),
            "SQLite (*.db);;All (*.*)")
        if path:
            self._set_db_path_and_restart(path, copy_current=False)

    def _set_db_path_and_restart(self, path: str, copy_current: bool) -> None:
        s = db_settings.get()
        old = s.resolved_db_path()
        if os.path.abspath(path) == os.path.abspath(old):
            return
        # When relocating to a brand-new file, offer to copy the current DB there
        # so the user's data moves with them.
        if copy_current and os.path.isfile(old):
            reply = QMessageBox.question(
                self, t("db_management_title"), t("db_copy_current_q"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    import shutil
                    from nestify.database import get_geometry_db
                    try:
                        get_geometry_db().close()
                    except Exception:
                        pass
                    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                    shutil.copy2(old, path)
                except OSError as exc:
                    QMessageBox.critical(self, t("db_management_title"), str(exc))
                    return
        s.db_path = path
        db_settings.save(s)
        QMessageBox.information(self, t("db_management_title"), t("db_switch_restart"))
        self.accept()

    def _backup_now(self) -> None:
        path = backup.create_backup("manual")
        if path:
            QMessageBox.information(self, t("db_management_title"), t("backup_created"))
        else:
            QMessageBox.warning(self, t("db_management_title"), t("backup_none"))
        self._refresh()

    def _open_backups(self) -> None:
        from nestify.ui_qt.dialogs.backup_dialog import BackupDialog
        BackupDialog(self).exec()
        self._refresh()
