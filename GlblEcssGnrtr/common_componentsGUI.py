"""
#-------------------------------------------------------------------------------
# Name:        common_componentsGUI.p
# Purpose:     consist of high level functions invoked by main GUI
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#
"""

__prog__ = 'common_componentsGUI.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

# Version history
# ---------------
#
from os.path import normpath, isfile

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox, QRadioButton, QButtonGroup)

from initialise_funcs import read_config_file, write_config_file

WDGT_SIZE_40 = 40
WDGT_SIZE_60 = 60
WDGT_SIZE_80 = 80
WDGT_SIZE_100 = 100
WDGT_SIZE_120 = 120
WDGT_SIZE_200 = 200

RESOLUTIONS = {120:'30"', 30:'2\'', 20:'3\'', 10:'6\'', 8:'7\' 30"', 6:'10\'', 4:'15\'', 3:'20\'', 2:'30\''}
LU_DEFNS = {'lu_type' : ['Arable','Forestry','Miscanthus','Grassland','Semi-natural', 'SRC', 'Rapeseed', 'Sugar cane'],
                   'abbrev': ['ara',   'for',      'mis',      'gra',      'nat',     'src', 'rps',      'sgc'],
                        'ilu':[1,        3,          5,          2,          4,          6,     7,          7]}

HILDA_LANDUSES = ['cropland', 'pasture', 'other', 'forest', 'grassland', 'all']

# run modes
# =========
SPATIAL = 1
XLS_FILE = 2

# ========================================

def _chck_box_inpt_choices(form, grid, irow):
    """
    C
    """
    irow += 1

    form.w_hilda_lus = {}
    for icol, lu in enumerate(HILDA_LANDUSES):
        w_hilda_lu = QCheckBox(lu.title())
        helpText = ''
        w_hilda_lu.setToolTip(helpText)
        if lu == 'all':
            w_hilda_lu.clicked.connect(form.adjustLuChckBoxes)

        grid.addWidget(w_hilda_lu, irow, icol)
        form.w_hilda_lus[lu] = w_hilda_lu

    return irow

def climate_section(form, grid, irow):
    """
    C
    """
    irow += 1
    lbl10w = QLabel('Weather resource:')
    lbl10w.setAlignment(Qt.AlignRight)
    helpText = 'permissable weather dataset resources include CRU, Euro-CORDEX - see: http://www.euro-cordex.net, MERA and EObs'
    lbl10w.setToolTip(helpText)
    grid.addWidget(lbl10w, irow, 0)

    combo10w = QComboBox()
    for weather_resource in form.weather_resources_generic:
        combo10w.addItem(weather_resource)
    combo10w.setFixedWidth(WDGT_SIZE_120)
    form.combo10w = combo10w
    grid.addWidget(combo10w, irow, 1)

    # line 9: scenarios
    # =================
    lbl10 = QLabel('Climate Scenario:')
    lbl10.setAlignment(Qt.AlignRight)
    helpText = 'Ecosse requires future average monthly precipitation and temperature derived from climate models.\n' \
        + 'The data used here is ClimGen v1.02 created on 16.10.08 developed by the Climatic Research Unit\n' \
        + ' and the Tyndall Centre. See: http://www.cru.uea.ac.uk/~timo/climgen/'

    lbl10.setToolTip(helpText)
    grid.addWidget(lbl10, irow, 2)

    # weather scenarios are populated when the config file is read or weather resource is changed
    # ===========================================================================================
    combo10 = QComboBox()
    combo10.setFixedWidth(WDGT_SIZE_80)
    grid.addWidget(combo10, irow, 3)
    form.combo10 = combo10

    # dataset start and end years
    # ===========================
    for wthr_set in form.weather_sets:
        irow += 1
        year_strt = form.weather_sets[wthr_set]['year_start']
        year_end = form.weather_sets[wthr_set]['year_end']
        lbl_strt_end = QLabel(wthr_set + ' start year: {}\tend year: {}'.format(year_strt, year_end))
        lbl_strt_end.setAlignment(Qt.AlignLeft)
        grid.addWidget(lbl_strt_end, irow, 1, 1, 4)

    # ======
    irow += 1
    grid.addWidget(QLabel(''), irow, 2)  # spacer

    return irow

def save_clicked(form):
    """
    write last GUI selections
    """
    #
    write_config_file(form)
    return

def exit_clicked(form, write_config_flag = True):
    """
    C
    """
    # write last GUI selections
    if write_config_flag:
        write_config_file(form)

    # close various files
    if hasattr(form, 'fobjs'):
        for key in form.fobjs:
            form.fobjs[key].close()

    # close logging
    try:
        form.lgr.handlers[0].close()
    except AttributeError:
        pass

    form.close()

    return

def projectTextChanged(form):

        # replace spaces with underscores and rebuild study list
        # ======================================================
        study = form.w_study.text()

        form.w_study.setText(study.replace(' ','_'))

        return
