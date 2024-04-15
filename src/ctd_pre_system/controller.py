import datetime
import os
import subprocess
import threading
from pathlib import Path

import file_explorer
import psutil
from file_explorer import psa
from file_explorer import seabird
from file_explorer.seabird import paths
from ctd_pre_system.ctd_config import CtdConfig
from ctd_pre_system.operator import Operators
from ctd_pre_system.ship import Ships
from ctd_pre_system.station import Stations
from svepa import exceptions as svepa_exceptions
import svepa


class Controller:

    def __init__(self, paths_object, **kwargs):
        self.ctd_config = None
        self.ctd_files = None

        self._paths = paths_object

        self.operators = Operators()
        # self.stations = Stations(update_primary=kwargs.get('update_primary_station_list'))
        self.stations = Stations()
        self.ships = Ships()

    @property
    def ctd_config_root_directory(self):
        return self._paths('config_dir')

    @ctd_config_root_directory.setter
    def ctd_config_root_directory(self, directory):
        self._paths.set_config_root_directory(directory)
        self.ctd_config = CtdConfig(self._paths('config_dir'))

    @property
    def ctd_data_directory(self):
        return self._paths.get_local_directory('source')

    @ctd_data_directory.setter
    def ctd_data_directory(self, directory):
        self._paths.set_source_directory(directory)

    @property
    def ctd_data_root_directory_server(self):
        return self._paths.get_server_directory('root')

    @ctd_data_root_directory_server.setter
    def ctd_data_root_directory_server(self, directory):
        self._paths.set_server_root_directory(directory)

    def get_svepa_info(self, credentials_path):
        info = svepa.get_current_station_info(path_to_svepa_credentials=credentials_path)
        return info

    def get_station_list(self):
        return self.stations.get_station_list()

    def get_operator_list(self):
        return self.operators.get_operator_list()

    def get_closest_station(self, lat, lon):
        return self.stations.get_closest_station(lat, lon)

    def get_station_info(self, station_name):
        return self.stations.get_station_info(station_name)
    
    def get_distance_to_station(self, lat, lon, station_name):
        return self.stations.get_distance_to_station(lat, lon, station_name)

    def _get_running_programs(self):
        program_list = []
        for p in psutil.process_iter():
            program_list.append(p.name())
        return program_list

    def run_seasave(self):
        if 'Seasave.exe' in self._get_running_programs():
            # filezilla.exe
            raise ChildProcessError('Seasave is already running!')

        t = threading.Thread(target=self._subprocess_seasave)
        t.daemon = True  # close pipe if GUI process exits
        t.start()

    def _subprocess_seasave(self):
        subprocess.run([str(self.ctd_config.seasave_program_path), f'-p={self.ctd_config.seasave_psa_main_file}'])

    def get_xmlcon_path(self, instrument):
        if instrument.lower() in ['sbe09', 'sbe9']:
            file_path = str(self.ctd_config.seasave_sbe09_xmlcon_file)
        elif instrument.lower() == 'sbe19':
            file_path = str(self.ctd_config.seasave_sbe19_xmlcon_file)
        else:
            raise ValueError(f'Incorrect instrument number: {instrument}')
        return file_path

    def get_seasave_psa_path(self):
        return self.ctd_config.seasave_psa_main_file

    def _get_xmlcon_object(self, instrument):
        xmlcon_file_path = self.get_xmlcon_path(instrument)
        obj = seabird.XmlconFile(xmlcon_file_path, ignore_pattern=True)
        return obj

    def _get_main_psa_object(self):
        return psa.SeasavePSAfile(self.ctd_config.seasave_psa_main_file)

    def update_xmlcon_in_main_psa_file(self, instrument):
        xmlcon_file_path = self.get_xmlcon_path(instrument)
        psa_obj = self._get_main_psa_object()
        psa_obj.xmlcon_path = xmlcon_file_path
        psa_obj.save()

    def update_main_psa_file(self,
                             instrument=None,
                             depth=None,
                             nr_bins=None,
                             cruise_nr=None,
                             ship_code=None,
                             serno=None,
                             station='',
                             operator='',
                             year=None,
                             tail=None,
                             position=['', ''],
                             event_ids={},
                             add_samp='',
                             metadata_admin={},
                             metadata_conditions={},
                             lims_job=None,
                             pumps={},
                             source_dir=False,
                             **kwargs):

        if not year:
            year = str(datetime.datetime.now().year)

        if instrument:
            self._instrument = instrument
            print('INSTRUMENT', instrument)
            self.update_xmlcon_in_main_psa_file(instrument)
            

        if self.series_exists(
                # server=True,
                cruise=cruise_nr,
                year=year,
                ship=ship_code,
                serno=serno,
                source_dir=source_dir, 
                check_serno=kwargs.get('check_serno')
        ):
            raise Exception(f'Serien med serienummer {serno} existerar redan på servern!')

        hex_file_path = self.get_data_file_path(instrument=instrument,
                                                cruise=cruise_nr,
                                                ship=ship_code,
                                                serno=serno,
                                                tail=tail)
        directory = hex_file_path.parent
        if not directory.exists():
            os.makedirs(directory)

        psa_obj = self._get_main_psa_object()
        psa_obj.data_path = hex_file_path

        if depth:
            psa_obj.display_depth = depth

        if nr_bins:
            psa_obj.nr_bins = nr_bins

        psa_obj.station = station

        psa_obj.operator = operator

        psa_obj.lims_job = lims_job or ''

        if ship_code:
            psa_obj.ship = f'{self.ships.get_code(ship_code)} {self.ships.get_name(ship_code)}'

        if cruise_nr and ship_code and year:
            psa_obj.cruise = f'{self.ships.get_code(ship_code)}-{year}-{cruise_nr.zfill(2)}'

        psa_obj.position = position

        psa_obj.pumps = pumps

        psa_obj.event_ids = event_ids

        psa_obj.add_samp = add_samp

        psa_obj.metadata_admin = metadata_admin
        psa_obj.metadata_conditions = metadata_conditions

        psa_obj.save()

    def get_data_file_path(self, instrument=None, cruise=None, ship=None, serno=None, tail=None):
        missing = []
        for key, value in zip(['instrument', 'cruise', 'ship', 'serno'], [instrument, cruise, ship, serno]):
            if not value:
                missing.append(key)
        if missing:
            raise ValueError(f'Missing information: {str(missing)}')
        # Builds the file stem to be as the name for the processed file.
        # sbe09_1387_20200207_0801_77SE_0120
        now = datetime.datetime.now()
        time_str = now.strftime('%Y%m%d_%H%M')
        year = str(now.year)

        file_stem = '_'.join([
            instrument,
            self.get_instrument_serial_number(instrument),
            time_str,
            self.ships.get_code(ship),
            cruise.zfill(2),
            serno
        ])
        if tail:
            file_stem = f'{file_stem}_{tail}'
        directory = self._paths.get_local_directory('source')
        file_path = Path(directory, f'{file_stem}.hex')
        return file_path

    def get_sensor_info_in_xmlcon(self, instrument):
        xmlcon = self._get_xmlcon_object(instrument)
        return xmlcon.sensor_info

    def get_instrument_serial_number(self, instrument):
        xmlcon = self._get_xmlcon_object(instrument)
        return xmlcon.instrument_number

    def _get_root_data_path(self, server=False):
        root_path = self.ctd_data_root_directory
        if server:
            root_path = self.ctd_data_root_directory_server
        if not root_path:
            # return ''
            raise NotADirectoryError
        return root_path

    def _get_raw_data_path(self, server=False, year=None, **kwargs):
        if server:
            return self._paths.get_server_directory('raw', year=year, **kwargs)
        else:
            return self._paths.get_local_directory('raw', year=year, **kwargs)

    def series_exists(self, return_file_name=False, server=False, **kwargs):
        root_path = None
        if kwargs.get('source_dir'):
            root_path = self._paths.get_local_directory('source')
        if not root_path:
            root_path = self._get_raw_data_path(server=server, year=kwargs.get('year'), create=True)
        if not root_path:
            return False
        pack_col = file_explorer.get_package_collection_for_directory(root_path)
        if kwargs.get('check_serno'):
            return pack_col.series_exists(serno=kwargs.get('serno'))
        else:
            return pack_col.series_exists(**kwargs)

        # ctd_files_obj = get_ctd_files_object(root_path, suffix='.hex')
        # return ctd_files_obj.series_exists(return_file_name=return_file_name, **kwargs)

    def get_latest_serno(self, server=False, **kwargs):
        root_path = self._get_raw_data_path(server=server, year=kwargs.get('year'), create=True)
        pack_col = file_explorer.get_package_collection_for_directory(root_path)
        return pack_col.get_latest_serno(**kwargs)
        # ctd_files_obj = get_ctd_files_object(root_path, suffix='.hex')
        # return ctd_files_obj.get_latest_serno(**kwargs)

    def get_latest_series_path(self, server=False, **kwargs):
        root_path = self._get_raw_data_path(server=server, year=kwargs.get('year'), create=True)
        pack_col = file_explorer.get_package_collection_for_directory(root_path)
        latest_pack = pack_col.get_latest_series(**kwargs)
        if not latest_pack:
            return
        return latest_pack.get_file_path(suffix='.hex')
        # ctd_files_obj = get_ctd_files_object(root_path, suffix='.hex')
        # # inga filer här av någon anledning....
        # return ctd_files_obj.get_latest_series(path=True, **kwargs)

    def get_next_serno(self, server=False, **kwargs):
        root_path = self._get_raw_data_path(server=server, year=kwargs.get('year'), create=True)
        pack_col = file_explorer.get_package_collection_for_directory(root_path)
        return pack_col.get_next_serno(**kwargs)
        # ctd_files_obj = get_ctd_files_object(root_path, suffix='.hex')
        # return ctd_files_obj.get_next_serno(**kwargs)


if __name__ == '__main__':
    sbe_paths = paths.SBEPaths()
    c = Controller(paths_object=sbe_paths)
    c.ctd_config_root_directory = r'C:\mw\git\ctd_config'
    c.ctd_data_root_directory = r'C:\mw\temp_ctd_pre_system_data_root'
    c.update_main_psa_file(instrument='sbe09', cruise_nr='01', ship_code='77SE', serno='0001')
    # c.run_seasave()
