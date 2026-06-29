"""
nestify/ui_qt/dialogs/about_dialog.py
About window: version, description, GitHub link, update check.
"""
from __future__ import annotations

import os
import webbrowser
from typing import Callable, Optional

from PySide6.QtCore import QRunnable, QObject, QSize, QThreadPool, Qt, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QWidget

from nestify import __version__
from nestify.i18n import t
from nestify.resources import logo_png_path
import nestify.ui_qt.theme_qt as _th
from nestify.ui_qt.forms.ui_about_dialog import Ui_AboutDialog
from nestify.ui_qt.nesting_scene import _text_color_for_bg
from nestify.updater import UpdateInfo, check_for_update


class _UpdateSignals(QObject):
    result = Signal(object)


class _UpdateWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = _UpdateSignals()

    def run(self) -> None:
        info = check_for_update()
        self.signals.result.emit(info)


class AboutDialog(QDialog):
    """Modal about / update dialog."""

    def __init__(
        self,
        parent: QWidget,
        github_url: str,
        paypal_url: str = "",
        buymeacoffee_url: str = "",
        on_check_done: Optional[Callable[[], None]] = None,
        on_no_show: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)

        self._github_url = github_url.rstrip("/")
        self._paypal_url = paypal_url
        self._coffee_url = buymeacoffee_url
        self._on_check_done = on_check_done
        self._on_no_show = on_no_show
        self._update_info: Optional[UpdateInfo] = None

        self.setWindowTitle(t("about_title"))

        # Single dialog-level stylesheet — avoids the Qt cascade-break that
        # occurs when individual child widgets call setStyleSheet without an
        # explicit background-color (child reverts to native white).
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {_th.BG_CARD};
            }}
            QLabel {{
                background-color: transparent;
                color: {_th.TEXT_PRI};
            }}
            QLabel#desc_lbl, QLabel#notice_lbl, QLabel#update_status {{
                color: {_th.TEXT_DIM};
            }}
            QLabel#notice_lbl {{
                font-size: 11px;
            }}
            QLabel#title_lbl {{
                font-size: 18px;
                font-weight: bold;
            }}
            QTextEdit {{
                background-color: {_th.BG_MID};
                color: {_th.TEXT_SEC};
                border: 1px solid {_th.BORDER};
                border-radius: 4px;
                padding: 4px;
            }}
            QCheckBox {{
                background-color: transparent;
                color: {_th.TEXT_SEC};
            }}
        """)

        # Logo: scaled to fit a 200×133 box (keeping aspect ratio, smoothly).
        lpath = logo_png_path()
        if os.path.isfile(lpath):
            pix = QPixmap(lpath).scaled(
                200, 133,
                aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
                mode=Qt.TransformationMode.SmoothTransformation,
            )
            self.ui.logo_lbl.setPixmap(pix)

        self.ui.title_lbl.setText(t("app_title"))
        self.ui.desc_lbl.setText(t("about_description"))
        self.ui.notice_lbl.setText(t("translations_notice"))
        self.ui.ver_lbl.setText(t("about_version_line").format(version=__version__))
        self.ui.update_status.setText(t("about_checking_updates"))
        self.ui.no_show_cb.setText(t("about_no_show_again"))
        self.ui.close_btn.setText(t("close"))

        # ── Branded buttons (shared base template) ────────────────────────────
        _btn = (
            "QPushButton {{"
            "  border: none; border-radius: 4px;"
            "  font-weight: bold; padding: 6px 14px; min-height: 32px;"
            "  background-color: {bg}; color: {fg};"
            "}}"
            "QPushButton:hover {{ background-color: {hover}; }}"
            "QPushButton:pressed {{ background-color: {pressed}; }}"
            "QPushButton:disabled {{ background-color: {disabled}; color: {dfg}; }}"
        )

        # GitHub — icon-only, 40×32, corporate dark #24292e
        from nestify.ui_qt.icons import themed_icon
        gh_icon = themed_icon("github", "#FFFFFF", size=20)
        sizes = gh_icon.availableSizes()
        self.ui.github_btn.setIcon(gh_icon)
        self.ui.github_btn.setIconSize(sizes[0] if sizes else QSize(20, 20))
        self.ui.github_btn.setText("")
        self.ui.github_btn.setToolTip("GitHub")
        self.ui.github_btn.setFixedSize(40, 32)
        self.ui.github_btn.setStyleSheet(
            _btn.format(bg="#24292e", fg="#FFFFFF",
                        hover="#444d56", pressed="#1b1f23",
                        disabled="#555", dfg="#999")
        )

        # PayPal — corporate blue
        self.ui.paypal_btn.setText("PayPal")
        self.ui.paypal_btn.setFixedHeight(32)
        self.ui.paypal_btn.setStyleSheet(
            _btn.format(bg="#003087", fg="#FFFFFF",
                        hover="#009cde", pressed="#002069",
                        disabled="#6b7b99", dfg="#cccccc")
        )
        self.ui.paypal_btn.setVisible(bool(paypal_url))

        # BuyMeACoffee — corporate yellow
        self.ui.coffee_btn.setText("Buy me a coffee")
        self.ui.coffee_btn.setFixedHeight(32)
        self.ui.coffee_btn.setStyleSheet(
            _btn.format(bg="#FFDD00", fg="#000000",
                        hover="#FFE840", pressed="#E6C700",
                        disabled="#f0e070", dfg="#666666")
        )
        self.ui.coffee_btn.setVisible(bool(buymeacoffee_url))

        # Check Updates — same 32px height, accent-coloured
        self.ui.check_btn.setText(t("about_check_updates"))
        self.ui.check_btn.setFixedHeight(32)
        self.ui.check_btn.setStyleSheet(
            _btn.format(bg=_th.ACCENT, fg=_text_color_for_bg(_th.ACCENT),
                        hover=_th.ACCENT_HVR, pressed=_th.ACCENT,
                        disabled=_th.BG_MID, dfg=_th.TEXT_DIM)
        )

        # Signal connections
        self.ui.github_btn.clicked.connect(self._open_github)
        self.ui.paypal_btn.clicked.connect(lambda: webbrowser.open(self._paypal_url))
        self.ui.coffee_btn.clicked.connect(lambda: webbrowser.open(self._coffee_url))
        self.ui.check_btn.clicked.connect(self._check_updates_async)
        self.ui.close_btn.clicked.connect(self._close)

        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._check_updates_async)

    def _close(self) -> None:
        if self.ui.no_show_cb.isChecked() and self._on_no_show:
            self._on_no_show()
        self.accept()

    def _open_github(self) -> None:
        webbrowser.open(self._github_url)

    def _set_update_ui(self, text: str, notes: str = "") -> None:
        self.ui.update_status.setText(text)
        self.ui.notes_box.setPlainText(notes)

    def _check_updates_async(self) -> None:
        self.ui.check_btn.setEnabled(False)
        self._set_update_ui(t("about_checking_updates"))
        worker = _UpdateWorker()
        worker.signals.result.connect(self._on_update_result)
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def _on_update_result(self, info: Optional[UpdateInfo]) -> None:
        self.ui.check_btn.setEnabled(True)
        self._update_info = info
        if self._on_check_done:
            self._on_check_done()

        if info is None:
            self._set_update_ui(t("about_update_check_failed"))
            return

        if info.update_available:
            status = t("about_update_available").format(
                current=info.current_version,
                latest=info.latest_version,
            )
            notes = info.release_notes or t("about_no_release_notes")
            self._set_update_ui(status, notes)
        else:
            self._set_update_ui(
                t("about_up_to_date").format(version=info.current_version),
                info.release_notes or "",
            )


def show_about_dialog(parent: QWidget, github_url: str,
                      paypal_url: str = "", buymeacoffee_url: str = "") -> None:
    AboutDialog(parent, github_url=github_url,
                paypal_url=paypal_url, buymeacoffee_url=buymeacoffee_url).exec()
