# -------------------------------------------------------------------------------
# Name:
# Purpose:     Creates a GUI with five adminstrative levels plus country
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# -------------------------------------------------------------------------------

__prog__ = 'GlblEcsseGnrtrGUI.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

import sys
from os.path import normpath, join
from os import system, getcwd
import subprocess
from time import time
from pandas import DataFrame

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (QLabel, QWidget, QApplication, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit,
                             QComboBox, QPushButton, QCheckBox, QFileDialog, QTextEdit, QMessageBox)

from common_componentsGUI import (exit_clicked, commonSection, projectTextChanged, save_clicked)
from glbl_ecss_cmmn_cmpntsGUI import calculate_grid_cell, grid_resolutions, glblecss_limit_sims, glblecss_bounding_box

from generate_soil_vars_nc import make_soil_nc_outputs
from glbl_ecsse_high_level_sp import generate_all_soil_metrics
from glbl_ecsse_low_level_fns_sv import fetch_soil_metrics

from weather_datasets import change_weather_resource
from initialise_funcs import read_config_file, initiation, build_and_display_projects
from wthr_generation_fns import generate_all_weather, make_wthr_coords_lookup
from set_up_logging import OutLog

STD_BTN_SIZE_120 = 120
STD_BTN_SIZE_80 = 80
STD_FLD_SIZE_180 = 180
STD_FLD_SIZE_200 = 200
STD_FLD_SIZE_250 = 250

CARBON_VARS = {'TOTAL_BM_LITTER_c': 'total conversion of biomass to litter',
                                                            'TOTAL_LITTER_SOIL_c': 'total litter and soil carbon'}
ERROR_STR = '*** Error *** '
WARN_STR = '*** Warning *** '

