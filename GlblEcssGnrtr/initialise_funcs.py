"""
#-------------------------------------------------------------------------------
# Name:        initialise_funcs.py
# Purpose:     script to read read and write the setup and configuration files
# Author:      Mike Martin
# Created:     31/07/2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
"""

__prog__ = 'initialise_funcs.py'
__version__ = '0.0.0'

# Version history
# ---------------
# 
from os.path import exists, normpath, split, splitext, isfile, isdir, join, expanduser
from os import getcwd, remove, makedirs, mkdir, name as os_name
from json import load as json_load, dump as json_dump
from time import sleep
import sys
from glob import glob
from netCDF4 import Dataset, num2date
from PyQt5.QtWidgets import QApplication

from shape_funcs import calculate_area
from weather_datasets import change_weather_resource, record_weather_settings
from glbl_ecss_cmmn_cmpntsGUI import calculate_grid_cell

from hwsd_mu_globals_fns import HWSD_mu_globals_csv
from glbl_ecss_cmmn_cmpntsGUI import print_resource_locations
from set_up_logging import set_up_logging
from weather_datasets import read_weather_dsets_detail
from hwsd_bil import check_hwsd_integrity
from shape_funcs import format_bbox

MIN_GUI_LIST = ['weatherResource', 'bbox', 'maxSims', 'endBand', 'strtBand']
CMN_GUI_LIST = ['climScnr', 'gridResol']

WARN_STR = '*** Warning *** '
ERROR_STR = '*** Error *** '
SETTINGS_LIST = ['config_dir', 'fname_png', 'hwsd_dir', 'log_dir', 'shp_dir', 'prj_drive', 'python_exe', 'weather_dir']
RUN_SETTINGS = ['completed_max', 'start_at_band', 'space_remaining_limit', 'kml_flag', 'soil_test_flag', 'zeros_file']
BBOX_DEFAULT = [116.90045, 28.2294, 117.0, 29.0]  # bounding box default - somewhere in SE Europe
sleepTime = 5

def initiation(form, variation=''):
    """
    this function is called to initiate the programme to process non-GUI settings.
    """
    fname_setup = 'global_ecosse_setup' + variation + '.json'

    # retrieve settings
    # =================
    _read_setup_file(form, fname_setup)

    form.project_files = build_and_display_projects(form)

    # set up logging
    # ==============
    set_up_logging(form, 'global_ecosse_min')

    # if specified then create pandas object read deom HWSD CSV file
    # ==============================================================
    if 'aoi_fname' in form.settings:
        form.hwsd_mu_globals = HWSD_mu_globals_csv(form, form.settings['aoi_fname'])
        # print('Reading AOI HWSD file ' + form.settings['aoi_fname'])

    return

def _read_setup_file(form, fname_setup):
    """
    read settings used for programme from the setup file, if it exists,
    or create setup file using default values if file does not exist
    """
    func_name = __prog__ + ' _read_setup_file'

    setup_file = join(getcwd(), fname_setup)
    if exists(setup_file):
        try:
            with open(setup_file, 'r') as fsetup:
                settings = json_load(fsetup)
        except (OSError, IOError) as e:
            sleep(sleepTime)
            exit(0)
    else:
        settings = write_default_setup_file(setup_file)
        print('Read default setup file ' + setup_file)

    # validate setup file
    # ===================
    grp = 'setup'
    for key in SETTINGS_LIST:
        if key not in settings[grp]:
            print(ERROR_STR + 'setting {} is required in setup file {} '.format(key, setup_file))
            sleep(sleepTime)
            exit(0)

    form.settings = {}
    for sttng in SETTINGS_LIST:
        form.settings[sttng] = settings[grp][sttng]

    # check settings
    # ==============
    prj_drive = form.settings['prj_drive']
    if not isdir(prj_drive):
        print(ERROR_STR + 'invalid project drive: ' + prj_drive)
        sleep(sleepTime)
        exit(0)

    # ==============
    log_dir = form.settings['log_dir']
    if not isdir(log_dir):
        makedirs(log_dir)

    # ==============
    config_dir = form.settings['config_dir']
    if not isdir(config_dir):
        makedirs(config_dir)

    form.settings['config_file'] =  join(config_dir, 'global_ecosse_config' + '.json')

    # ==============
    python_exe = form.settings['python_exe']
    mess = '\tPython interpreter: ' + python_exe
    if isfile(python_exe):
        print(mess)
    else:
        print(WARN_STR + mess + ' does not exist')
        form.settings['python_exe'] = None

    # HWSD and weather are crucial
    # ============================
    err_mess = ERROR_STR + 'reading setup file\n\t' + setup_file
    hwsd_dir = form.settings['hwsd_dir']
    if isdir(hwsd_dir):
        check_hwsd_integrity(hwsd_dir)
    else:
        print(err_mess + 'HWSD directory {} must exist'.format(hwsd_dir))
        sleep(sleepTime)
        exit(0)

    # ===================
    weather_dir = form.settings['weather_dir']
    if isdir(weather_dir):
        form.weather_dir = weather_dir
        form.settings['weather_dir'] = weather_dir
    else:
        print(err_mess + 'Climate directory {} must exist'.format(weather_dir))
        sleep(sleepTime)
        exit(0)

    # check weather data
    # ==================
    avlbl_wthr_rsrcs = ['CRU', 'EObs', 'CHESS', 'HARMONIE', 'EFISCEN-ISIMIP']
    rqurd_wthr_rsrcs = ['CRU', 'EFISCEN-ISIMIP']
    read_weather_dsets_detail(form, rqurd_wthr_rsrcs)

    # TODO: most of these are not used
    # ================================
    grp = 'run_settings'
    for key in RUN_SETTINGS:
        if key not in settings[grp]:
            print(WARN_STR + 'setting {} is required in setup file {} '.format(key, setup_file))

    for sttng in RUN_SETTINGS:
        form.settings[sttng] = settings[grp][sttng]

    # report settings
    # ===============
    lta_nc_fname = None
    print_resource_locations(setup_file, config_dir, hwsd_dir, weather_dir, lta_nc_fname, prj_drive, log_dir)

    return True

