# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'nesting_layout_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_NestingLayoutDialog(object):
    def setupUi(self, NestingLayoutDialog):
        if not NestingLayoutDialog.objectName():
            NestingLayoutDialog.setObjectName(u"NestingLayoutDialog")
        NestingLayoutDialog.resize(440, 340)
        NestingLayoutDialog.setModal(True)
        self.main_layout = QVBoxLayout(NestingLayoutDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.title = QLabel(NestingLayoutDialog)
        self.title.setObjectName(u"title")

        self.main_layout.addWidget(self.title)

        self.form_layout = QFormLayout()
        self.form_layout.setObjectName(u"form_layout")
        self.form_layout.setContentsMargins(8, 8, 8, 8)
        self.lbl_pieces = QLabel(NestingLayoutDialog)
        self.lbl_pieces.setObjectName(u"lbl_pieces")

        self.form_layout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_pieces)

        self.pieces_combo = QComboBox(NestingLayoutDialog)
        self.pieces_combo.setObjectName(u"pieces_combo")

        self.form_layout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.pieces_combo)

        self.lbl_bars = QLabel(NestingLayoutDialog)
        self.lbl_bars.setObjectName(u"lbl_bars")

        self.form_layout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_bars)

        self.bars_combo = QComboBox(NestingLayoutDialog)
        self.bars_combo.setObjectName(u"bars_combo")

        self.form_layout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.bars_combo)

        self.hint = QLabel(NestingLayoutDialog)
        self.hint.setObjectName(u"hint")
        self.hint.setWordWrap(True)

        self.form_layout.setWidget(2, QFormLayout.ItemRole.SpanningRole, self.hint)

        self.lbl_snap_zone = QLabel(NestingLayoutDialog)
        self.lbl_snap_zone.setObjectName(u"lbl_snap_zone")

        self.form_layout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_snap_zone)

        self.snap_zone = QLineEdit(NestingLayoutDialog)
        self.snap_zone.setObjectName(u"snap_zone")
        self.snap_zone.setProperty(u"fixedWidth", 80)
        self.snap_zone.setMaximumSize(QSize(80, 16777215))

        self.form_layout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.snap_zone)

        self.use_colors = QCheckBox(NestingLayoutDialog)
        self.use_colors.setObjectName(u"use_colors")

        self.form_layout.setWidget(4, QFormLayout.ItemRole.SpanningRole, self.use_colors)


        self.main_layout.addLayout(self.form_layout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.verticalSpacer)

        self.button_box = QDialogButtonBox(NestingLayoutDialog)
        self.button_box.setObjectName(u"button_box")
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)

        self.main_layout.addWidget(self.button_box)


        self.retranslateUi(NestingLayoutDialog)

        QMetaObject.connectSlotsByName(NestingLayoutDialog)
    # setupUi

    def retranslateUi(self, NestingLayoutDialog):
        NestingLayoutDialog.setWindowTitle(QCoreApplication.translate("NestingLayoutDialog", u"Nesting Layout Settings", None))
        self.title.setText(QCoreApplication.translate("NestingLayoutDialog", u"Nesting Layout Settings", None))
        self.lbl_pieces.setText(QCoreApplication.translate("NestingLayoutDialog", u"Pieces Panel", None))
        self.lbl_bars.setText(QCoreApplication.translate("NestingLayoutDialog", u"Bars Panel", None))
        self.hint.setText(QCoreApplication.translate("NestingLayoutDialog", u"Hint text", None))
        self.lbl_snap_zone.setText(QCoreApplication.translate("NestingLayoutDialog", u"Snap Zone (mm)", None))
        self.use_colors.setText(QCoreApplication.translate("NestingLayoutDialog", u"Use Cut Colors", None))
    # retranslateUi

