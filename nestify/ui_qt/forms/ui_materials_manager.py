# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'materials_manager.ui'
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

class Ui_MaterialsManagerDialog(object):
    def setupUi(self, MaterialsManagerDialog):
        if not MaterialsManagerDialog.objectName():
            MaterialsManagerDialog.setObjectName(u"MaterialsManagerDialog")
        MaterialsManagerDialog.resize(520, 540)
        MaterialsManagerDialog.setMinimumSize(QSize(460, 480))
        MaterialsManagerDialog.setModal(True)
        self.main_layout = QVBoxLayout(MaterialsManagerDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.title = QLabel(MaterialsManagerDialog)
        self.title.setObjectName(u"title")

        self.main_layout.addWidget(self.title)

        self.form_card = QFrame(MaterialsManagerDialog)
        self.form_card.setObjectName(u"form_card")
        self.form_layout = QGridLayout(self.form_card)
        self.form_layout.setObjectName(u"form_layout")
        self.form_layout.setContentsMargins(12, 10, 12, 10)
        self.lbl_name = QLabel(self.form_card)
        self.lbl_name.setObjectName(u"lbl_name")

        self.form_layout.addWidget(self.lbl_name, 0, 0, 1, 1)

        self.e_name = QLineEdit(self.form_card)
        self.e_name.setObjectName(u"e_name")

        self.form_layout.addWidget(self.e_name, 0, 1, 1, 1)

        self.lbl_quality = QLabel(self.form_card)
        self.lbl_quality.setObjectName(u"lbl_quality")

        self.form_layout.addWidget(self.lbl_quality, 1, 0, 1, 1)

        self.e_quality = QLineEdit(self.form_card)
        self.e_quality.setObjectName(u"e_quality")

        self.form_layout.addWidget(self.e_quality, 1, 1, 1, 1)

        self.lbl_specific_weight = QLabel(self.form_card)
        self.lbl_specific_weight.setObjectName(u"lbl_specific_weight")

        self.form_layout.addWidget(self.lbl_specific_weight, 2, 0, 1, 1)

        self.e_specific_weight = QLineEdit(self.form_card)
        self.e_specific_weight.setObjectName(u"e_specific_weight")

        self.form_layout.addWidget(self.e_specific_weight, 2, 1, 1, 1)

        self.hint = QLabel(self.form_card)
        self.hint.setObjectName(u"hint")
        self.hint.setWordWrap(True)

        self.form_layout.addWidget(self.hint, 3, 0, 1, 2)

        self.form_btns_layout = QHBoxLayout()
        self.form_btns_layout.setObjectName(u"form_btns_layout")
        self.form_btns_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.form_btns_layout.addItem(self.form_btns_spacer)

        self.save_btn = QPushButton(self.form_card)
        self.save_btn.setObjectName(u"save_btn")

        self.form_btns_layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton(self.form_card)
        self.clear_btn.setObjectName(u"clear_btn")

        self.form_btns_layout.addWidget(self.clear_btn)


        self.form_layout.addLayout(self.form_btns_layout, 4, 0, 1, 2)


        self.main_layout.addWidget(self.form_card)

        self.scroll = QScrollArea(MaterialsManagerDialog)
        self.scroll.setObjectName(u"scroll")
        self.scroll.setWidgetResizable(True)
        self.list_widget = QWidget()
        self.list_widget.setObjectName(u"list_widget")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(2)
        self.list_layout.setObjectName(u"list_layout")
        self.list_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.list_widget)

        self.main_layout.addWidget(self.scroll)

        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setObjectName(u"bottom_layout")
        self.bottom_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bottom_layout.addItem(self.bottom_spacer)

        self.del_btn = QPushButton(MaterialsManagerDialog)
        self.del_btn.setObjectName(u"del_btn")

        self.bottom_layout.addWidget(self.del_btn)


        self.main_layout.addLayout(self.bottom_layout)


        self.retranslateUi(MaterialsManagerDialog)

        QMetaObject.connectSlotsByName(MaterialsManagerDialog)
    # setupUi

    def retranslateUi(self, MaterialsManagerDialog):
        MaterialsManagerDialog.setWindowTitle(QCoreApplication.translate("MaterialsManagerDialog", u"Materials Manager", None))
        self.title.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Materials Manager", None))
        self.lbl_name.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Name *", None))
        self.e_name.setPlaceholderText(QCoreApplication.translate("MaterialsManagerDialog", u"Name", None))
        self.lbl_quality.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Quality", None))
        self.e_quality.setPlaceholderText(QCoreApplication.translate("MaterialsManagerDialog", u"Quality", None))
        self.lbl_specific_weight.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Specific Weight", None))
        self.e_specific_weight.setPlaceholderText(QCoreApplication.translate("MaterialsManagerDialog", u"7.85", None))
        self.hint.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Hint text", None))
        self.save_btn.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Save", None))
        self.clear_btn.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Clear", None))
        self.del_btn.setText(QCoreApplication.translate("MaterialsManagerDialog", u"Delete", None))
    # retranslateUi