def write_default_setup_file(setup_file):
    """
    stanza if setup_file needs to be created
    """
    # Windows only for now
    # =====================
    os_system = os_name
    if os_system != 'nt':
        print('Operating system is ' + os_system + 'should be nt - cannot proceed with writing default setup file')
        sleep(sleepTime)
        sys.exit(0)

    # return list of drives
    # =====================
    import win32api

    drives = win32api.GetLogicalDriveStrings()
    drives = drives.split('\000')[:-1]
    if 'S:\\' in drives:
        root_dir_app = 'S:\\tools\\'  # Global Ecosse installed here
        root_dir_user = 'H:\\'  # user files reside here
    else:
        root_dir_app = 'E:\\'
        root_dir_user = 'C:\\AbUniv\\'

    suite_path = root_dir_app + 'GlobalEcosseSuite\\'
    data_path = root_dir_app + 'GlobalEcosseData\\'
    outputs_path = root_dir_app + 'GlobalEcosseOutputs\\'
    root_dir_user += 'GlobalEcosseSuite\\'

    _default_setup = {
        'setup': {
            'config_dir': root_dir_user + 'config',
            'fname_png': join(suite_path + 'Images', 'Tree_of_life.PNG'),
            'hwsd_dir': data_path + 'HWSD_NEW',
            'images_dir': outputs_path + 'images',
            'log_dir': root_dir_user + 'logs',
            'python_exe': 'E:\\Python38\\python.exe',
            'shp_dir': data_path + 'CountryShapefiles',
            'sims_dir': outputs_path + 'EcosseSims',
            'weather_dir': data_path
        },
        'run_settings': {
            'completed_max': 5000000000,
            'start_at_band': 0,
            'space_remaining_limit': 1270,
            'kml_flag': True,
            'soil_test_flag': False,
            'zeros_file': False
        }
    }
    # create setup file
    # =================
    with open(setup_file, 'w') as fsetup:
        json_dump(_default_setup, fsetup, indent=2, sort_keys=True)
        fsetup.close()
        return _default_setup

def build_and_display_projects(form):
    """
    is called at start up and when user creates a new project
    """
    prj_drive = form.settings['prj_drive']
    projects = []
    for path_nm in glob(prj_drive + 'Gl*'):
        if isdir(path_nm):
            sims_dir = join(path_nm, 'EcosseSims')
            if isdir(sims_dir):
                project = split(path_nm)[1]
                projects.append(project)

    form.projects = projects

    # display projects list
    # ====================
    if hasattr(form, 'combo00s'):
        form.combo00s.clear()
        for study in projects:
            form.w_combo00s.addItem(study)

    return projects

