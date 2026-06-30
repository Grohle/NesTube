# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_cortes.ui'
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
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QSplitter,
    QVBoxLayout, QWidget)

class Ui_TabCortes(object):
    def setupUi(self, TabCortes):
        if not TabCortes.objectName():
            TabCortes.setObjectName(u"TabCortes")
        TabCortes.resize(900, 600)
        self.main_layout = QVBoxLayout(TabCortes)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.header_card = QFrame(TabCortes)
        self.header_card.setObjectName(u"header_card")
        self.header_grid = QGridLayout(self.header_card)
        self.header_grid.setSpacing(8)
        self.header_grid.setObjectName(u"header_grid")
        self.header_grid.setContentsMargins(8, 6, 8, 6)
        self.mat_ac_placeholder = QWidget(self.header_card)
        self.mat_ac_placeholder.setObjectName(u"mat_ac_placeholder")

        self.header_grid.addWidget(self.mat_ac_placeholder, 0, 0, 1, 2)

        self.e_pedido = QLineEdit(self.header_card)
        self.e_pedido.setObjectName(u"e_pedido")

        self.header_grid.addWidget(self.e_pedido, 0, 2, 1, 1)

        self.e_oferta = QLineEdit(self.header_card)
        self.e_oferta.setObjectName(u"e_oferta")

        self.header_grid.addWidget(self.e_oferta, 0, 3, 1, 1)

        self.e_cliente = QLineEdit(self.header_card)
        self.e_cliente.setObjectName(u"e_cliente")

        self.header_grid.addWidget(self.e_cliente, 1, 0, 1, 1)

        self.field_btns = QWidget(self.header_card)
        self.field_btns.setObjectName(u"field_btns")
        self.field_btns_layout = QHBoxLayout(self.field_btns)
        self.field_btns_layout.setSpacing(4)
        self.field_btns_layout.setObjectName(u"field_btns_layout")
        self.field_btns_layout.setContentsMargins(0, 0, 0, 0)
        self.add_field_btn = QPushButton(self.field_btns)
        self.add_field_btn.setObjectName(u"add_field_btn")
        self.add_field_btn.setMinimumSize(QSize(0, 22))
        self.add_field_btn.setMaximumSize(QSize(16777215, 22))

        self.field_btns_layout.addWidget(self.add_field_btn)

        self.edit_fields_btn = QPushButton(self.field_btns)
        self.edit_fields_btn.setObjectName(u"edit_fields_btn")
        self.edit_fields_btn.setMinimumSize(QSize(0, 22))
        self.edit_fields_btn.setMaximumSize(QSize(16777215, 22))

        self.field_btns_layout.addWidget(self.edit_fields_btn)

        self.field_btns_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.field_btns_layout.addItem(self.field_btns_spacer)


        self.header_grid.addWidget(self.field_btns, 1, 1, 1, 3)

        self.custom_fields_widget = QWidget(self.header_card)
        self.custom_fields_widget.setObjectName(u"custom_fields_widget")
        self.custom_fields_widget.setVisible(False)
        self.custom_fields_layout = QHBoxLayout(self.custom_fields_widget)
        self.custom_fields_layout.setSpacing(6)
        self.custom_fields_layout.setObjectName(u"custom_fields_layout")
        self.custom_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_fields_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.custom_fields_layout.addItem(self.custom_fields_spacer)


        self.header_grid.addWidget(self.custom_fields_widget, 2, 0, 1, 4)


        self.main_layout.addWidget(self.header_card)

        self.controls_card = QFrame(TabCortes)
        self.controls_card.setObjectName(u"controls_card")
        self.controls_layout = QHBoxLayout(self.controls_card)
        self.controls_layout.setSpacing(12)
        self.controls_layout.setObjectName(u"controls_layout")
        self.controls_layout.setContentsMargins(8, 10, 8, 10)
        self.lbl_kerf = QLabel(self.controls_card)
        self.lbl_kerf.setObjectName(u"lbl_kerf")

        self.controls_layout.addWidget(self.lbl_kerf)

        self.e_kerf = QLineEdit(self.controls_card)
        self.e_kerf.setObjectName(u"e_kerf")
        self.e_kerf.setMinimumSize(QSize(54, 30))
        self.e_kerf.setMaximumSize(QSize(54, 30))

        self.controls_layout.addWidget(self.e_kerf)

        self.lbl_margin = QLabel(self.controls_card)
        self.lbl_margin.setObjectName(u"lbl_margin")

        self.controls_layout.addWidget(self.lbl_margin)

        self.e_margin = QLineEdit(self.controls_card)
        self.e_margin.setObjectName(u"e_margin")
        self.e_margin.setMinimumSize(QSize(54, 30))
        self.e_margin.setMaximumSize(QSize(54, 30))

        self.controls_layout.addWidget(self.e_margin)

        self.lbl_bar_len = QLabel(self.controls_card)
        self.lbl_bar_len.setObjectName(u"lbl_bar_len")

        self.controls_layout.addWidget(self.lbl_bar_len)

        self.e_bar_len = QLineEdit(self.controls_card)
        self.e_bar_len.setObjectName(u"e_bar_len")
        self.e_bar_len.setMinimumSize(QSize(72, 30))
        self.e_bar_len.setMaximumSize(QSize(72, 30))

        self.controls_layout.addWidget(self.e_bar_len)

        self.lbl_bar_height = QLabel(self.controls_card)
        self.lbl_bar_height.setObjectName(u"lbl_bar_height")

        self.controls_layout.addWidget(self.lbl_bar_height)

        self.e_bar_height = QLineEdit(self.controls_card)
        self.e_bar_height.setObjectName(u"e_bar_height")
        self.e_bar_height.setMinimumSize(QSize(80, 30))
        self.e_bar_height.setMaximumSize(QSize(80, 30))

        self.controls_layout.addWidget(self.e_bar_height)

        self.controls_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.controls_layout.addItem(self.controls_spacer)

        self.calc_combo_cuts = QComboBox(self.controls_card)
        self.calc_combo_cuts.setObjectName(u"calc_combo_cuts")
        self.calc_combo_cuts.setMinimumSize(QSize(210, 30))
        self.calc_combo_cuts.setMaximumSize(QSize(16777215, 30))

        self.controls_layout.addWidget(self.calc_combo_cuts)

        self.result_lbl = QLabel(self.controls_card)
        self.result_lbl.setObjectName(u"result_lbl")

        self.controls_layout.addWidget(self.result_lbl)

        self.add_btn = QPushButton(self.controls_card)
        self.add_btn.setObjectName(u"add_btn")
        self.add_btn.setMinimumSize(QSize(0, 30))
        self.add_btn.setMaximumSize(QSize(16777215, 30))

        self.controls_layout.addWidget(self.add_btn)

        self.calc_btn = QPushButton(self.controls_card)
        self.calc_btn.setObjectName(u"calc_btn")
        self.calc_btn.setMinimumSize(QSize(0, 30))
        self.calc_btn.setMaximumSize(QSize(16777215, 30))

        self.controls_layout.addWidget(self.calc_btn)


        self.main_layout.addWidget(self.controls_card)

        self.splitter = QSplitter(TabCortes)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.cuts_panel = QWidget(self.splitter)
        self.cuts_panel.setObjectName(u"cuts_panel")
        self.cuts_panel.setMinimumSize(QSize(480, 0))
        self.cuts_panel_layout = QVBoxLayout(self.cuts_panel)
        self.cuts_panel_layout.setSpacing(2)
        self.cuts_panel_layout.setObjectName(u"cuts_panel_layout")
        self.cuts_panel_layout.setContentsMargins(4, 4, 4, 4)
        self.cuts_hdr = QLabel(self.cuts_panel)
        self.cuts_hdr.setObjectName(u"cuts_hdr")

        self.cuts_panel_layout.addWidget(self.cuts_hdr)

        self.cuts_scroll = QScrollArea(self.cuts_panel)
        self.cuts_scroll.setObjectName(u"cuts_scroll")
        self.cuts_scroll.setFrameShape(QFrame.NoFrame)
        self.cuts_scroll.setWidgetResizable(True)
        self.cuts_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rows_container = QWidget()
        self.rows_container.setObjectName(u"rows_container")
        self.rows_container.setGeometry(QRect(0, 0, 470, 300))
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setSpacing(2)
        self.rows_layout.setObjectName(u"rows_layout")
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.rows_layout.addItem(self.rows_spacer)

        self.cuts_scroll.setWidget(self.rows_container)

        self.cuts_panel_layout.addWidget(self.cuts_scroll)

        self.splitter.addWidget(self.cuts_panel)
        self.preview_panel = QWidget(self.splitter)
        self.preview_panel.setObjectName(u"preview_panel")
        self.preview_panel.setMinimumSize(QSize(200, 0))
        self.preview_panel_layout = QVBoxLayout(self.preview_panel)
        self.preview_panel_layout.setSpacing(2)
        self.preview_panel_layout.setObjectName(u"preview_panel_layout")
        self.preview_panel_layout.setContentsMargins(4, 4, 4, 4)
        self.preview_hdr = QLabel(self.preview_panel)
        self.preview_hdr.setObjectName(u"preview_hdr")

        self.preview_panel_layout.addWidget(self.preview_hdr)

        self.preview_scroll = QScrollArea(self.preview_panel)
        self.preview_scroll.setObjectName(u"preview_scroll")
        self.preview_scroll.setFrameShape(QFrame.NoFrame)
        self.preview_scroll.setWidgetResizable(True)

        self.preview_panel_layout.addWidget(self.preview_scroll)

        self.splitter.addWidget(self.preview_panel)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(TabCortes)

        QMetaObject.connectSlotsByName(TabCortes)
    # setupUi

    def retranslateUi(self, TabCortes):
        self.header_card.setProperty(u"role", QCoreApplication.translate("TabCortes", u"card", None))
        self.e_pedido.setPlaceholderText(QCoreApplication.translate("TabCortes", u"Order number", None))
        self.e_oferta.setPlaceholderText(QCoreApplication.translate("TabCortes", u"Offer number", None))
        self.e_cliente.setPlaceholderText(QCoreApplication.translate("TabCortes", u"Client", None))
        self.add_field_btn.setText(QCoreApplication.translate("TabCortes", u"+ Add field", None))
        self.edit_fields_btn.setText(QCoreApplication.translate("TabCortes", u"Edit fields", None))
        self.controls_card.setProperty(u"role", QCoreApplication.translate("TabCortes", u"card", None))
        self.lbl_kerf.setText(QCoreApplication.translate("TabCortes", u"Kerf loss", None))
        self.e_kerf.setText(QCoreApplication.translate("TabCortes", u"2.0", None))
        self.lbl_margin.setText(QCoreApplication.translate("TabCortes", u"Tube margin", None))
        self.e_margin.setText(QCoreApplication.translate("TabCortes", u"0", None))
        self.lbl_bar_len.setText(QCoreApplication.translate("TabCortes", u"Bar length", None))
        self.e_bar_len.setText(QCoreApplication.translate("TabCortes", u"6000", None))
        self.lbl_bar_height.setText(QCoreApplication.translate("TabCortes", u"Bar height", None))
        self.e_bar_height.setText("")
        self.result_lbl.setText("")
        self.add_btn.setText(QCoreApplication.translate("TabCortes", u"+ Add cut", None))
        self.calc_btn.setText(QCoreApplication.translate("TabCortes", u"Calculate", None))
        self.cuts_hdr.setText(QCoreApplication.translate("TabCortes", u"Cuts", None))
        self.preview_hdr.setText(QCoreApplication.translate("TabCortes", u"Nesting preview", None))
        pass
    # retranslateUi

