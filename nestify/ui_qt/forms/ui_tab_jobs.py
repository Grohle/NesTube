# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_jobs.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_TabJobsExplorer(object):
    def setupUi(self, TabJobsExplorer):
        if not TabJobsExplorer.objectName():
            TabJobsExplorer.setObjectName(u"TabJobsExplorer")
        TabJobsExplorer.resize(860, 500)
        self.main_layout = QHBoxLayout(TabJobsExplorer)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(TabJobsExplorer)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.list_panel = QWidget(self.splitter)
        self.list_panel.setObjectName(u"list_panel")
        self.list_panel.setMinimumSize(QSize(220, 0))
        self.list_panel.setMaximumSize(QSize(340, 16777215))
        self.list_panel_layout = QVBoxLayout(self.list_panel)
        self.list_panel_layout.setSpacing(0)
        self.list_panel_layout.setObjectName(u"list_panel_layout")
        self.list_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.header = QWidget(self.list_panel)
        self.header.setObjectName(u"header")
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setObjectName(u"header_layout")
        self.header_layout.setContentsMargins(12, 12, 12, 6)
        self.title = QLabel(self.header)
        self.title.setObjectName(u"title")

        self.header_layout.addWidget(self.title)

        self.header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.header_layout.addItem(self.header_spacer)

        self.new_btn = QPushButton(self.header)
        self.new_btn.setObjectName(u"new_btn")
        self.new_btn.setProperty(u"fixedHeight", 28)
        self.new_btn.setMinimumSize(QSize(0, 28))
        self.new_btn.setMaximumSize(QSize(16777215, 28))

        self.header_layout.addWidget(self.new_btn)


        self.list_panel_layout.addWidget(self.header)

        self.search_widget = QWidget(self.list_panel)
        self.search_widget.setObjectName(u"search_widget")
        self.search_layout = QHBoxLayout(self.search_widget)
        self.search_layout.setSpacing(4)
        self.search_layout.setObjectName(u"search_layout")
        self.search_layout.setContentsMargins(8, 0, 8, 4)
        self.search_field = QComboBox(self.search_widget)
        self.search_field.setObjectName(u"search_field")
        self.search_field.setMinimumSize(QSize(100, 26))
        self.search_field.setMaximumSize(QSize(100, 26))

        self.search_layout.addWidget(self.search_field)

        self.search_entry = QLineEdit(self.search_widget)
        self.search_entry.setObjectName(u"search_entry")
        self.search_entry.setMinimumSize(QSize(0, 26))
        self.search_entry.setMaximumSize(QSize(16777215, 26))

        self.search_layout.addWidget(self.search_entry)

        self.search_btn = QPushButton(self.search_widget)
        self.search_btn.setObjectName(u"search_btn")
        self.search_btn.setText(u"\U0001f50d")
        self.search_btn.setMinimumSize(QSize(26, 26))
        self.search_btn.setMaximumSize(QSize(26, 26))

        self.search_layout.addWidget(self.search_btn)

        self.clear_btn = QPushButton(self.search_widget)
        self.clear_btn.setObjectName(u"clear_btn")
        self.clear_btn.setText(u"\u2715")
        self.clear_btn.setMinimumSize(QSize(26, 26))
        self.clear_btn.setMaximumSize(QSize(26, 26))

        self.search_layout.addWidget(self.clear_btn)


        self.list_panel_layout.addWidget(self.search_widget)

        self.list_scroll = QScrollArea(self.list_panel)
        self.list_scroll.setObjectName(u"list_scroll")
        self.list_scroll.setFrameShape(QFrame.NoFrame)
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_container = QWidget()
        self.list_container.setObjectName(u"list_container")
        self.list_container.setGeometry(QRect(0, 0, 220, 400))
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(4)
        self.list_layout.setObjectName(u"list_layout")
        self.list_layout.setContentsMargins(4, 0, 4, 4)
        self.list_scroll.setWidget(self.list_container)

        self.list_panel_layout.addWidget(self.list_scroll)

        self.splitter.addWidget(self.list_panel)
        self.detail_outer = QWidget(self.splitter)
        self.detail_outer.setObjectName(u"detail_outer")
        self.detail_outer_layout = QVBoxLayout(self.detail_outer)
        self.detail_outer_layout.setObjectName(u"detail_outer_layout")
        self.detail_outer_layout.setContentsMargins(8, 8, 8, 8)
        self.detail_placeholder = QLabel(self.detail_outer)
        self.detail_placeholder.setObjectName(u"detail_placeholder")
        self.detail_placeholder.setAlignment(Qt.AlignTop|Qt.AlignHCenter)

        self.detail_outer_layout.addWidget(self.detail_placeholder)

        self.detail_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.detail_outer_layout.addItem(self.detail_spacer)

        self.detail_card = QFrame(self.detail_outer)
        self.detail_card.setObjectName(u"detail_card")
        self.detail_card.setVisible(False)
        self.detail_card_layout = QVBoxLayout(self.detail_card)
        self.detail_card_layout.setSpacing(6)
        self.detail_card_layout.setObjectName(u"detail_card_layout")
        self.detail_card_layout.setContentsMargins(12, 12, 12, 10)
        self.detail_hdr = QWidget(self.detail_card)
        self.detail_hdr.setObjectName(u"detail_hdr")
        self.detail_hdr_layout = QHBoxLayout(self.detail_hdr)
        self.detail_hdr_layout.setObjectName(u"detail_hdr_layout")
        self.detail_hdr_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_name_lbl = QLineEdit(self.detail_hdr)
        self.detail_name_lbl.setObjectName(u"detail_name_lbl")

        self.detail_hdr_layout.addWidget(self.detail_name_lbl)

        self.detail_hdr_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.detail_hdr_layout.addItem(self.detail_hdr_spacer)

        self.detail_date_lbl = QLabel(self.detail_hdr)
        self.detail_date_lbl.setObjectName(u"detail_date_lbl")

        self.detail_hdr_layout.addWidget(self.detail_date_lbl)


        self.detail_card_layout.addWidget(self.detail_hdr)

        self.meta_widget = QWidget(self.detail_card)
        self.meta_widget.setObjectName(u"meta_widget")
        self.meta_grid = QGridLayout(self.meta_widget)
        self.meta_grid.setSpacing(4)
        self.meta_grid.setObjectName(u"meta_grid")
        self.meta_grid.setContentsMargins(0, 0, 0, 0)
        self.key_client = QLabel(self.meta_widget)
        self.key_client.setObjectName(u"key_client")
        self.key_client.setMinimumSize(QSize(80, 0))
        self.key_client.setMaximumSize(QSize(80, 16777215))

        self.meta_grid.addWidget(self.key_client, 0, 0, 1, 1)

        self.detail_client_lbl = QLineEdit(self.meta_widget)
        self.detail_client_lbl.setObjectName(u"detail_client_lbl")

        self.meta_grid.addWidget(self.detail_client_lbl, 0, 1, 1, 1)

        self.key_offer = QLabel(self.meta_widget)
        self.key_offer.setObjectName(u"key_offer")
        self.key_offer.setMinimumSize(QSize(80, 0))
        self.key_offer.setMaximumSize(QSize(80, 16777215))

        self.meta_grid.addWidget(self.key_offer, 0, 2, 1, 1)

        self.detail_offer_lbl = QLineEdit(self.meta_widget)
        self.detail_offer_lbl.setObjectName(u"detail_offer_lbl")

        self.meta_grid.addWidget(self.detail_offer_lbl, 0, 3, 1, 1)

        self.key_order = QLabel(self.meta_widget)
        self.key_order.setObjectName(u"key_order")
        self.key_order.setMinimumSize(QSize(80, 0))
        self.key_order.setMaximumSize(QSize(80, 16777215))

        self.meta_grid.addWidget(self.key_order, 1, 0, 1, 1)

        self.detail_order_lbl = QLineEdit(self.meta_widget)
        self.detail_order_lbl.setObjectName(u"detail_order_lbl")

        self.meta_grid.addWidget(self.detail_order_lbl, 1, 1, 1, 1)

        self.key_desc = QLabel(self.meta_widget)
        self.key_desc.setObjectName(u"key_desc")
        self.key_desc.setMinimumSize(QSize(80, 0))
        self.key_desc.setMaximumSize(QSize(80, 16777215))

        self.meta_grid.addWidget(self.key_desc, 1, 2, 1, 1)

        self.detail_desc_lbl = QLineEdit(self.meta_widget)
        self.detail_desc_lbl.setObjectName(u"detail_desc_lbl")

        self.meta_grid.addWidget(self.detail_desc_lbl, 1, 3, 1, 1)


        self.detail_card_layout.addWidget(self.meta_widget)

        self.pieces_table = QTableWidget(self.detail_card)
        if (self.pieces_table.columnCount() < 4):
            self.pieces_table.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.pieces_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.pieces_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.pieces_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.pieces_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.pieces_table.setObjectName(u"pieces_table")
        self.pieces_table.setMinimumSize(QSize(0, 120))

        self.detail_card_layout.addWidget(self.pieces_table)

        self.btn_row = QWidget(self.detail_card)
        self.btn_row.setObjectName(u"btn_row")
        self.btn_row_layout = QHBoxLayout(self.btn_row)
        self.btn_row_layout.setSpacing(8)
        self.btn_row_layout.setObjectName(u"btn_row_layout")
        self.btn_row_layout.setContentsMargins(0, 0, 0, 0)
        self.save_changes_btn = QPushButton(self.btn_row)
        self.save_changes_btn.setObjectName(u"save_changes_btn")

        self.btn_row_layout.addWidget(self.save_changes_btn)

        self.open_btn = QPushButton(self.btn_row)
        self.open_btn.setObjectName(u"open_btn")

        self.btn_row_layout.addWidget(self.open_btn)

        self.del_btn = QPushButton(self.btn_row)
        self.del_btn.setObjectName(u"del_btn")

        self.btn_row_layout.addWidget(self.del_btn)


        self.detail_card_layout.addWidget(self.btn_row)


        self.detail_outer_layout.addWidget(self.detail_card)

        self.splitter.addWidget(self.detail_outer)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(TabJobsExplorer)

        QMetaObject.connectSlotsByName(TabJobsExplorer)
    # setupUi

    def retranslateUi(self, TabJobsExplorer):
        self.title.setText(QCoreApplication.translate("TabJobsExplorer", u"Jobs", None))
        self.new_btn.setText(QCoreApplication.translate("TabJobsExplorer", u"New Job", None))
        self.search_entry.setPlaceholderText(QCoreApplication.translate("TabJobsExplorer", u"Search...", None))
        self.detail_placeholder.setText(QCoreApplication.translate("TabJobsExplorer", u"Select a job to view details", None))
        self.detail_name_lbl.setText("")
        self.detail_date_lbl.setText("")
        self.key_client.setText(QCoreApplication.translate("TabJobsExplorer", u"Client:", None))
        self.detail_client_lbl.setText("")
        self.key_offer.setText(QCoreApplication.translate("TabJobsExplorer", u"Offer:", None))
        self.detail_offer_lbl.setText("")
        self.key_order.setText(QCoreApplication.translate("TabJobsExplorer", u"Order:", None))
        self.detail_order_lbl.setText("")
        self.key_desc.setText(QCoreApplication.translate("TabJobsExplorer", u"Description:", None))
        self.detail_desc_lbl.setText("")
        ___qtablewidgetitem = self.pieces_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("TabJobsExplorer", u"#", None))
        ___qtablewidgetitem1 = self.pieces_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("TabJobsExplorer", u"Description", None))
        ___qtablewidgetitem2 = self.pieces_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("TabJobsExplorer", u"Length (mm)", None))
        ___qtablewidgetitem3 = self.pieces_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("TabJobsExplorer", u"Qty", None))
        self.save_changes_btn.setText(QCoreApplication.translate("TabJobsExplorer", u"Save changes", None))
        self.open_btn.setText(QCoreApplication.translate("TabJobsExplorer", u"Open", None))
        self.del_btn.setText(QCoreApplication.translate("TabJobsExplorer", u"Delete", None))
        pass
    # retranslateUi