def read_config_file(form):
    """
    read widget settings used in the previous programme session from the config file, if it exists,
    or create config file using default settings if config file does not exist
    """
    config_file = form.settings['config_file']
    if isfile(config_file):
        try:
            with open(config_file, 'r') as fconfig:
                config = json_load(fconfig)
                print('Read config file ' + config_file)
        except (OSError, IOError) as err:
            print(err)
            return False
    else:
        config = _write_default_config_file(config_file)

    grp = 'minGUI'
    for key in MIN_GUI_LIST:
        if key not in config[grp]:
            if key == 'maxSims':
                config[grp][key] = str(9999999)
            elif key == 'strtBand':
                config[grp][key] = str(0)
            elif key == 'endBand':
                config[grp][key] = str(360)
            else:
                print(ERROR_STR + 'setting {} is required in group {} of config file {}'.format(key, grp, config_file))
                return False

    # bounding box set up
    # ===================
    bbox = config[grp]['bbox']
    area = calculate_area(bbox)
    ll_lon, ll_lat, ur_lon, ur_lat = bbox
    form.w_ll_lon.setText(str(ll_lon))
    form.w_ll_lat.setText(str(ll_lat))
    form.w_ur_lon.setText(str(ur_lon))
    form.w_ur_lat.setText(str(ur_lat))


    # post limit simulations settings
    # ===============================
    form.w_max_sims.setText(config[grp]['maxSims'])
    form.w_strt_band.setText(config[grp]['strtBand'])
    form.w_end_band.setText(config[grp]['endBand'])

    weather_resource = config[grp]['weatherResource']
    if weather_resource == '':
        weather_resource = 'EFISCEN-ISIMIP'

    form.bbox = config[grp]['bbox']
    form.combo10w.setCurrentText(weather_resource)
    change_weather_resource(form, weather_resource)

    # common area
    # ===========
    grp = 'cmnGUI'
    for key in CMN_GUI_LIST:
        if key not in config[grp]:
            print(ERROR_STR + 'setting {} is required in configuration file {} '.format(key, config_file))
            form.bbox = BBOX_DEFAULT
            form.csv_fname = ''
            return False

    # other settings
    # ==============
    form.combo16.setCurrentIndex(config[grp]['gridResol'])

    # record weather settings
    # =======================
    scenario = config[grp]['climScnr']
    form.combo10.setCurrentText(scenario)

    # bounding box set up
    # ===================
    area = calculate_area(form.bbox)
    form.fstudy = ''
    form.w_bbox.setText(format_bbox(form.bbox, area))

    # limit simulations settings
    # ==========================

    # avoids errors when exiting
    # ==========================
    form.req_resol_deg = None
    form.req_resol_granul = None
    form.w_use_dom_soil.setChecked(True)
    form.w_use_high_cover.setChecked(True)

    return True

def write_config_file(form):
    """
    write current selections to config file
    """
    config_file = form.settings['config_file']

    # ========================
    weather_resource = form.combo10w.currentText()
    scenario = form.combo10.currentText()
    grid_resol = form.combo16.currentIndex()

    # prepare the bounding box
    # ========================
    try:
        ll_lon = float(form.w_ll_lon.text())
        ll_lat = float(form.w_ll_lat.text())
        ur_lon = float(form.w_ur_lon.text())
        ur_lat = float(form.w_ur_lat.text())
    except ValueError as err:
        print('Problem writing bounding box to config file: ' + str(err))
        ur_lon = 0.0
        ur_lat = 0.0
        ll_lon = 0.0
        ll_lat = 0.0
    bbox = list([ll_lon, ll_lat, ur_lon, ur_lat])

    config = {
        'minGUI': {
            'bbox': bbox,
            'weatherResource': weather_resource,
            'usePolyFlag': False,
            'maxSims': form.w_max_sims.text(),
            'strtBand': form.w_strt_band.text(),
            'endBand': form.w_end_band.text()
        },
        'cmnGUI': {
            'climScnr': scenario,
            'gridResol': grid_resol
        }
    }
    with open(config_file, 'w') as fconfig:
        json_dump(config, fconfig, indent=2, sort_keys=True)
        print('Wrote configuration file ' + config_file)

    return

def _write_default_config_file(config_file):
    """
    #        ll_lon,    ll_lat  ur_lon,ur_lat
    # stanza if config_file needs to be created
    """
    _default_config = {
        'minGUI': {
            'bbox': BBOX_DEFAULT,
            'cordexFlag': 0,
            'luPiJsonFname': '',
            'snglPntFlag': True,
            'usePolyFlag': False
        },
        'cmnGUI': {
            'climScnr': 'rcp26',
            'eqilMode': '9.5',
            'futStrtYr': '2006',
            'futEndYr': '2015',
            'gridResol': 0,
            'histStrtYr': '1980',
            'histEndYr': '2005',
            'study': ''
        }
    }
    # if config file does not exist then create it...
    with open(config_file, 'w') as fconfig:
        json_dump(_default_config, fconfig, indent=2, sort_keys=True)
        fconfig.close()
        return _default_config
