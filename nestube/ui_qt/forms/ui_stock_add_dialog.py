# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stock_add_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_StockAddDialog(object):
    def setupUi(self, StockAddDialog):
        if not StockAddDialog.objectName():
            StockAddDialog.setObjectName(u"StockAddDialog")
        StockAddDialog.resize(500, 640)
        StockAddDialog.setMinimumSize(QSize(460, 480))
        StockAddDialog.setModal(True)
        self.outer_layout = QVBoxLayout(StockAddDialog)
        self.outer_layout.setObjectName(u"outer_layout")
        self.outer_layout.setContentsMargins(8, 14, 8, 14)
        self.title = QLabel(StockAddDialog)
        self.title.setObjectName(u"title")

        self.outer_layout.addWidget(self.title)

        self.scroll = QScrollArea(StockAddDialog)
        self.scroll.setObjectName(u"scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName(u"scroll_widget")
        self.scroll_widget.setGeometry(QRect(0, 0, 482, 560))
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setObjectName(u"scroll_layout")
        self.scroll_layout.setContentsMargins(8, 4, 8, 4)
        self.hint = QLabel(self.scroll_widget)
        self.hint.setObjectName(u"hint")
        self.hint.setWordWrap(True)

        self.scroll_layout.addWidget(self.hint)

        self.scroll_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.scroll_layout.addItem(self.scroll_spacer)

        self.scroll.setWidget(self.scroll_widget)

        self.outer_layout.addWidget(self.scroll)

        self.btn_layout = QHBoxLayout()
        self.btn_layout.setObjectName(u"btn_layout")
        self.btn_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.btn_layout.addItem(self.btn_spacer)

        self.save_btn = QPushButton(StockAddDialog)
        self.save_btn.setObjectName(u"save_btn")

        self.btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton(StockAddDialog)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.btn_layout.addWidget(self.cancel_btn)


        self.outer_layout.addLayout(self.btn_layout)


        self.retranslateUi(StockAddDialog)

        QMetaObject.connectSlotsByName(StockAddDialog)
    # setupUi

    def retranslateUi(self, StockAddDialog):
        StockAddDialog.setWindowTitle(QCoreApplication.translate("StockAddDialog", u"Add to Stock", None))
        self.title.setText(QCoreApplication.translate("StockAddDialog", u"Add to Stock", None))
        self.hint.setText(QCoreApplication.translate("StockAddDialog", u"Form hint", None))
        self.save_btn.setText(QCoreApplication.translate("StockAddDialog", u"Save", None))
        self.cancel_btn.setText(QCoreApplication.translate("StockAddDialog", u"Cancel", None))
    # retranslateUi

