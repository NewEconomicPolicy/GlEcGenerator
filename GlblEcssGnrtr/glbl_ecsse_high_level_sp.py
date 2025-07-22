"""
#-------------------------------------------------------------------------------
# Name:        glbl_ecsse_high_level_sp.py
# Purpose:     consist of high level functions invoked by main GUI
# Author:      Mike Martin
# Created:     11/12/2015
# Licence:     <your licence>
# Description:
#
#-------------------------------------------------------------------------------
#
"""
__prog__ = 'glbl_ecsse_high_level_sp.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

import time
import csv
from os.path import join, isdir
from os import mkdir
from operator import itemgetter
from copy import copy

from PyQt5.QtWidgets import QApplication

from hwsd_bil import HWSD_bil

from hwsd_mu_globals_fns import gen_grid_cells_for_band
from prepare_ecosse_files import update_progress
from glbl_ecss_cmmn_cmpntsGUI import calculate_grid_cell

SOIL_HDRS = list(['UID', 'HWSD_Y', 'HWSD_X', 'Latitude', 'Longitude', 'MU_GLOBAL', 'SHARE',
                  'T_OC', 'T_BULK_DENSITY', 'T_PH_H2O', 'T_SAND', 'T_SILT', 'T_CLAY',
                  'S_OC', 'S_BULK_DENSITY', 'S_PH_H2O', 'S_SAND', 'S_SILT', 'S_CLAY'])
SOIL_DIR = 'soil_metrics'
GRANULARITY = 120

WARN_STR = '*** Warning *** '
ERROR_STR = '*** Error *** '

# ===============================================================
#
def simplify_soil_recs(soil_recs, use_dom_soil_flag):
    """
    compress soil records if duplicates are present
    simplify soil records if requested
    each mu_global points to a group of soils
    a soil group can have up to ten soils
    """
    func_name = __prog__ + ' _simplify_soil_recs'

    num_raw = 0         # total number of sub-soils
    num_compress = 0    # total number of sub-soils after compressions

    new_soil_recs = {}
    for mu_global in soil_recs:

        # no processing necessary
        # =======================
        num_sub_soils = len(soil_recs[mu_global])
        num_raw += num_sub_soils
        if num_sub_soils == 1:
            num_compress += 1
            new_soil_recs[mu_global] = soil_recs[mu_global]
            continue

        # check each soil for duplicates
        # ==============================
        new_soil_group = []
        soil_group = sorted(soil_recs[mu_global])

        # skip empty groups
        # =================
        if len(soil_group) == 0:
            continue

        first_soil = soil_group[0]
        metrics1 = first_soil[:-1]
        share1   = first_soil[-1]
        for soil in soil_group[1:]:
            metrics2 = soil[:-1]
            share2 =   soil[-1]
            if metrics1 == metrics2:
                share1 += share2
            else:
                new_soil_group.append(metrics1 + [share1])
                metrics1 = metrics2
                share1 = share2

        new_soil_group.append(metrics1 + [share1])
        num_sub_soils = len(new_soil_group)
        num_compress += num_sub_soils
        if num_sub_soils == 1:
            new_soil_recs[mu_global] = new_soil_group
            continue

        if use_dom_soil_flag:
            # assign 100% to the first entry of sorted list
            # =============================================
            dom_soil = copy(sorted(new_soil_group, reverse = True, key=itemgetter(-1))[0])
            dom_soil[-1] = 100.0
            new_soil_recs[mu_global] = list([dom_soil])

    mess = 'Leaving {}\trecords in: {} out: {}'.format(func_name, len(soil_recs),len(new_soil_recs))
    print(mess + '\tnum raw sub-soils: {}\tafter compression: {}'.format(num_raw, num_compress))
    return new_soil_recs

def _simplify_aoi(aoi_res):
    """
    simplify AOI records
    """
    aoi_res_new = []
    j = 0
    for site_rec in aoi_res:
        content = site_rec[-1]
        npairs = len(content)
        if npairs == 0:
            print('No soil information for AOI cell at lat/long: {} {} - will skip'
                                                                .format(round(site_rec[2], 4), round(site_rec[3], 4)))
        elif npairs == 1:
            aoi_res_new.append(site_rec)
        else:
            site_rec_list = list(site_rec)  # convert tuple to a list so we can edit last element
            new_content = sorted(content.items(), reverse = True, key = itemgetter(1))  # sort content so we can pick up most dominant mu_global
            total_proportion = sum(content.values())    # add up proportions
            site_rec_list[-1] = {new_content[0][0]: total_proportion}       # create a new single mu global with summed proportions

            aoi_res_new.append(tuple(site_rec_list)) # convert list to tuple

    return aoi_res_new

class SoilCsvOutputs(object):
    """
    Class to write CSV files of soil data
    """
    def __init__(self, form):

        self.lgr = form.lgr
        self.hdrs = SOIL_HDRS

        prjct = form.w_combo00s.currentText()

        soil_dir = join(form.settings['prj_drive'], prjct, SOIL_DIR)
        if not isdir(soil_dir):
            mkdir(soil_dir)

        self.soil_dir = soil_dir
        self.study = prjct
        calculate_grid_cell(form, GRANULARITY)
        self.req_resol_upscale = form.req_resol_upscale

        self.output_fobj = None
        self.writer = None

    def create_soil_file(self):
        """
        Create empty results file
        """
        req_resol_str =  '{:0=2d}'.format(self.req_resol_upscale)
        fname = join(self.soil_dir, 'HWSD_recs_' + req_resol_str + '.csv')
        try:
            self.output_fobj = open(fname, 'w', newline='')
        except (OSError, IOError) as err:
            err_mess = 'Unable to open output file. {} {}'.format(fname, err)
            self.lgr.critical(err_mess)
            print(err_mess)
            QApplication.processEvents()

        self.writer = csv.writer(self.output_fobj, delimiter=',')
        self.writer.writerow(self.hdrs)
        return fname

