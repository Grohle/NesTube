# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tab_perfiles.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QSplitter, QVBoxLayout, QWidget)

class Ui_TabPerfiles(object):
    def setupUi(self, TabPerfiles):
        if not TabPerfiles.objectName():
            TabPerfiles.setObjectName(u"TabPerfiles")
        TabPerfiles.resize(860, 500)
        self.main_layout = QVBoxLayout(TabPerfiles)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(TabPerfiles)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.config_outer = QWidget(self.splitter)
        self.config_outer.setObjectName(u"config_outer")
        self.config_outer.setMinimumSize(QSize(260, 0))
        self.config_outer.setMaximumSize(QSize(420, 16777215))
        self.config_outer_layout = QVBoxLayout(self.config_outer)
        self.config_outer_layout.setObjectName(u"config_outer_layout")
        self.config_outer_layout.setContentsMargins(0, 0, 0, 0)
        self.config_scroll = QScrollArea(self.config_outer)
        self.config_scroll.setObjectName(u"config_scroll")
        self.config_scroll.setFrameShape(QFrame.NoFrame)
        self.config_scroll.setWidgetResizable(True)
        self.config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.config_inner = QWidget()
        self.config_inner.setObjectName(u"config_inner")
        self.config_inner.setGeometry(QRect(0, 0, 260, 800))
        self.config_inner_layout = QVBoxLayout(self.config_inner)
        self.config_inner_layout.setSpacing(6)
        self.config_inner_layout.setObjectName(u"config_inner_layout")
        self.config_inner_layout.setContentsMargins(8, 8, 8, 8)
        self.btns0 = QWidget(self.config_inner)
        self.btns0.setObjectName(u"btns0")
        self.btns0_layout = QHBoxLayout(self.btns0)
        self.btns0_layout.setSpacing(4)
        self.btns0_layout.setObjectName(u"btns0_layout")
        self.btns0_layout.setContentsMargins(0, 0, 0, 0)
        self.calc_btn = QPushButton(self.btns0)
        self.calc_btn.setObjectName(u"calc_btn")

        self.btns0_layout.addWidget(self.calc_btn)

        self.clear_btn = QPushButton(self.btns0)
        self.clear_btn.setObjectName(u"clear_btn")

        self.btns0_layout.addWidget(self.clear_btn)


        self.config_inner_layout.addWidget(self.btns0)

        self.btns1 = QWidget(self.config_inner)
        self.btns1.setObjectName(u"btns1")
        self.btns1_layout = QHBoxLayout(self.btns1)
        self.btns1_layout.setSpacing(4)
        self.btns1_layout.setObjectName(u"btns1_layout")
        self.btns1_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_excel = QPushButton(self.btns1)
        self.btn_excel.setObjectName(u"btn_excel")
        self.btn_excel.setMinimumSize(QSize(0, 24))
        self.btn_excel.setMaximumSize(QSize(16777215, 24))
        self.btn_excel.setStyleSheet(u"font-size:10px;")

        self.btns1_layout.addWidget(self.btn_excel)

        self.btn_pdf = QPushButton(self.btns1)
        self.btn_pdf.setObjectName(u"btn_pdf")
        self.btn_pdf.setMinimumSize(QSize(0, 24))
        self.btn_pdf.setMaximumSize(QSize(16777215, 24))
        self.btn_pdf.setStyleSheet(u"font-size:10px;")

        self.btns1_layout.addWidget(self.btn_pdf)

        self.btn_docx = QPushButton(self.btns1)
        self.btn_docx.setObjectName(u"btn_docx")
        self.btn_docx.setMinimumSize(QSize(0, 24))
        self.btn_docx.setMaximumSize(QSize(16777215, 24))
        self.btn_docx.setStyleSheet(u"font-size:10px;")

        self.btns1_layout.addWidget(self.btn_docx)

        self.btn_print = QPushButton(self.btns1)
        self.btn_print.setObjectName(u"btn_print")
        self.btn_print.setMinimumSize(QSize(0, 24))
        self.btn_print.setMaximumSize(QSize(16777215, 24))
        self.btn_print.setStyleSheet(u"font-size:10px;")

        self.btns1_layout.addWidget(self.btn_print)


        self.config_inner_layout.addWidget(self.btns1)

        self.weight_section_lbl = QLabel(self.config_inner)
        self.weight_section_lbl.setObjectName(u"weight_section_lbl")

        self.config_inner_layout.addWidget(self.weight_section_lbl)

        self.fav_widget = QWidget(self.config_inner)
        self.fav_widget.setObjectName(u"fav_widget")
        self.fav_layout = QHBoxLayout(self.fav_widget)
        self.fav_layout.setSpacing(4)
        self.fav_layout.setObjectName(u"fav_layout")
        self.fav_layout.setContentsMargins(0, 0, 0, 0)
        self.fav_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.fav_layout.addItem(self.fav_spacer)


        self.config_inner_layout.addWidget(self.fav_widget)

        self.profile_combo = QComboBox(self.config_inner)
        self.profile_combo.setObjectName(u"profile_combo")

        self.config_inner_layout.addWidget(self.profile_combo)

        self.dim_container = QWidget(self.config_inner)
        self.dim_container.setObjectName(u"dim_container")
        self.dim_layout = QGridLayout(self.dim_container)
        self.dim_layout.setSpacing(4)
        self.dim_layout.setObjectName(u"dim_layout")
        self.dim_layout.setContentsMargins(0, 0, 0, 0)

        self.config_inner_layout.addWidget(self.dim_container)

        self.field_espesor = QWidget(self.config_inner)
        self.field_espesor.setObjectName(u"field_espesor")
        self.field_espesor_layout = QHBoxLayout(self.field_espesor)
        self.field_espesor_layout.setSpacing(6)
        self.field_espesor_layout.setObjectName(u"field_espesor_layout")
        self.field_espesor_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_espesor = QLabel(self.field_espesor)
        self.lbl_espesor.setObjectName(u"lbl_espesor")
        self.lbl_espesor.setMinimumSize(QSize(120, 0))

        self.field_espesor_layout.addWidget(self.lbl_espesor)

        self.e_espesor = QLineEdit(self.field_espesor)
        self.e_espesor.setObjectName(u"e_espesor")
        self.e_espesor.setMinimumSize(QSize(0, 30))
        self.e_espesor.setMaximumSize(QSize(16777215, 30))

        self.field_espesor_layout.addWidget(self.e_espesor)


        self.config_inner_layout.addWidget(self.field_espesor)

        self.cb_macizo = QCheckBox(self.config_inner)
        self.cb_macizo.setObjectName(u"cb_macizo")

        self.config_inner_layout.addWidget(self.cb_macizo)

        self.field_kg_m = QWidget(self.config_inner)
        self.field_kg_m.setObjectName(u"field_kg_m")
        self.field_kg_m_layout = QHBoxLayout(self.field_kg_m)
        self.field_kg_m_layout.setSpacing(6)
        self.field_kg_m_layout.setObjectName(u"field_kg_m_layout")
        self.field_kg_m_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_kg_m = QLabel(self.field_kg_m)
        self.lbl_kg_m.setObjectName(u"lbl_kg_m")
        self.lbl_kg_m.setMinimumSize(QSize(120, 0))

        self.field_kg_m_layout.addWidget(self.lbl_kg_m)

        self.e_kg_m = QLineEdit(self.field_kg_m)
        self.e_kg_m.setObjectName(u"e_kg_m")
        self.e_kg_m.setMinimumSize(QSize(0, 30))
        self.e_kg_m.setMaximumSize(QSize(16777215, 30))

        self.field_kg_m_layout.addWidget(self.e_kg_m)


        self.config_inner_layout.addWidget(self.field_kg_m)

        self.field_peso_esp = QWidget(self.config_inner)
        self.field_peso_esp.setObjectName(u"field_peso_esp")
        self.field_peso_esp_layout = QHBoxLayout(self.field_peso_esp)
        self.field_peso_esp_layout.setSpacing(6)
        self.field_peso_esp_layout.setObjectName(u"field_peso_esp_layout")
        self.field_peso_esp_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_peso_esp = QLabel(self.field_peso_esp)
        self.lbl_peso_esp.setObjectName(u"lbl_peso_esp")
        self.lbl_peso_esp.setMinimumSize(QSize(120, 0))

        self.field_peso_esp_layout.addWidget(self.lbl_peso_esp)

        self.e_peso_esp = QLineEdit(self.field_peso_esp)
        self.e_peso_esp.setObjectName(u"e_peso_esp")
        self.e_peso_esp.setMinimumSize(QSize(0, 30))
        self.e_peso_esp.setMaximumSize(QSize(16777215, 30))

        self.field_peso_esp_layout.addWidget(self.e_peso_esp)


        self.config_inner_layout.addWidget(self.field_peso_esp)

        self.pricing_section_lbl = QLabel(self.config_inner)
        self.pricing_section_lbl.setObjectName(u"pricing_section_lbl")

        self.config_inner_layout.addWidget(self.pricing_section_lbl)

        self.field_precio_kg = QWidget(self.config_inner)
        self.field_precio_kg.setObjectName(u"field_precio_kg")
        self.field_precio_kg_layout = QHBoxLayout(self.field_precio_kg)
        self.field_precio_kg_layout.setSpacing(6)
        self.field_precio_kg_layout.setObjectName(u"field_precio_kg_layout")
        self.field_precio_kg_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_precio_kg = QLabel(self.field_precio_kg)
        self.lbl_precio_kg.setObjectName(u"lbl_precio_kg")
        self.lbl_precio_kg.setMinimumSize(QSize(120, 0))

        self.field_precio_kg_layout.addWidget(self.lbl_precio_kg)

        self.e_precio_kg = QLineEdit(self.field_precio_kg)
        self.e_precio_kg.setObjectName(u"e_precio_kg")
        self.e_precio_kg.setMinimumSize(QSize(0, 30))
        self.e_precio_kg.setMaximumSize(QSize(16777215, 30))

        self.field_precio_kg_layout.addWidget(self.e_precio_kg)


        self.config_inner_layout.addWidget(self.field_precio_kg)

        self.field_precio_m = QWidget(self.config_inner)
        self.field_precio_m.setObjectName(u"field_precio_m")
        self.field_precio_m_layout = QHBoxLayout(self.field_precio_m)
        self.field_precio_m_layout.setSpacing(6)
        self.field_precio_m_layout.setObjectName(u"field_precio_m_layout")
        self.field_precio_m_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_precio_m = QLabel(self.field_precio_m)
        self.lbl_precio_m.setObjectName(u"lbl_precio_m")
        self.lbl_precio_m.setMinimumSize(QSize(120, 0))

        self.field_precio_m_layout.addWidget(self.lbl_precio_m)

        self.e_precio_m = QLineEdit(self.field_precio_m)
        self.e_precio_m.setObjectName(u"e_precio_m")
        self.e_precio_m.setMinimumSize(QSize(0, 30))
        self.e_precio_m.setMaximumSize(QSize(16777215, 30))

        self.field_precio_m_layout.addWidget(self.e_precio_m)


        self.config_inner_layout.addWidget(self.field_precio_m)

        self.field_precio_barra = QWidget(self.config_inner)
        self.field_precio_barra.setObjectName(u"field_precio_barra")
        self.field_precio_barra_layout = QHBoxLayout(self.field_precio_barra)
        self.field_precio_barra_layout.setSpacing(6)
        self.field_precio_barra_layout.setObjectName(u"field_precio_barra_layout")
        self.field_precio_barra_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_precio_barra = QLabel(self.field_precio_barra)
        self.lbl_precio_barra.setObjectName(u"lbl_precio_barra")
        self.lbl_precio_barra.setMinimumSize(QSize(120, 0))

        self.field_precio_barra_layout.addWidget(self.lbl_precio_barra)

        self.e_precio_barra = QLineEdit(self.field_precio_barra)
        self.e_precio_barra.setObjectName(u"e_precio_barra")
        self.e_precio_barra.setMinimumSize(QSize(0, 30))
        self.e_precio_barra.setMaximumSize(QSize(16777215, 30))

        self.field_precio_barra_layout.addWidget(self.e_precio_barra)


        self.config_inner_layout.addWidget(self.field_precio_barra)

        self.field_margen = QWidget(self.config_inner)
        self.field_margen.setObjectName(u"field_margen")
        self.field_margen_layout = QHBoxLayout(self.field_margen)
        self.field_margen_layout.setSpacing(6)
        self.field_margen_layout.setObjectName(u"field_margen_layout")
        self.field_margen_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_margen = QLabel(self.field_margen)
        self.lbl_margen.setObjectName(u"lbl_margen")
        self.lbl_margen.setMinimumSize(QSize(120, 0))

        self.field_margen_layout.addWidget(self.lbl_margen)

        self.e_margen_beneficio = QLineEdit(self.field_margen)
        self.e_margen_beneficio.setObjectName(u"e_margen_beneficio")
        self.e_margen_beneficio.setMinimumSize(QSize(0, 30))
        self.e_margen_beneficio.setMaximumSize(QSize(16777215, 30))

        self.field_margen_layout.addWidget(self.e_margen_beneficio)


        self.config_inner_layout.addWidget(self.field_margen)

        self.currency_row = QWidget(self.config_inner)
        self.currency_row.setObjectName(u"currency_row")
        self.currency_row_layout = QHBoxLayout(self.currency_row)
        self.currency_row_layout.setObjectName(u"currency_row_layout")
        self.currency_row_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_currency = QLabel(self.currency_row)
        self.lbl_currency.setObjectName(u"lbl_currency")

        self.currency_row_layout.addWidget(self.lbl_currency)

        self.currency_combo = QComboBox(self.currency_row)
        self.currency_combo.setObjectName(u"currency_combo")

        self.currency_row_layout.addWidget(self.currency_combo)


        self.config_inner_layout.addWidget(self.currency_row)

        self.cost_mode_row = QWidget(self.config_inner)
        self.cost_mode_row.setObjectName(u"cost_mode_row")
        self.cost_mode_row_layout = QHBoxLayout(self.cost_mode_row)
        self.cost_mode_row_layout.setObjectName(u"cost_mode_row_layout")
        self.cost_mode_row_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_cost_mode = QLabel(self.cost_mode_row)
        self.lbl_cost_mode.setObjectName(u"lbl_cost_mode")

        self.cost_mode_row_layout.addWidget(self.lbl_cost_mode)

        self.cost_mode_combo = QComboBox(self.cost_mode_row)
        self.cost_mode_combo.setObjectName(u"cost_mode_combo")
        self.cost_mode_combo.setMinimumSize(QSize(0, 30))

        self.cost_mode_row_layout.addWidget(self.cost_mode_combo)


        self.config_inner_layout.addWidget(self.cost_mode_row)

        self.cb_retales = QCheckBox(self.config_inner)
        self.cb_retales.setObjectName(u"cb_retales")

        self.config_inner_layout.addWidget(self.cb_retales)

        self.cb_confirm_costs = QCheckBox(self.config_inner)
        self.cb_confirm_costs.setObjectName(u"cb_confirm_costs")

        self.config_inner_layout.addWidget(self.cb_confirm_costs)

        self.labour_section_lbl = QLabel(self.config_inner)
        self.labour_section_lbl.setObjectName(u"labour_section_lbl")

        self.config_inner_layout.addWidget(self.labour_section_lbl)

        self.field_t_recto = QWidget(self.config_inner)
        self.field_t_recto.setObjectName(u"field_t_recto")
        self.field_t_recto_layout = QHBoxLayout(self.field_t_recto)
        self.field_t_recto_layout.setSpacing(6)
        self.field_t_recto_layout.setObjectName(u"field_t_recto_layout")
        self.field_t_recto_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_t_recto = QLabel(self.field_t_recto)
        self.lbl_t_recto.setObjectName(u"lbl_t_recto")
        self.lbl_t_recto.setMinimumSize(QSize(120, 0))

        self.field_t_recto_layout.addWidget(self.lbl_t_recto)

        self.e_t_recto = QLineEdit(self.field_t_recto)
        self.e_t_recto.setObjectName(u"e_t_recto")
        self.e_t_recto.setMinimumSize(QSize(0, 30))
        self.e_t_recto.setMaximumSize(QSize(16777215, 30))

        self.field_t_recto_layout.addWidget(self.e_t_recto)


        self.config_inner_layout.addWidget(self.field_t_recto)

        self.field_pct_inglete = QWidget(self.config_inner)
        self.field_pct_inglete.setObjectName(u"field_pct_inglete")
        self.field_pct_inglete_layout = QHBoxLayout(self.field_pct_inglete)
        self.field_pct_inglete_layout.setSpacing(6)
        self.field_pct_inglete_layout.setObjectName(u"field_pct_inglete_layout")
        self.field_pct_inglete_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_pct_inglete = QLabel(self.field_pct_inglete)
        self.lbl_pct_inglete.setObjectName(u"lbl_pct_inglete")
        self.lbl_pct_inglete.setMinimumSize(QSize(120, 0))

        self.field_pct_inglete_layout.addWidget(self.lbl_pct_inglete)

        self.e_pct_inglete = QLineEdit(self.field_pct_inglete)
        self.e_pct_inglete.setObjectName(u"e_pct_inglete")
        self.e_pct_inglete.setMinimumSize(QSize(0, 30))
        self.e_pct_inglete.setMaximumSize(QSize(16777215, 30))

        self.field_pct_inglete_layout.addWidget(self.e_pct_inglete)


        self.config_inner_layout.addWidget(self.field_pct_inglete)

        self.field_coste_op = QWidget(self.config_inner)
        self.field_coste_op.setObjectName(u"field_coste_op")
        self.field_coste_op_layout = QHBoxLayout(self.field_coste_op)
        self.field_coste_op_layout.setSpacing(6)
        self.field_coste_op_layout.setObjectName(u"field_coste_op_layout")
        self.field_coste_op_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_coste_op = QLabel(self.field_coste_op)
        self.lbl_coste_op.setObjectName(u"lbl_coste_op")
        self.lbl_coste_op.setMinimumSize(QSize(120, 0))

        self.field_coste_op_layout.addWidget(self.lbl_coste_op)

        self.e_coste_op = QLineEdit(self.field_coste_op)
        self.e_coste_op.setObjectName(u"e_coste_op")
        self.e_coste_op.setMinimumSize(QSize(0, 30))
        self.e_coste_op.setMaximumSize(QSize(16777215, 30))

        self.field_coste_op_layout.addWidget(self.e_coste_op)


        self.config_inner_layout.addWidget(self.field_coste_op)

        self.config_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.config_inner_layout.addItem(self.config_spacer)

        self.config_scroll.setWidget(self.config_inner)

        self.config_outer_layout.addWidget(self.config_scroll)

        self.splitter.addWidget(self.config_outer)
        self.results_outer = QWidget(self.splitter)
        self.results_outer.setObjectName(u"results_outer")
        self.results_outer_layout = QVBoxLayout(self.results_outer)
        self.results_outer_layout.setObjectName(u"results_outer_layout")
        self.results_outer_layout.setContentsMargins(0, 0, 0, 0)
        self.results_hdr = QLabel(self.results_outer)
        self.results_hdr.setObjectName(u"results_hdr")

        self.results_outer_layout.addWidget(self.results_hdr)

        self.results_scroll = QScrollArea(self.results_outer)
        self.results_scroll.setObjectName(u"results_scroll")
        self.results_scroll.setFrameShape(QFrame.NoFrame)
        self.results_scroll.setWidgetResizable(True)
        self.results_container = QWidget()
        self.results_container.setObjectName(u"results_container")
        self.results_container.setGeometry(QRect(0, 0, 400, 400))
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(6)
        self.results_layout.setObjectName(u"results_layout")
        self.results_layout.setContentsMargins(4, 4, 4, 4)
        self.results_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.results_layout.addItem(self.results_spacer)

        self.results_scroll.setWidget(self.results_container)

        self.results_outer_layout.addWidget(self.results_scroll)

        self.splitter.addWidget(self.results_outer)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(TabPerfiles)

        QMetaObject.connectSlotsByName(TabPerfiles)
    # setupUi

    def retranslateUi(self, TabPerfiles):
        self.calc_btn.setText(QCoreApplication.translate("TabPerfiles", u"Calculate", None))
        self.clear_btn.setText(QCoreApplication.translate("TabPerfiles", u"Clear", None))
        self.btn_excel.setText(QCoreApplication.translate("TabPerfiles", u"Excel", None))
        self.btn_pdf.setText(QCoreApplication.translate("TabPerfiles", u"PDF", None))
        self.btn_docx.setText(QCoreApplication.translate("TabPerfiles", u"DOCX", None))
        self.btn_print.setText(QCoreApplication.translate("TabPerfiles", u"Print", None))
        self.weight_section_lbl.setText(QCoreApplication.translate("TabPerfiles", u"WEIGHT", None))
        self.lbl_espesor.setText(QCoreApplication.translate("TabPerfiles", u"Wall thickness", None))
        self.cb_macizo.setText(QCoreApplication.translate("TabPerfiles", u"Solid section", None))
        self.lbl_kg_m.setText(QCoreApplication.translate("TabPerfiles", u"kg/m", None))
        self.lbl_peso_esp.setText(QCoreApplication.translate("TabPerfiles", u"Specific weight", None))
        self.e_peso_esp.setText(QCoreApplication.translate("TabPerfiles", u"7.85", None))
        self.pricing_section_lbl.setText(QCoreApplication.translate("TabPerfiles", u"PRICING", None))
        self.lbl_precio_kg.setText(QCoreApplication.translate("TabPerfiles", u"Price/kg", None))
        self.lbl_precio_m.setText(QCoreApplication.translate("TabPerfiles", u"Price/m", None))
        self.lbl_precio_barra.setText(QCoreApplication.translate("TabPerfiles", u"Price/bar", None))
        self.lbl_margen.setText(QCoreApplication.translate("TabPerfiles", u"Profit margin", None))
        self.lbl_currency.setText(QCoreApplication.translate("TabPerfiles", u"Currency", None))
        self.lbl_cost_mode.setText(QCoreApplication.translate("TabPerfiles", u"Cost mode", None))
        self.cb_retales.setText(QCoreApplication.translate("TabPerfiles", u"Distribute scrap", None))
        self.cb_confirm_costs.setText(QCoreApplication.translate("TabPerfiles", u"Confirm cost configuration before calculating", None))
        self.labour_section_lbl.setText(QCoreApplication.translate("TabPerfiles", u"LABOUR", None))
        self.lbl_t_recto.setText(QCoreApplication.translate("TabPerfiles", u"Straight cut time", None))
        self.e_t_recto.setText(QCoreApplication.translate("TabPerfiles", u"3", None))
        self.lbl_pct_inglete.setText(QCoreApplication.translate("TabPerfiles", u"Miter extra (%)", None))
        self.e_pct_inglete.setText(QCoreApplication.translate("TabPerfiles", u"35", None))
        self.lbl_coste_op.setText(QCoreApplication.translate("TabPerfiles", u"Operator cost", None))
        self.e_coste_op.setText(QCoreApplication.translate("TabPerfiles", u"30", None))
        self.results_hdr.setText(QCoreApplication.translate("TabPerfiles", u"Results per cut", None))
        pass
    # retranslateUi

