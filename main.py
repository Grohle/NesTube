"""
main.py
Entry point for Nestify (version in nestify.__version__).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from nestify import app_config
from nestify.ui_qt.fonts_qt import register_bundled_fonts
from nestify.ui_qt.theme_qt import build_stylesheet


def main():
    prefs = app_config.load()

    # Automatic, consistent snapshot of the SQLite store on every launch
    # (rolling retention). Non-fatal: a backup failure never blocks startup.
    from nestify import backup
    backup.create_backup("startup")

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Nestify")

    register_bundled_fonts()
    app.setStyleSheet(build_stylesheet(prefs.theme))

    from nestify.ui_qt.app import NestifyApp

    window = NestifyApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