class Form(QWidget):
    """
    C
    """
    def __init__(self, parent=None):

        super(Form, self).__init__(parent)

        self.version = 'HWSD_grid'
        initiation(self, '_generator')
        font = QFont(self.font())
        font.setPointSize(font.pointSize() + 2)
        self.setFont(font)

        # The layout is done with the QGridLayout
        grid = QGridLayout()
        grid.setSpacing(10)  # set spacing between widgets

        # line 0
        # ======
        irow = 0
        w_lbl00s = QLabel('Projects:')
        w_lbl00s.setAlignment(Qt.AlignRight)
        helpText = 'list of projects'
        w_lbl00s.setToolTip(helpText)
        grid.addWidget(w_lbl00s, irow, 0)

        w_combo00s = QComboBox()
        for project in self.projects:
            w_combo00s.addItem(str(project))
        grid.addWidget(w_combo00s, irow, 1)
        w_combo00s.currentIndexChanged[str].connect(self.changeProject)
        self.w_combo00s = w_combo00s

        irow += 1
        w_nc_extnt = QLabel('')  # project detail
        grid.addWidget(w_nc_extnt, irow, 1, 1, 4)
        self.w_nc_extnt = w_nc_extnt

        irow += 1
        grid.addWidget(QLabel(''), irow, 2)  # spacer

        # ==============
        irow = glblecss_bounding_box(self, grid, irow)
        irow += 1
        grid.addWidget(QLabel(''), irow, 2)  # spacer

        # soil switches
        # =============
        irow += 1
        lbl04 = QLabel('Options:')
        lbl04.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl04, irow, 0)

        w_use_dom_soil = QCheckBox('Use most dominant soil')
        helpText = 'Each HWSD grid cell can have up to 10 soils. Select this option to use most dominant soil and\n' \
                   ' discard all others. The the most dominant soil is defined as having the highest percentage coverage ' \
                   ' of all the soils for that grid cell'
        w_use_dom_soil.setToolTip(helpText)
        # grid.addWidget(w_use_dom_soil, irow, 1, 1, 2)
        grid.addWidget(w_use_dom_soil, irow, 1)
        self.w_use_dom_soil = w_use_dom_soil

        w_use_high_cover = QCheckBox('Use highest coverage soil')
        helpText = 'Each meta-cell has one or more HWSD mu global keys with each key associated with a coverage expressed \n' \
                   ' as a proportion of the area of the meta cell. Select this option to use the mu global with the highest coverage,\n' \
                   ' discard the others and aggregate their coverages to the selected mu global'
        w_use_high_cover.setToolTip(helpText)
        # grid.addWidget(w_use_high_cover, irow, 3, 1, 2)
        grid.addWidget(w_use_high_cover, irow, 2)
        self.w_use_high_cover = w_use_high_cover

        # AOI bounding box detail
        # =======================
        irow += 1
        w_lbl07 = QLabel('AOI bounding box:')
        helpText = 'Select NetCDF file of plant inputs'
        w_lbl07.setToolTip(helpText)
        w_lbl07.setAlignment(Qt.AlignRight)
        grid.addWidget(w_lbl07, irow, 0)

        w_hwsd_bbox = QLabel('')
        w_hwsd_bbox.setToolTip(helpText)
        w_hwsd_bbox.setAlignment(Qt.AlignLeft)
        self.w_hwsd_bbox = w_hwsd_bbox
        grid.addWidget(self.w_hwsd_bbox, irow, 1, 1, 5)

        # create weather and grid resolution
        # ==================================
        irow = commonSection(self, grid, irow)
        irow = grid_resolutions(self, grid, irow)
        irow += 1
        grid.addWidget(QLabel(''), irow, 2)  # spacer

        # ================== command lines ===========================
        irow += 1
        irow = glblecss_limit_sims(self, grid, irow)

        # ================= row 3 ============================
        irow += 1
        icol = 1

        w_ovewrite = QPushButton("Ovewrite")
        helpText = 'Ovewrite existing weather or soil for this project'
        w_ovewrite.setToolTip(helpText)
        w_ovewrite.setFixedWidth(STD_BTN_SIZE_80)
        w_ovewrite.setEnabled(False)
        grid.addWidget(w_ovewrite, irow, icol)
        w_ovewrite.clicked.connect(self.cleanSimsClicked)

        icol += 1
        w_clear = QPushButton("Clear window", self)
        helpText = 'Clear reporting window'
        w_clear.setToolTip(helpText)
        w_clear.setFixedWidth(STD_BTN_SIZE_120)
        w_clear.clicked.connect(self.clearReporting)
        grid.addWidget(w_clear, irow, icol)

        icol += 1
        w_save = QPushButton("Save")
        helpText = 'Save configuration and study definition files'
        w_save.setToolTip(helpText)
        w_save.setFixedWidth(STD_BTN_SIZE_80)
        grid.addWidget(w_save, irow, icol)
        w_save.clicked.connect(self.saveClicked)

        icol += 1
        w_cancel = QPushButton("Cancel")
        helpText = 'Leaves GUI without saving configuration and study definition files'
        w_cancel.setToolTip(helpText)
        w_cancel.setFixedWidth(STD_BTN_SIZE_80)
        grid.addWidget(w_cancel, irow, icol)
        w_cancel.clicked.connect(self.cancelClicked)

        icol += 1
        w_exit = QPushButton("Exit", self)
        grid.addWidget(w_exit, irow, icol)
        w_exit.setFixedWidth(STD_BTN_SIZE_80)
        w_exit.clicked.connect(self.exitClicked)

        irow += 1
        grid.addWidget(QLabel(''), irow, 2)  # spacer

        # ================= row 6 ============================
        irow += 1
        icol = 0
        w_wthr_only = QPushButton('Create weather')
        helpText = 'Generate weather only'
        w_wthr_only.setToolTip(helpText)
        w_wthr_only.setEnabled(True)
        grid.addWidget(w_wthr_only, irow, icol)
        w_wthr_only.setFixedWidth(STD_BTN_SIZE_120)
        w_wthr_only.clicked.connect(self.gnrtWthrClicked)
        self.w_wthr_only = w_wthr_only

        icol += 1
        w_wthr_lookup = QPushButton("Make wthr lookup")
        helpText = 'Make weather coords lookup file'
        w_wthr_lookup.setToolTip(helpText)
        w_wthr_lookup.setFixedWidth(STD_BTN_SIZE_120)
        grid.addWidget(w_wthr_lookup, irow, icol)
        w_wthr_lookup.clicked.connect(self.makeWthrLookupClicked)
        self.w_wthr_lookup = w_wthr_lookup

        icol += 1
        w_soil_all = QPushButton("Make soil CSV")
        helpText = 'Generate CSV data of soil carbon (Dominant) for all metrics'
        w_soil_all.setToolTip(helpText)
        w_soil_all.setFixedWidth(STD_BTN_SIZE_120)
        grid.addWidget(w_soil_all, irow, icol)
        w_soil_all.clicked.connect(lambda: self.genSoilOutptsClicked(True))
        self.w_soil_all = w_soil_all

        icol += 1
        w_check_soil = QPushButton("Check soil CSV")
        helpText = 'Generate CSV data of soil carbon (Dominant) for all metrics'
        w_check_soil.setToolTip(helpText)
        w_check_soil.setFixedWidth(STD_BTN_SIZE_120)
        grid.addWidget(w_check_soil, irow, icol)
        w_check_soil.clicked.connect(self.checkSoilCsv)
        self.w_check_soil = w_check_soil

        icol += 1
        w_soil_nc = QPushButton("Make soil NC")
        helpText = 'Generate NetCDF file of soil carbon (Dominant), pH and bulk density for both layers'
        w_soil_nc.setToolTip(helpText)
        w_soil_nc.setFixedWidth(STD_BTN_SIZE_120)
        grid.addWidget(w_soil_nc, irow, icol)
        w_soil_nc.clicked.connect(self.genSoilNcClicked)
        self.w_soil_nc = w_soil_nc

        # LH vertical box consists of png image
        # =====================================
        lh_vbox = QVBoxLayout()

        lbl20 = QLabel()
        lbl20.setPixmap(QPixmap(self.settings['fname_png']))
        lbl20.setScaledContents(True)
        lh_vbox.addWidget(lbl20)

        # add grid consisting of combo boxes, labels and buttons to RH vertical box
        # =========================================================================
        rh_vbox = QVBoxLayout()
        rh_vbox.addLayout(grid)

        # add reporting
        # =============
        bot_hbox = QHBoxLayout()
        w_report = QTextEdit()
        w_report.verticalScrollBar().minimum()
        w_report.setMinimumHeight(250)
        w_report.setMinimumWidth(1000)
        w_report.setStyleSheet('font: bold 10.5pt Courier')  # big jump to 11pt
        bot_hbox.addWidget(w_report, 1)
        self.w_report = w_report

        sys.stdout = OutLog(self.w_report, sys.stdout)
        # sys.stderr = OutLog(self.w_report, sys.stderr, QColor(255, 0, 0))

        # add LH and RH vertical boxes to main horizontal box
        # ===================================================
        main_hbox = QHBoxLayout()
        main_hbox.setSpacing(10)
        main_hbox.addLayout(lh_vbox)
        main_hbox.addLayout(rh_vbox, stretch=1)

        # feed horizontal boxes into the window
        # =====================================
        outer_layout = QVBoxLayout()
        outer_layout.addLayout(main_hbox)
        outer_layout.addLayout(bot_hbox)
        self.setLayout(outer_layout)

        # posx, posy, width, height
        self.setGeometry(200, 100, 690, 250)
        self.setWindowTitle('Global Ecosse Holisoils spatial variation - uses EFISCEN NetCDF plant inputs')

        # reads and set values from last run
        # ==================================
        read_config_file(self)
        if len(self.weather_set_linkages) == 0:
            self.w_wthr_only.setEnabled(False)
        else:
            self.w_wthr_only.setEnabled(True)

        self.combo10w.currentIndexChanged[str].connect(self.weatherResourceChanged)

