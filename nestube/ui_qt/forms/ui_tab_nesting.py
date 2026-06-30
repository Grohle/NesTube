# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_nesting.ui'
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

class Ui_TabNesting(object):
    def setupUi(self, TabNesting):
        if not TabNesting.objectName():
            TabNesting.setObjectName(u"TabNesting")
        TabNesting.resize(900, 600)
        self.main_layout = QVBoxLayout(TabNesting)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar_frame = QFrame(TabNesting)
        self.toolbar_frame.setObjectName(u"toolbar_frame")
        self.toolbar_outer_layout = QVBoxLayout(self.toolbar_frame)
        self.toolbar_outer_layout.setSpacing(0)
        self.toolbar_outer_layout.setObjectName(u"toolbar_outer_layout")
        self.toolbar_outer_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar_row1 = QWidget(self.toolbar_frame)
        self.toolbar_row1.setObjectName(u"toolbar_row1")
        self.row1_layout = QHBoxLayout(self.toolbar_row1)
        self.row1_layout.setSpacing(4)
        self.row1_layout.setObjectName(u"row1_layout")
        self.row1_layout.setContentsMargins(6, 6, 6, 6)
        self.save_btn = QPushButton(self.toolbar_row1)
        self.save_btn.setObjectName(u"save_btn")
        self.save_btn.setMinimumSize(QSize(30, 30))
        self.save_btn.setMaximumSize(QSize(30, 30))

        self.row1_layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton(self.toolbar_row1)
        self.clear_btn.setObjectName(u"clear_btn")
        self.clear_btn.setMinimumSize(QSize(30, 30))
        self.clear_btn.setMaximumSize(QSize(30, 30))

        self.row1_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton(self.toolbar_row1)
        self.export_btn.setObjectName(u"export_btn")
        self.export_btn.setMinimumSize(QSize(30, 30))
        self.export_btn.setMaximumSize(QSize(30, 30))

        self.row1_layout.addWidget(self.export_btn)

        self.sep1 = QFrame(self.toolbar_row1)
        self.sep1.setObjectName(u"sep1")
        self.sep1.setFrameShape(QFrame.Shape.VLine)
        self.sep1.setMinimumSize(QSize(2, 0))
        self.sep1.setMaximumSize(QSize(2, 16777215))

        self.row1_layout.addWidget(self.sep1)

        self.sep2 = QFrame(self.toolbar_row1)
        self.sep2.setObjectName(u"sep2")
        self.sep2.setFrameShape(QFrame.Shape.VLine)
        self.sep2.setMinimumSize(QSize(2, 0))
        self.sep2.setMaximumSize(QSize(2, 16777215))

        self.row1_layout.addWidget(self.sep2)

        self.add_bar_btn = QPushButton(self.toolbar_row1)
        self.add_bar_btn.setObjectName(u"add_bar_btn")
        self.add_bar_btn.setMinimumSize(QSize(0, 30))
        self.add_bar_btn.setMaximumSize(QSize(16777215, 30))

        self.row1_layout.addWidget(self.add_bar_btn)

        self.rem_toolbar_btn = QPushButton(self.toolbar_row1)
        self.rem_toolbar_btn.setObjectName(u"rem_toolbar_btn")
        self.rem_toolbar_btn.setMinimumSize(QSize(0, 30))
        self.rem_toolbar_btn.setMaximumSize(QSize(16777215, 30))

        self.row1_layout.addWidget(self.rem_toolbar_btn)

        self.sep3 = QFrame(self.toolbar_row1)
        self.sep3.setObjectName(u"sep3")
        self.sep3.setFrameShape(QFrame.Shape.VLine)
        self.sep3.setMinimumSize(QSize(2, 0))
        self.sep3.setMaximumSize(QSize(2, 16777215))

        self.row1_layout.addWidget(self.sep3)

        self.rotate_left_btn = QPushButton(self.toolbar_row1)
        self.rotate_left_btn.setObjectName(u"rotate_left_btn")
        self.rotate_left_btn.setMinimumSize(QSize(30, 30))
        self.rotate_left_btn.setMaximumSize(QSize(30, 30))

        self.row1_layout.addWidget(self.rotate_left_btn)

        self.flip_v_btn = QPushButton(self.toolbar_row1)
        self.flip_v_btn.setObjectName(u"flip_v_btn")
        self.flip_v_btn.setMinimumSize(QSize(30, 30))
        self.flip_v_btn.setMaximumSize(QSize(30, 30))

        self.row1_layout.addWidget(self.flip_v_btn)

        self.flip_h_btn = QPushButton(self.toolbar_row1)
        self.flip_h_btn.setObjectName(u"flip_h_btn")
        self.flip_h_btn.setMinimumSize(QSize(30, 30))
        self.flip_h_btn.setMaximumSize(QSize(30, 30))

        self.row1_layout.addWidget(self.flip_h_btn)

        self.rotate_right_btn = QPushButton(self.toolbar_row1)
        self.rotate_right_btn.setObjectName(u"rotate_right_btn")
        self.rotate_right_btn.setMinimumSize(QSize(30, 30))
        self.rotate_right_btn.setMaximumSize(QSize(30, 30))

        self.row1_layout.addWidget(self.rotate_right_btn)

        self.row1_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.row1_layout.addItem(self.row1_spacer)

        self.auto_nest_btn = QPushButton(self.toolbar_row1)
        self.auto_nest_btn.setObjectName(u"auto_nest_btn")
        self.auto_nest_btn.setMinimumSize(QSize(150, 30))
        self.auto_nest_btn.setMaximumSize(QSize(16777215, 30))

        self.row1_layout.addWidget(self.auto_nest_btn)


        self.toolbar_outer_layout.addWidget(self.toolbar_row1)

        self.toolbar_row2 = QWidget(self.toolbar_frame)
        self.toolbar_row2.setObjectName(u"toolbar_row2")
        self.row2_layout = QHBoxLayout(self.toolbar_row2)
        self.row2_layout.setSpacing(6)
        self.row2_layout.setObjectName(u"row2_layout")
        self.row2_layout.setContentsMargins(6, 6, 6, 6)
        self.lbl_kerf = QLabel(self.toolbar_row2)
        self.lbl_kerf.setObjectName(u"lbl_kerf")

        self.row2_layout.addWidget(self.lbl_kerf)

        self.tb_kerf = QLineEdit(self.toolbar_row2)
        self.tb_kerf.setObjectName(u"tb_kerf")
        self.tb_kerf.setMinimumSize(QSize(44, 30))
        self.tb_kerf.setMaximumSize(QSize(44, 30))

        self.row2_layout.addWidget(self.tb_kerf)

        self.lbl_margin = QLabel(self.toolbar_row2)
        self.lbl_margin.setObjectName(u"lbl_margin")

        self.row2_layout.addWidget(self.lbl_margin)

        self.tb_margin = QLineEdit(self.toolbar_row2)
        self.tb_margin.setObjectName(u"tb_margin")
        self.tb_margin.setMinimumSize(QSize(44, 30))
        self.tb_margin.setMaximumSize(QSize(44, 30))

        self.row2_layout.addWidget(self.tb_margin)

        self.lbl_bar_len = QLabel(self.toolbar_row2)
        self.lbl_bar_len.setObjectName(u"lbl_bar_len")

        self.row2_layout.addWidget(self.lbl_bar_len)

        self.tb_bar_len = QLineEdit(self.toolbar_row2)
        self.tb_bar_len.setObjectName(u"tb_bar_len")
        self.tb_bar_len.setMinimumSize(QSize(64, 30))
        self.tb_bar_len.setMaximumSize(QSize(64, 30))

        self.row2_layout.addWidget(self.tb_bar_len)

        self.lbl_height = QLabel(self.toolbar_row2)
        self.lbl_height.setObjectName(u"lbl_height")

        self.row2_layout.addWidget(self.lbl_height)

        self.tb_height = QLineEdit(self.toolbar_row2)
        self.tb_height.setObjectName(u"tb_height")
        self.tb_height.setMinimumSize(QSize(80, 30))
        self.tb_height.setMaximumSize(QSize(80, 30))

        self.row2_layout.addWidget(self.tb_height)

        self.sep4 = QFrame(self.toolbar_row2)
        self.sep4.setObjectName(u"sep4")
        self.sep4.setFrameShape(QFrame.Shape.VLine)
        self.sep4.setMinimumSize(QSize(2, 0))
        self.sep4.setMaximumSize(QSize(2, 16777215))

        self.row2_layout.addWidget(self.sep4)

        self.opt_combo = QComboBox(self.toolbar_row2)
        self.opt_combo.setObjectName(u"opt_combo")
        self.opt_combo.setMinimumSize(QSize(96, 30))
        self.opt_combo.setMaximumSize(QSize(96, 30))

        self.row2_layout.addWidget(self.opt_combo)

        self.strategy_combo = QComboBox(self.toolbar_row2)
        self.strategy_combo.setObjectName(u"strategy_combo")
        self.strategy_combo.setMinimumSize(QSize(170, 30))
        self.strategy_combo.setMaximumSize(QSize(16777215, 30))

        self.row2_layout.addWidget(self.strategy_combo)

        self.row2_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.row2_layout.addItem(self.row2_spacer)


        self.toolbar_outer_layout.addWidget(self.toolbar_row2)


        self.main_layout.addWidget(self.toolbar_frame)

        self.info_bar = QWidget(TabNesting)
        self.info_bar.setObjectName(u"info_bar")
        self.info_bar_layout = QHBoxLayout(self.info_bar)
        self.info_bar_layout.setObjectName(u"info_bar_layout")
        self.info_bar_layout.setContentsMargins(8, 0, 8, 0)
        self.qty_lbl = QLabel(self.info_bar)
        self.qty_lbl.setObjectName(u"qty_lbl")
        self.qty_lbl.setVisible(False)

        self.info_bar_layout.addWidget(self.qty_lbl)

        self.info_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.info_bar_layout.addItem(self.info_spacer)

        self.status_lbl = QLabel(self.info_bar)
        self.status_lbl.setObjectName(u"status_lbl")

        self.info_bar_layout.addWidget(self.status_lbl)

        self.delete_btn = QPushButton(self.info_bar)
        self.delete_btn.setObjectName(u"delete_btn")
        self.delete_btn.setMinimumSize(QSize(0, 24))
        self.delete_btn.setMaximumSize(QSize(16777215, 24))
        self.delete_btn.setVisible(False)

        self.info_bar_layout.addWidget(self.delete_btn)

        self.remove_btn = QPushButton(self.info_bar)
        self.remove_btn.setObjectName(u"remove_btn")
        self.remove_btn.setMinimumSize(QSize(0, 24))
        self.remove_btn.setMaximumSize(QSize(16777215, 24))
        self.remove_btn.setVisible(False)

        self.info_bar_layout.addWidget(self.remove_btn)


        self.main_layout.addWidget(self.info_bar)

        self.splitter = QSplitter(TabNesting)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        self.pieces_panel = QWidget(self.splitter)
        self.pieces_panel.setObjectName(u"pieces_panel")
        self.pieces_panel.setMinimumSize(QSize(160, 0))
        self.pieces_panel.setMaximumSize(QSize(280, 16777215))
        self.pieces_panel_layout = QVBoxLayout(self.pieces_panel)
        self.pieces_panel_layout.setSpacing(0)
        self.pieces_panel_layout.setObjectName(u"pieces_panel_layout")
        self.pieces_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.pieces_hdr_frame = QFrame(self.pieces_panel)
        self.pieces_hdr_frame.setObjectName(u"pieces_hdr_frame")
        self.pieces_hdr_layout = QVBoxLayout(self.pieces_hdr_frame)
        self.pieces_hdr_layout.setObjectName(u"pieces_hdr_layout")
        self.pieces_hdr_layout.setContentsMargins(8, 6, 8, 6)
        self.sidebar_title = QLabel(self.pieces_hdr_frame)
        self.sidebar_title.setObjectName(u"sidebar_title")

        self.pieces_hdr_layout.addWidget(self.sidebar_title)

        self.filter_row = QWidget(self.pieces_hdr_frame)
        self.filter_row.setObjectName(u"filter_row")
        self.filter_row_layout = QHBoxLayout(self.filter_row)
        self.filter_row_layout.setSpacing(4)
        self.filter_row_layout.setObjectName(u"filter_row_layout")
        self.filter_row_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_all_btn = QPushButton(self.filter_row)
        self.filter_all_btn.setObjectName(u"filter_all_btn")
        self.filter_all_btn.setMinimumSize(QSize(0, 20))
        self.filter_all_btn.setMaximumSize(QSize(16777215, 20))

        self.filter_row_layout.addWidget(self.filter_all_btn)

        self.filter_complete_btn = QPushButton(self.filter_row)
        self.filter_complete_btn.setObjectName(u"filter_complete_btn")
        self.filter_complete_btn.setMinimumSize(QSize(0, 20))
        self.filter_complete_btn.setMaximumSize(QSize(16777215, 20))

        self.filter_row_layout.addWidget(self.filter_complete_btn)

        self.filter_incomplete_btn = QPushButton(self.filter_row)
        self.filter_incomplete_btn.setObjectName(u"filter_incomplete_btn")
        self.filter_incomplete_btn.setMinimumSize(QSize(0, 20))
        self.filter_incomplete_btn.setMaximumSize(QSize(16777215, 20))

        self.filter_row_layout.addWidget(self.filter_incomplete_btn)


        self.pieces_hdr_layout.addWidget(self.filter_row)


        self.pieces_panel_layout.addWidget(self.pieces_hdr_frame)

        self.pieces_scroll = QScrollArea(self.pieces_panel)
        self.pieces_scroll.setObjectName(u"pieces_scroll")
        self.pieces_scroll.setWidgetResizable(True)
        self.pieces_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar_container = QWidget()
        self.sidebar_container.setObjectName(u"sidebar_container")
        self.sidebar_container.setGeometry(QRect(0, 0, 160, 300))
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setSpacing(2)
        self.sidebar_layout.setObjectName(u"sidebar_layout")
        self.sidebar_layout.setContentsMargins(4, 4, 4, 4)
        self.sidebar_stretch = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.sidebar_layout.addItem(self.sidebar_stretch)

        self.pieces_scroll.setWidget(self.sidebar_container)

        self.pieces_panel_layout.addWidget(self.pieces_scroll)

        self.splitter.addWidget(self.pieces_panel)
        self.bars_panel = QWidget(self.splitter)
        self.bars_panel.setObjectName(u"bars_panel")
        self.bars_panel.setMinimumSize(QSize(140, 0))
        self.bars_panel.setMaximumSize(QSize(260, 16777215))
        self.bars_panel_layout = QVBoxLayout(self.bars_panel)
        self.bars_panel_layout.setSpacing(0)
        self.bars_panel_layout.setObjectName(u"bars_panel_layout")
        self.bars_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.bars_hdr_frame = QFrame(self.bars_panel)
        self.bars_hdr_frame.setObjectName(u"bars_hdr_frame")
        self.bars_hdr_layout = QHBoxLayout(self.bars_hdr_frame)
        self.bars_hdr_layout.setObjectName(u"bars_hdr_layout")
        self.bars_hdr_layout.setContentsMargins(6, 4, 6, 4)
        self.bars_hdr_title = QLabel(self.bars_hdr_frame)
        self.bars_hdr_title.setObjectName(u"bars_hdr_title")

        self.bars_hdr_layout.addWidget(self.bars_hdr_title)

        self.bars_hdr_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bars_hdr_layout.addItem(self.bars_hdr_spacer)

        self.show_all_btn = QPushButton(self.bars_hdr_frame)
        self.show_all_btn.setObjectName(u"show_all_btn")
        self.show_all_btn.setMinimumSize(QSize(0, 30))
        self.show_all_btn.setMaximumSize(QSize(16777215, 30))

        self.bars_hdr_layout.addWidget(self.show_all_btn)


        self.bars_panel_layout.addWidget(self.bars_hdr_frame)

        self.bars_scroll = QScrollArea(self.bars_panel)
        self.bars_scroll.setObjectName(u"bars_scroll")
        self.bars_scroll.setWidgetResizable(True)
        self.bars_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.bars_container = QWidget()
        self.bars_container.setObjectName(u"bars_container")
        self.bars_container.setGeometry(QRect(0, 0, 140, 300))
        self.bars_layout = QVBoxLayout(self.bars_container)
        self.bars_layout.setSpacing(2)
        self.bars_layout.setObjectName(u"bars_layout")
        self.bars_layout.setContentsMargins(4, 4, 4, 4)
        self.bars_stretch = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.bars_layout.addItem(self.bars_stretch)

        self.bars_scroll.setWidget(self.bars_container)

        self.bars_panel_layout.addWidget(self.bars_scroll)

        self.remnant_panel = QFrame(self.bars_panel)
        self.remnant_panel.setObjectName(u"remnant_panel")
        self.remnant_panel.setVisible(False)
        self.remnant_panel.setMinimumSize(QSize(0, 130))
        self.remnant_panel_layout = QVBoxLayout(self.remnant_panel)
        self.remnant_panel_layout.setSpacing(4)
        self.remnant_panel_layout.setObjectName(u"remnant_panel_layout")
        self.remnant_panel_layout.setContentsMargins(6, 6, 6, 6)
        self.rem_title = QLabel(self.remnant_panel)
        self.rem_title.setObjectName(u"rem_title")

        self.remnant_panel_layout.addWidget(self.rem_title)

        self.rem_row = QWidget(self.remnant_panel)
        self.rem_row.setObjectName(u"rem_row")
        self.rem_row_layout = QGridLayout(self.rem_row)
        self.rem_row_layout.setObjectName(u"rem_row_layout")
        self.rem_row_layout.setHorizontalSpacing(6)
        self.rem_row_layout.setVerticalSpacing(4)
        self.rem_row_layout.setContentsMargins(0, 0, 0, 0)
        self.rem_min_lbl = QLabel(self.rem_row)
        self.rem_min_lbl.setObjectName(u"rem_min_lbl")

        self.rem_row_layout.addWidget(self.rem_min_lbl, 0, 0, 1, 1)

        self.remnant_min_entry = QLineEdit(self.rem_row)
        self.remnant_min_entry.setObjectName(u"remnant_min_entry")
        self.remnant_min_entry.setMinimumSize(QSize(56, 30))
        self.remnant_min_entry.setMaximumSize(QSize(16777215, 30))

        self.rem_row_layout.addWidget(self.remnant_min_entry, 0, 1, 1, 1)

        self.rem_margin_lbl = QLabel(self.rem_row)
        self.rem_margin_lbl.setObjectName(u"rem_margin_lbl")

        self.rem_row_layout.addWidget(self.rem_margin_lbl, 1, 0, 1, 1)

        self.rem_margin_entry = QLineEdit(self.rem_row)
        self.rem_margin_entry.setObjectName(u"rem_margin_entry")
        self.rem_margin_entry.setMinimumSize(QSize(56, 30))
        self.rem_margin_entry.setMaximumSize(QSize(16777215, 30))

        self.rem_row_layout.addWidget(self.rem_margin_entry, 1, 1, 1, 1)

        self.rem_refresh_btn = QPushButton(self.rem_row)
        self.rem_refresh_btn.setObjectName(u"rem_refresh_btn")
        self.rem_refresh_btn.setMinimumSize(QSize(30, 30))
        self.rem_refresh_btn.setMaximumSize(QSize(30, 30))

        self.rem_row_layout.addWidget(self.rem_refresh_btn, 2, 0, 1, 1)

        self.rem_apply_btn = QPushButton(self.rem_row)
        self.rem_apply_btn.setObjectName(u"rem_apply_btn")
        self.rem_apply_btn.setMinimumSize(QSize(0, 30))
        self.rem_apply_btn.setMaximumSize(QSize(16777215, 30))

        self.rem_row_layout.addWidget(self.rem_apply_btn, 2, 1, 1, 1)


        self.remnant_panel_layout.addWidget(self.rem_row)

        self.remnant_list_lbl = QLabel(self.remnant_panel)
        self.remnant_list_lbl.setObjectName(u"remnant_list_lbl")
        self.remnant_list_lbl.setWordWrap(True)

        self.remnant_panel_layout.addWidget(self.remnant_list_lbl)


        self.bars_panel_layout.addWidget(self.remnant_panel)

        self.splitter.addWidget(self.bars_panel)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(TabNesting)

        QMetaObject.connectSlotsByName(TabNesting)
    # setupUi

    def retranslateUi(self, TabNesting):
        self.lbl_kerf.setText(QCoreApplication.translate("TabNesting", u"Kerf", None))
        self.tb_kerf.setText(QCoreApplication.translate("TabNesting", u"2.0", None))
        self.lbl_margin.setText(QCoreApplication.translate("TabNesting", u"Margin", None))
        self.tb_margin.setText(QCoreApplication.translate("TabNesting", u"0", None))
        self.lbl_bar_len.setText(QCoreApplication.translate("TabNesting", u"Bar length", None))
        self.tb_bar_len.setText(QCoreApplication.translate("TabNesting", u"6000", None))
        self.lbl_height.setText(QCoreApplication.translate("TabNesting", u"Height", None))
        self.qty_lbl.setText("")
        self.status_lbl.setText("")
        self.sidebar_title.setText(QCoreApplication.translate("TabNesting", u"PIECES REMAINING", None))
        self.filter_all_btn.setText(QCoreApplication.translate("TabNesting", u"All", None))
        self.filter_complete_btn.setText(QCoreApplication.translate("TabNesting", u"Complete", None))
        self.filter_incomplete_btn.setText(QCoreApplication.translate("TabNesting", u"Incomplete", None))
        self.bars_hdr_title.setText(QCoreApplication.translate("TabNesting", u"BARS", None))
        self.rem_title.setText(QCoreApplication.translate("TabNesting", u"REMNANTS", None))
        self.rem_min_lbl.setText(QCoreApplication.translate("TabNesting", u"Min length", None))
        self.remnant_min_entry.setText(QCoreApplication.translate("TabNesting", u"1000", None))
        self.rem_margin_lbl.setText(QCoreApplication.translate("TabNesting", u"Margin", None))
        self.rem_margin_entry.setText(QCoreApplication.translate("TabNesting", u"0", None))
        pass
    # retranslateUi

