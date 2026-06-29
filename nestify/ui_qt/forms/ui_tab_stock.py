# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_stock.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_TabStock(object):
    def setupUi(self, TabStock):
        if not TabStock.objectName():
            TabStock.setObjectName(u"TabStock")
        TabStock.resize(900, 550)
        self.main_layout = QVBoxLayout(TabStock)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar = QFrame(TabStock)
        self.toolbar.setObjectName(u"toolbar")
        self.toolbar.setMinimumSize(QSize(0, 88))
        self.toolbar.setMaximumSize(QSize(16777215, 88))
        self.toolbar_layout = QVBoxLayout(self.toolbar)
        self.toolbar_layout.setSpacing(4)
        self.toolbar_layout.setObjectName(u"toolbar_layout")
        self.toolbar_layout.setContentsMargins(8, 6, 8, 4)
        self.row0 = QWidget(self.toolbar)
        self.row0.setObjectName(u"row0")
        self.row0_layout = QHBoxLayout(self.row0)
        self.row0_layout.setSpacing(6)
        self.row0_layout.setObjectName(u"row0_layout")
        self.row0_layout.setContentsMargins(0, 0, 0, 0)
        self.add_btn = QPushButton(self.row0)
        self.add_btn.setObjectName(u"add_btn")
        self.add_btn.setMinimumSize(QSize(0, 30))
        self.add_btn.setMaximumSize(QSize(16777215, 30))

        self.row0_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton(self.row0)
        self.edit_btn.setObjectName(u"edit_btn")
        self.edit_btn.setMinimumSize(QSize(0, 30))
        self.edit_btn.setMaximumSize(QSize(16777215, 30))

        self.row0_layout.addWidget(self.edit_btn)

        self.del_btn = QPushButton(self.row0)
        self.del_btn.setObjectName(u"del_btn")
        self.del_btn.setMinimumSize(QSize(0, 30))
        self.del_btn.setMaximumSize(QSize(16777215, 30))

        self.row0_layout.addWidget(self.del_btn)

        self.row0_spacer1 = QSpacerItem(8, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.row0_layout.addItem(self.row0_spacer1)

        self.filter_entry = QLineEdit(self.row0)
        self.filter_entry.setObjectName(u"filter_entry")
        self.filter_entry.setMinimumSize(QSize(200, 28))
        self.filter_entry.setMaximumSize(QSize(200, 28))

        self.row0_layout.addWidget(self.filter_entry)

        self.profile_combo = QComboBox(self.row0)
        self.profile_combo.setObjectName(u"profile_combo")
        self.profile_combo.setMinimumSize(QSize(160, 28))
        self.profile_combo.setMaximumSize(QSize(160, 28))

        self.row0_layout.addWidget(self.profile_combo)

        self.row0_spacer2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.row0_layout.addItem(self.row0_spacer2)

        self.summary_lbl = QLabel(self.row0)
        self.summary_lbl.setObjectName(u"summary_lbl")

        self.row0_layout.addWidget(self.summary_lbl)


        self.toolbar_layout.addWidget(self.row0)

        self.row1 = QWidget(self.toolbar)
        self.row1.setObjectName(u"row1")
        self.row1_layout = QHBoxLayout(self.row1)
        self.row1_layout.setSpacing(6)
        self.row1_layout.setObjectName(u"row1_layout")
        self.row1_layout.setContentsMargins(0, 0, 0, 0)
        self.select_all_cb = QCheckBox(self.row1)
        self.select_all_cb.setObjectName(u"select_all_cb")

        self.row1_layout.addWidget(self.select_all_cb)

        self.row1_spacer1 = QSpacerItem(12, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.row1_layout.addItem(self.row1_spacer1)

        self.lbl_min_length = QLabel(self.row1)
        self.lbl_min_length.setObjectName(u"lbl_min_length")

        self.row1_layout.addWidget(self.lbl_min_length)

        self.min_length_entry = QLineEdit(self.row1)
        self.min_length_entry.setObjectName(u"min_length_entry")
        self.min_length_entry.setMinimumSize(QSize(70, 24))
        self.min_length_entry.setMaximumSize(QSize(70, 24))

        self.row1_layout.addWidget(self.min_length_entry)

        self.row1_spacer2 = QSpacerItem(8, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.row1_layout.addItem(self.row1_spacer2)

        self.lbl_max_length = QLabel(self.row1)
        self.lbl_max_length.setObjectName(u"lbl_max_length")

        self.row1_layout.addWidget(self.lbl_max_length)

        self.max_length_entry = QLineEdit(self.row1)
        self.max_length_entry.setObjectName(u"max_length_entry")
        self.max_length_entry.setMinimumSize(QSize(70, 24))
        self.max_length_entry.setMaximumSize(QSize(70, 24))
        self.max_length_entry.setPlaceholderText(u"\u221e")

        self.row1_layout.addWidget(self.max_length_entry)

        self.row1_spacer3 = QSpacerItem(8, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.row1_layout.addItem(self.row1_spacer3)

        self.lbl_min_retal = QLabel(self.row1)
        self.lbl_min_retal.setObjectName(u"lbl_min_retal")

        self.row1_layout.addWidget(self.lbl_min_retal)

        self.min_retal_entry = QLineEdit(self.row1)
        self.min_retal_entry.setObjectName(u"min_retal_entry")
        self.min_retal_entry.setMinimumSize(QSize(70, 24))
        self.min_retal_entry.setMaximumSize(QSize(70, 24))

        self.row1_layout.addWidget(self.min_retal_entry)

        self.row1_spacer4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.row1_layout.addItem(self.row1_spacer4)


        self.toolbar_layout.addWidget(self.row1)


        self.main_layout.addWidget(self.toolbar)

        self.table_frame = QFrame(TabStock)
        self.table_frame.setObjectName(u"table_frame")
        self.table_frame_layout = QVBoxLayout(self.table_frame)
        self.table_frame_layout.setObjectName(u"table_frame_layout")
        self.table_frame_layout.setContentsMargins(4, 4, 4, 4)
        self.table = QTableWidget(self.table_frame)
        if (self.table.columnCount() < 10):
            self.table.setColumnCount(10)
        __qtablewidgetitem = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        __qtablewidgetitem1.setText(u"\u25cf")
        self.table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(8, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.table.setHorizontalHeaderItem(9, __qtablewidgetitem9)
        self.table.setObjectName(u"table")
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table_frame_layout.addWidget(self.table)


        self.main_layout.addWidget(self.table_frame)


        self.retranslateUi(TabStock)

        QMetaObject.connectSlotsByName(TabStock)
    # setupUi

    def retranslateUi(self, TabStock):
        self.add_btn.setText(QCoreApplication.translate("TabStock", u"+ Add to Stock", None))
        self.edit_btn.setText(QCoreApplication.translate("TabStock", u"Edit", None))
        self.del_btn.setText(QCoreApplication.translate("TabStock", u"Remove", None))
        self.filter_entry.setPlaceholderText(QCoreApplication.translate("TabStock", u"Filter profile...", None))
        self.summary_lbl.setText("")
        self.select_all_cb.setText(QCoreApplication.translate("TabStock", u"Select all", None))
        self.lbl_min_length.setText(QCoreApplication.translate("TabStock", u"Min length", None))
        self.min_length_entry.setPlaceholderText(QCoreApplication.translate("TabStock", u"0", None))
        self.lbl_max_length.setText(QCoreApplication.translate("TabStock", u"Max length", None))
        self.lbl_min_retal.setText(QCoreApplication.translate("TabStock", u"Min retal length", None))
        ___qtablewidgetitem = self.table.horizontalHeaderItem(2)
        ___qtablewidgetitem.setText(QCoreApplication.translate("TabStock", u"Profile", None))
        ___qtablewidgetitem1 = self.table.horizontalHeaderItem(3)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("TabStock", u"Material", None))
        ___qtablewidgetitem2 = self.table.horizontalHeaderItem(4)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("TabStock", u"Length", None))
        ___qtablewidgetitem3 = self.table.horizontalHeaderItem(5)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("TabStock", u"Qty", None))
        ___qtablewidgetitem4 = self.table.horizontalHeaderItem(6)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("TabStock", u"Available", None))
        ___qtablewidgetitem5 = self.table.horizontalHeaderItem(7)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("TabStock", u"Retal", None))
        ___qtablewidgetitem6 = self.table.horizontalHeaderItem(8)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("TabStock", u"Creation Job", None))
        ___qtablewidgetitem7 = self.table.horizontalHeaderItem(9)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("TabStock", u"Used In Jobs", None))
        pass
    # retranslateUi