# ===============================
    def checkSoilCsv(self):
        """
        C
        """
        fetch_soil_metrics(self)
        return

    def makeWthrLookupClicked(self):
        """
        Make weather coords lookup file
        """
        make_wthr_coords_lookup(self)

        return

    def gnrtWthrClicked(self):
        """
        generate weather for all regions, scenarios and GCMs
        """
        generate_all_weather(self)

    def genSoilOutptsClicked(self, all_metrics_flag=False):
        """
        C
        """
        if all_metrics_flag:
            generate_all_soil_metrics(self)

    def genSoilNcClicked(self):
        """
        C
        """
        make_soil_nc_outputs(self)

    def clearReporting(self):
        """
        C
        """
        self.w_report.clear()

    def adjustLuChckBoxes(self):
        """
        C
        """
        for lu in self.w_hilda_lus:
            if lu == 'all':
                continue
            else:
                if self.w_hilda_lus['all'].isChecked():
                    self.w_hilda_lus[lu].setEnabled(False)
                else:
                    self.w_hilda_lus[lu].setEnabled(True)
        return

    def weatherResourceChanged(self):
        """
        C
        """
        change_weather_resource(self)

    def resolutionChanged(self):
        """
        C
        """
        granularity = 120
        calculate_grid_cell(self, granularity)

    def saveClicked(self):
        """
        C
        """
        func_name = __prog__ + ' saveClicked'

        # check for spaces
        # ================
        study = self.w_study.text()
        if study == '':
            print('study cannot be blank')
        else:
            if study.find(' ') >= 0:
                print('*** study name must not have spaces ***')
            else:
                save_clicked(self)
                build_and_display_projects(self)

    def cancelClicked(self):
        """
        C
        """
        func_name = __prog__ + ' cancelClicked'

        exit_clicked(self, write_config_flag=False)

    def exitClicked(self):
        """
        exit cleanly
        """

        exit_clicked(self)

    def changeProject(self):
        """
        permits change of configuration file
        """
        pass

    def projectTextChanged(self):
        """
        C
        """
        projectTextChanged(self)

    def cleanSimsClicked(self):
        """
        C
        """
        print('under construction')

    def viewRunReport(self):
        """
        C
        """
        print('under construction')

def main():
    """
    C
    """
    app = QApplication(sys.argv)  # create QApplication object
    form = Form()  # instantiate form
    # display the GUI and start the event loop if we're not running batch mode
    form.show()  # paint form
    sys.exit(app.exec_())  # start event loop

if __name__ == '__main__':
    main()
