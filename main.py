"""
main.py
Entry point for NesTube (version in nestube.__version__).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from nestube import app_config
from nestube.ui_qt.fonts_qt import register_bundled_fonts
from nestube.ui_qt.theme_qt import build_stylesheet


def main():
    prefs = app_config.load()

    # Automatic, consistent snapshot of the SQLite store on every launch
    # (rolling retention). Non-fatal: a backup failure never blocks startup.
    from nestube import backup
    backup.create_backup("startup")

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("NesTube")

    register_bundled_fonts()
    app.setStyleSheet(build_stylesheet(prefs.theme))

    from nestube.ui_qt.app import NesTubeApp

    window = NesTubeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
