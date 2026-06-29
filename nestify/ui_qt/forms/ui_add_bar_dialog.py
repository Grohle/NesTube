# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_bar_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_AddBarDialog(object):
    def setupUi(self, AddBarDialog):
        if not AddBarDialog.objectName():
            AddBarDialog.setObjectName(u"AddBarDialog")
        AddBarDialog.resize(450, 400)
        AddBarDialog.setMinimumSize(QSize(380, 300))
        AddBarDialog.setModal(True)
        self.main_layout = QVBoxLayout(AddBarDialog)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.retranslateUi(AddBarDialog)

        QMetaObject.connectSlotsByName(AddBarDialog)
    # setupUi

    def retranslateUi(self, AddBarDialog):
        AddBarDialog.setWindowTitle(QCoreApplication.translate("AddBarDialog", u"Add Bar", None))
    # retranslateUi

