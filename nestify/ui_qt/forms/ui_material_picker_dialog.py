# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'material_picker_dialog.ui'
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
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_MaterialPickerDialog(object):
    def setupUi(self, MaterialPickerDialog):
        if not MaterialPickerDialog.objectName():
            MaterialPickerDialog.setObjectName(u"MaterialPickerDialog")
        MaterialPickerDialog.resize(420, 360)
        MaterialPickerDialog.setModal(True)
        self.main_layout = QVBoxLayout(MaterialPickerDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.title = QLabel(MaterialPickerDialog)
        self.title.setObjectName(u"title")

        self.main_layout.addWidget(self.title)

        self.search_row = QHBoxLayout()
        self.search_row.setObjectName(u"search_row")
        self.search = QLineEdit(MaterialPickerDialog)
        self.search.setObjectName(u"search")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.search.sizePolicy().hasHeightForWidth())
        self.search.setSizePolicy(sizePolicy)

        self.search_row.addWidget(self.search)

        self.manage_btn = QPushButton(MaterialPickerDialog)
        self.manage_btn.setObjectName(u"manage_btn")
        self.manage_btn.setMinimumSize(QSize(100, 28))
        self.manage_btn.setMaximumSize(QSize(100, 28))

        self.search_row.addWidget(self.manage_btn)


        self.main_layout.addLayout(self.search_row)

        self.scroll = QScrollArea(MaterialPickerDialog)
        self.scroll.setObjectName(u"scroll")
        self.scroll.setWidgetResizable(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.scroll.sizePolicy().hasHeightForWidth())
        self.scroll.setSizePolicy(sizePolicy1)
        self.list_widget = QWidget()
        self.list_widget.setObjectName(u"list_widget")
        self.list_widget.setGeometry(QRect(0, 0, 394, 280))
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(2)
        self.list_layout.setObjectName(u"list_layout")
        self.list_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.list_widget)

        self.main_layout.addWidget(self.scroll)


        self.retranslateUi(MaterialPickerDialog)

        QMetaObject.connectSlotsByName(MaterialPickerDialog)
    # setupUi

    def retranslateUi(self, MaterialPickerDialog):
        MaterialPickerDialog.setWindowTitle(QCoreApplication.translate("MaterialPickerDialog", u"Material Search", None))
        self.title.setText(QCoreApplication.translate("MaterialPickerDialog", u"Material Search", None))
        self.search.setPlaceholderText(QCoreApplication.translate("MaterialPickerDialog", u"Search materials...", None))
        self.manage_btn.setText(QCoreApplication.translate("MaterialPickerDialog", u"Manage", None))
    # retranslateUi