def _write_to_soil_file(form, soil_csv, aoi_res):
    """
    Main loop for generating soil data outputs
    """


    # open land use NC dataset
    # ========================
    last_time = time.time()
    start_time = time.time()
    completed = 0
    skipped = 0
    warn_count = 0

    # each soil can have one or more dominant soils
    # =======================================================================
    for site_rec in aoi_res:
        gran_lat, gran_lon, lat, long, area, mu_globals_props = site_rec
        gran_coord = '{:0=5d}_{:0=5d}'.format(int(gran_lat), int(gran_lon))

        for pair in mu_globals_props.items():
            mu_global, proportion = pair

            soil_list = form.hwsd_mu_globals.soil_recs[mu_global]

            # soil_c, bulk_dens, ph = soil[:3]
            # ===============================
            for soil in soil_list:
                share = soil[-1]
                if len(soil) == 13:
                    sub_soil = soil[6:-1]
                else:
                    sub_soil = 6*[-999]

                t_oc, t_bulk_density, t_ph_h2o, t_sand, t_silt, t_clay = soil[:6]
                s_oc, s_bulk_density, s_ph_h2o, s_sand, s_silt, s_clay = sub_soil

                out_rec = list([gran_coord, gran_lat, gran_lon, round(lat, 4), round(long, 4), mu_global, share])
                out_rec += list([t_oc, t_bulk_density, t_ph_h2o, t_sand, t_silt, t_clay])
                out_rec += list([s_oc, s_bulk_density, s_ph_h2o, s_sand, s_silt, s_clay])
                soil_csv.writer.writerow(out_rec)

        completed += 1
        num_meta_cells = -999
        last_time = update_progress(last_time, start_time, completed, num_meta_cells, skipped, warn_count)
        QApplication.processEvents()

    mess = '\nskipped: {}\tcompleted: {}'.format(skipped, completed)
    print(mess)
    QApplication.processEvents()

    print('')   # spacer
    return completed

def generate_soil_metrics(form):
    """
    called from GUI
    """
    func_name = __prog__ + '\tgenerate_csv_valid_file'
    max_sims = int(form.w_max_sims.text())

    if form.w_use_dom_soil.isChecked():
        use_dom_soil_flag = True
    else:
        use_dom_soil_flag = False

    # prepare the bounding box
    # ========================
    try:
        lon_ll = float(form.w_ll_lon.text())
        lat_ll = float(form.w_ll_lat.text())
        lon_ur = float(form.w_ur_lon.text())
        lat_ur = float(form.w_ur_lat.text())
    except ValueError as err:
        print('Problem retrieving bounding box: ' + str(err))
        return

    bbox = list([lon_ll, lat_ll, lon_ur, lat_ur])
    form.bbox = bbox

    # extract required values from the HWSD database and simplify if requested
    # ========================================================================
    print('Gathering soil data...\t\t(' + func_name + ')')
    hwsd = HWSD_bil(form.lgr, form.settings['hwsd_dir'])
    nrows_read = hwsd.read_bbox_mu_globals(bbox)    # create grid of mu_globals based on bounding box

    # retrieve dictionary consisting of mu_globals (keys) and number of occurrences (values)
    # ======================================================================================
    mu_globals = hwsd.get_mu_globals_dict()
    if len(mu_globals) == 0:
        print('No soil records for this area')
        return

    mess = 'Generated {} rows and {} columns of HWSD grid for ths AOI: '.format(nrows_read, hwsd.nlons)
    mess += '\n\tnumber of unique mu_globals: {}'.format(len(mu_globals))
    print(mess)
    form.lgr.info(mess)

    # extract required values from the HWSD database
    # ==============================================
    soil_recs = hwsd.get_soil_recs(sorted(mu_globals.keys()))  # sorted key list (of mu_globals)

    # remove undefined mu globals
    # ===========================
    for mu_global in hwsd.bad_muglobals:
        del(soil_recs[mu_global])

    soil_aoi_recs = simplify_soil_recs(soil_recs, use_dom_soil_flag)
    bad_mu_globals = [0] + hwsd.bad_muglobals
    del hwsd

    # Create empty soil files
    # =======================
    soil_csv = SoilCsvOutputs(form)
    fname = soil_csv.create_soil_file()

    print('\nPopulating soil file ' + fname)
    QApplication.processEvents()
    ncompleted = _write_to_soil_file(form, soil_csv, soil_aoi_recs)  # does actual work

    if ncompleted >= max_sims:
        print('Finished processing after generating {} cells'.format(ncompleted))
        QApplication.processEvents()

    # ==============
    soil_csv.output_fobj.close()    # close CSV file
    print('\nFinished soil metric writing')
    QApplication.processEvents()

    return
