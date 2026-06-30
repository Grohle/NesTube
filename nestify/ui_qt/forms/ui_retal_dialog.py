# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'retal_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_GenerarRetalesDialog(object):
    def setupUi(self, GenerarRetalesDialog):
        if not GenerarRetalesDialog.objectName():
            GenerarRetalesDialog.setObjectName(u"GenerarRetalesDialog")
        GenerarRetalesDialog.resize(480, 460)
        GenerarRetalesDialog.setModal(True)
        self.main_layout = QVBoxLayout(GenerarRetalesDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(16, 14, 16, 14)
        self.title = QLabel(GenerarRetalesDialog)
        self.title.setObjectName(u"title")

        self.main_layout.addWidget(self.title)

        self.settings = QHBoxLayout()
        self.settings.setObjectName(u"settings")
        self.lbl_min_len = QLabel(GenerarRetalesDialog)
        self.lbl_min_len.setObjectName(u"lbl_min_len")

        self.settings.addWidget(self.lbl_min_len)

        self.min_len = QLineEdit(GenerarRetalesDialog)
        self.min_len.setObjectName(u"min_len")
        self.min_len.setProperty(u"fixedWidth", 70)
        self.min_len.setMaximumSize(QSize(70, 16777215))
        self.min_len.setMinimumSize(QSize(70, 0))

        self.settings.addWidget(self.min_len)

        self.lbl_desc = QLabel(GenerarRetalesDialog)
        self.lbl_desc.setObjectName(u"lbl_desc")

        self.settings.addWidget(self.lbl_desc)

        self.desc = QLineEdit(GenerarRetalesDialog)
        self.desc.setObjectName(u"desc")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.desc.sizePolicy().hasHeightForWidth())
        self.desc.setSizePolicy(sizePolicy)

        self.settings.addWidget(self.desc)

        self.refresh_btn = QPushButton(GenerarRetalesDialog)
        self.refresh_btn.setObjectName(u"refresh_btn")
        self.refresh_btn.setMaximumSize(QSize(80, 16777215))
        self.refresh_btn.setMinimumSize(QSize(80, 0))

        self.settings.addWidget(self.refresh_btn)


        self.main_layout.addLayout(self.settings)

        self.hdr = QFrame(GenerarRetalesDialog)
        self.hdr.setObjectName(u"hdr")
        self.hdr.setProperty(u"fixedHeight", 28)
        self.hdr.setMaximumSize(QSize(16777215, 28))
        self.hdr.setMinimumSize(QSize(0, 28))
        self.hdr_layout = QHBoxLayout(self.hdr)
        self.hdr_layout.setObjectName(u"hdr_layout")
        self.hdr_layout.setContentsMargins(36, 0, 12, 0)
        self.hdr_bar = QLabel(self.hdr)
        self.hdr_bar.setObjectName(u"hdr_bar")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.hdr_bar.sizePolicy().hasHeightForWidth())
        self.hdr_bar.setSizePolicy(sizePolicy1)

        self.hdr_layout.addWidget(self.hdr_bar)

        self.hdr_length = QLabel(self.hdr)
        self.hdr_length.setObjectName(u"hdr_length")
        sizePolicy1.setHeightForWidth(self.hdr_length.sizePolicy().hasHeightForWidth())
        self.hdr_length.setSizePolicy(sizePolicy1)

        self.hdr_layout.addWidget(self.hdr_length)

        self.hdr_pct = QLabel(self.hdr)
        self.hdr_pct.setObjectName(u"hdr_pct")
        self.hdr_pct.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.hdr_layout.addWidget(self.hdr_pct)


        self.main_layout.addWidget(self.hdr)

        self.scroll = QScrollArea(GenerarRetalesDialog)
        self.scroll.setObjectName(u"scroll")
        self.scroll.setWidgetResizable(True)
        self.list_widget = QWidget()
        self.list_widget.setObjectName(u"list_widget")
        self.list_layout = QGridLayout(self.list_widget)
        self.list_layout.setObjectName(u"list_layout")
        self.list_layout.setContentsMargins(8, 4, 12, 4)
        self.scroll.setWidget(self.list_widget)

        self.main_layout.addWidget(self.scroll)

        self.status_lbl = QLabel(GenerarRetalesDialog)
        self.status_lbl.setObjectName(u"status_lbl")

        self.main_layout.addWidget(self.status_lbl)

        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setObjectName(u"bottom_layout")
        self.bottom_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bottom_layout.addItem(self.bottom_spacer)

        self.ok_btn = QPushButton(GenerarRetalesDialog)
        self.ok_btn.setObjectName(u"ok_btn")

        self.bottom_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton(GenerarRetalesDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.bottom_layout.addWidget(self.cancel_btn)


        self.main_layout.addLayout(self.bottom_layout)


        self.retranslateUi(GenerarRetalesDialog)

        QMetaObject.connectSlotsByName(GenerarRetalesDialog)
    # setupUi

    def retranslateUi(self, GenerarRetalesDialog):
        GenerarRetalesDialog.setWindowTitle(QCoreApplication.translate("GenerarRetalesDialog", u"Generate Remnants", None))
        self.title.setText(QCoreApplication.translate("GenerarRetalesDialog", u"Generate Remnants", None))
        self.lbl_min_len.setText(QCoreApplication.translate("GenerarRetalesDialog", u"Min length", None))
        self.lbl_desc.setText(QCoreApplication.translate("GenerarRetalesDialog", u"Description", None))
        self.refresh_btn.setText(QCoreApplication.translate("GenerarRetalesDialog", u"Refresh", None))
        self.hdr_bar.setText(QCoreApplication.translate("GenerarRetalesDialog", u"Bar", None))
        self.hdr_length.setText(QCoreApplication.translate("GenerarRetalesDialog", u"Length", None))
        self.hdr_pct.setText(QCoreApplication.translate("GenerarRetalesDialog", u"%", None))
        self.status_lbl.setText("")
        self.ok_btn.setText(QCoreApplication.translate("GenerarRetalesDialog", u"OK", None))
        self.cancel_btn.setText(QCoreApplication.translate("GenerarRetalesDialog", u"Cancel", None))
    # retranslateUi

