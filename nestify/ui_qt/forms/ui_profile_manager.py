# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'profile_manager.ui'
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
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_ProfileManager(object):
    def setupUi(self, ProfileManager):
        if not ProfileManager.objectName():
            ProfileManager.setObjectName(u"ProfileManager")
        ProfileManager.resize(540, 500)
        ProfileManager.setMinimumSize(QSize(480, 420))
        ProfileManager.setModal(True)
        self.main_layout = QVBoxLayout(ProfileManager)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(12, 12, 12, 16)
        self.title = QLabel(ProfileManager)
        self.title.setObjectName(u"title")

        self.main_layout.addWidget(self.title)

        self.scroll = QScrollArea(ProfileManager)
        self.scroll.setObjectName(u"scroll")
        self.scroll.setWidgetResizable(True)
        self.list_widget = QWidget()
        self.list_widget.setObjectName(u"list_widget")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(3)
        self.list_layout.setObjectName(u"list_layout")
        self.list_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.list_widget)

        self.main_layout.addWidget(self.scroll)

        self.btn_grid = QHBoxLayout()
        self.btn_grid.setObjectName(u"btn_grid")
        self.img_btn = QPushButton(ProfileManager)
        self.img_btn.setObjectName(u"img_btn")

        self.btn_grid.addWidget(self.img_btn)

        self.fields_btn = QPushButton(ProfileManager)
        self.fields_btn.setObjectName(u"fields_btn")

        self.btn_grid.addWidget(self.fields_btn)


        self.main_layout.addLayout(self.btn_grid)

        self.btn_grid2 = QHBoxLayout()
        self.btn_grid2.setObjectName(u"btn_grid2")
        self.draw_btn = QPushButton(ProfileManager)
        self.draw_btn.setObjectName(u"draw_btn")

        self.btn_grid2.addWidget(self.draw_btn)

        self.del_btn = QPushButton(ProfileManager)
        self.del_btn.setObjectName(u"del_btn")

        self.btn_grid2.addWidget(self.del_btn)


        self.main_layout.addLayout(self.btn_grid2)


        self.retranslateUi(ProfileManager)

        QMetaObject.connectSlotsByName(ProfileManager)
    # setupUi

    def retranslateUi(self, ProfileManager):
        ProfileManager.setWindowTitle(QCoreApplication.translate("ProfileManager", u"Profile Manager", None))
        self.title.setText(QCoreApplication.translate("ProfileManager", u"Profile Manager", None))
        self.img_btn.setText(QCoreApplication.translate("ProfileManager", u"Assign Image", None))
        self.fields_btn.setText(QCoreApplication.translate("ProfileManager", u"Edit Fields", None))
        self.draw_btn.setText(QCoreApplication.translate("ProfileManager", u"Creator Tools", None))
        self.del_btn.setText(QCoreApplication.translate("ProfileManager", u"Delete", None))
    # retranslateUi

