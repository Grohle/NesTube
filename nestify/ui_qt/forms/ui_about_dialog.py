# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName(u"AboutDialog")
        AboutDialog.resize(520, 560)
        AboutDialog.setMinimumSize(QSize(520, 560))
        AboutDialog.setMaximumSize(QSize(520, 560))
        AboutDialog.setModal(True)
        self.main_layout = QVBoxLayout(AboutDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.logo_lbl = QLabel(AboutDialog)
        self.logo_lbl.setObjectName(u"logo_lbl")
        self.logo_lbl.setAlignment(Qt.AlignCenter)

        self.main_layout.addWidget(self.logo_lbl)

        self.title_lbl = QLabel(AboutDialog)
        self.title_lbl.setObjectName(u"title_lbl")
        self.title_lbl.setAlignment(Qt.AlignCenter)

        self.main_layout.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(AboutDialog)
        self.desc_lbl.setObjectName(u"desc_lbl")
        self.desc_lbl.setWordWrap(True)

        self.main_layout.addWidget(self.desc_lbl)

        self.notice_lbl = QLabel(AboutDialog)
        self.notice_lbl.setObjectName(u"notice_lbl")
        self.notice_lbl.setWordWrap(True)

        self.main_layout.addWidget(self.notice_lbl)

        self.ver_lbl = QLabel(AboutDialog)
        self.ver_lbl.setObjectName(u"ver_lbl")

        self.main_layout.addWidget(self.ver_lbl)

        self.update_status = QLabel(AboutDialog)
        self.update_status.setObjectName(u"update_status")
        self.update_status.setWordWrap(True)

        self.main_layout.addWidget(self.update_status)

        self.notes_box = QTextEdit(AboutDialog)
        self.notes_box.setObjectName(u"notes_box")
        self.notes_box.setMaximumSize(QSize(16777215, 100))
        self.notes_box.setReadOnly(True)

        self.main_layout.addWidget(self.notes_box)

        self.donate_row = QHBoxLayout()
        self.donate_row.setObjectName(u"donate_row")
        self.paypal_btn = QPushButton(AboutDialog)
        self.paypal_btn.setObjectName(u"paypal_btn")

        self.donate_row.addWidget(self.paypal_btn)

        self.coffee_btn = QPushButton(AboutDialog)
        self.coffee_btn.setObjectName(u"coffee_btn")

        self.donate_row.addWidget(self.coffee_btn)


        self.main_layout.addLayout(self.donate_row)

        self.btn_row = QHBoxLayout()
        self.btn_row.setObjectName(u"btn_row")
        self.check_btn = QPushButton(AboutDialog)
        self.check_btn.setObjectName(u"check_btn")

        self.btn_row.addWidget(self.check_btn)


        self.main_layout.addLayout(self.btn_row)

        self.close_row = QHBoxLayout()
        self.close_row.setObjectName(u"close_row")
        self.github_btn = QPushButton(AboutDialog)
        self.github_btn.setObjectName(u"github_btn")

        self.close_row.addWidget(self.github_btn)

        self.no_show_cb = QCheckBox(AboutDialog)
        self.no_show_cb.setObjectName(u"no_show_cb")

        self.close_row.addWidget(self.no_show_cb)

        self.close_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.close_row.addItem(self.close_spacer)

        self.close_btn = QPushButton(AboutDialog)
        self.close_btn.setObjectName(u"close_btn")

        self.close_row.addWidget(self.close_btn)


        self.main_layout.addLayout(self.close_row)


        self.retranslateUi(AboutDialog)

        QMetaObject.connectSlotsByName(AboutDialog)
    # setupUi

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(QCoreApplication.translate("AboutDialog", u"About", None))
        self.logo_lbl.setText("")
        self.title_lbl.setText(QCoreApplication.translate("AboutDialog", u"Nestify", None))
        self.desc_lbl.setText(QCoreApplication.translate("AboutDialog", u"Description", None))
        self.notice_lbl.setText(QCoreApplication.translate("AboutDialog", u"Notice", None))
        self.ver_lbl.setText(QCoreApplication.translate("AboutDialog", u"Version", None))
        self.update_status.setText(QCoreApplication.translate("AboutDialog", u"Checking for updates...", None))
        self.paypal_btn.setText(QCoreApplication.translate("AboutDialog", u"PayPal", None))
        self.coffee_btn.setText(QCoreApplication.translate("AboutDialog", u"Buy Me a Coffee", None))
        self.check_btn.setText(QCoreApplication.translate("AboutDialog", u"Check Updates", None))
        self.github_btn.setText(QCoreApplication.translate("AboutDialog", u"GitHub", None))
        self.no_show_cb.setText(QCoreApplication.translate("AboutDialog", u"Don't show again", None))
        self.close_btn.setText(QCoreApplication.translate("AboutDialog", u"Close", None))
    # retranslateUi

