# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'profile_save_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_ProfileSaveDialog(object):
    def setupUi(self, ProfileSaveDialog):
        if not ProfileSaveDialog.objectName():
            ProfileSaveDialog.setObjectName(u"ProfileSaveDialog")
        ProfileSaveDialog.resize(440, 440)
        ProfileSaveDialog.setMinimumSize(QSize(360, 380))
        ProfileSaveDialog.setModal(True)
        self.main_layout = QVBoxLayout(ProfileSaveDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.form_layout = QFormLayout()
        self.form_layout.setObjectName(u"form_layout")
        self.lbl_name = QLabel(ProfileSaveDialog)
        self.lbl_name.setObjectName(u"lbl_name")

        self.form_layout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_name)

        self.e_name = QLineEdit(ProfileSaveDialog)
        self.e_name.setObjectName(u"e_name")

        self.form_layout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.e_name)

        self.lbl_material = QLabel(ProfileSaveDialog)
        self.lbl_material.setObjectName(u"lbl_material")

        self.form_layout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_material)

        self.combo_material = QComboBox(ProfileSaveDialog)
        self.combo_material.setObjectName(u"combo_material")
        self.combo_material.setEditable(True)

        self.form_layout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.combo_material)

        self.lbl_sw = QLabel(ProfileSaveDialog)
        self.lbl_sw.setObjectName(u"lbl_sw")

        self.form_layout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_sw)

        self.lbl_sw_value = QLabel(ProfileSaveDialog)
        self.lbl_sw_value.setObjectName(u"lbl_sw_value")

        self.form_layout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lbl_sw_value)

        self.lbl_quality = QLabel(ProfileSaveDialog)
        self.lbl_quality.setObjectName(u"lbl_quality")

        self.form_layout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_quality)

        self.e_quality = QLineEdit(ProfileSaveDialog)
        self.e_quality.setObjectName(u"e_quality")

        self.form_layout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.e_quality)

        self.lbl_notes = QLabel(ProfileSaveDialog)
        self.lbl_notes.setObjectName(u"lbl_notes")

        self.form_layout.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lbl_notes)

        self.e_notes = QTextEdit(ProfileSaveDialog)
        self.e_notes.setObjectName(u"e_notes")
        self.e_notes.setMaximumSize(QSize(16777215, 80))

        self.form_layout.setWidget(4, QFormLayout.ItemRole.FieldRole, self.e_notes)

        self.lbl_fields = QLabel(ProfileSaveDialog)
        self.lbl_fields.setObjectName(u"lbl_fields")

        self.form_layout.setWidget(5, QFormLayout.ItemRole.LabelRole, self.lbl_fields)

        self.e_fields = QLineEdit(ProfileSaveDialog)
        self.e_fields.setObjectName(u"e_fields")

        self.form_layout.setWidget(5, QFormLayout.ItemRole.FieldRole, self.e_fields)


        self.main_layout.addLayout(self.form_layout)

        self.lbl_hint = QLabel(ProfileSaveDialog)
        self.lbl_hint.setObjectName(u"lbl_hint")
        self.lbl_hint.setWordWrap(True)

        self.main_layout.addWidget(self.lbl_hint)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.verticalSpacer)

        self.button_box = QDialogButtonBox(ProfileSaveDialog)
        self.button_box.setObjectName(u"button_box")
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)

        self.main_layout.addWidget(self.button_box)


        self.retranslateUi(ProfileSaveDialog)

        QMetaObject.connectSlotsByName(ProfileSaveDialog)
    # setupUi

    def retranslateUi(self, ProfileSaveDialog):
        ProfileSaveDialog.setWindowTitle(QCoreApplication.translate("ProfileSaveDialog", u"Save Profile", None))
        self.lbl_name.setText(QCoreApplication.translate("ProfileSaveDialog", u"Name *", None))
        self.e_name.setPlaceholderText(QCoreApplication.translate("ProfileSaveDialog", u"Name", None))
        self.lbl_material.setText(QCoreApplication.translate("ProfileSaveDialog", u"Material", None))
        self.lbl_sw.setText(QCoreApplication.translate("ProfileSaveDialog", u"Specific Weight", None))
        self.lbl_sw_value.setText(QCoreApplication.translate("ProfileSaveDialog", u"\u2014", None))
        self.lbl_quality.setText(QCoreApplication.translate("ProfileSaveDialog", u"Quality", None))
        self.e_quality.setPlaceholderText(QCoreApplication.translate("ProfileSaveDialog", u"Quality", None))
        self.lbl_notes.setText(QCoreApplication.translate("ProfileSaveDialog", u"Notes", None))
        self.lbl_fields.setText(QCoreApplication.translate("ProfileSaveDialog", u"Fields", None))
        self.lbl_hint.setText(QCoreApplication.translate("ProfileSaveDialog", u"Hint text", None))
    # retranslateUi

