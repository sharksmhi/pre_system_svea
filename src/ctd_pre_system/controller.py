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
from ctd_pre_system import auto_fire
from ctd_pre_system import exceptions

svepa = None
try:
    import svepa
except ImportError:
    pass


class Controller:

    def __init__(self, paths_object, **kwargs):
        self.ctd_config = None
        self.ctd_files = None

        self._paths = paths_object

        self.operators = Operators()
        # self.stations = Stations(update_primary=kwargs.get('update_primary_station_list'))
        self.stations = Stations()
        self.ships = Ships()

        self.auto_fire_station_pressure = auto_fire.get_station_pressure_object()
        self.auto_fire_bottle_order = auto_fire.get_bottle_order_object()

        self._seasave_psa = None

    @property
    def seasave_psa(self):
        if not self._seasave_psa:
            self._seasave_psa = self._get_main_psa_object()
        return self._seasave_psa

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
        if not svepa:
            return {}
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

    def _get_main_psa_object(self) -> psa.SeasavePSAfile:
        return psa.SeasavePSAfile(self.ctd_config.seasave_psa_main_file)

    def update_xmlcon_in_main_psa_file(self, instrument):
        xmlcon_file_path = self.get_xmlcon_path(instrument)
        # psa_obj = self._get_main_psa_object()
        self.seasave_psa.xmlcon_path = xmlcon_file_path
        self.seasave_psa.save()

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

        # psa_obj = self._get_main_psa_object()
        self.seasave_psa.data_path = hex_file_path

        if depth:
            self.seasave_psa.display_depth = depth

        if nr_bins:
            self.seasave_psa.nr_bins = nr_bins

        self.seasave_psa.station = station

        self.seasave_psa.operator = operator

        self.seasave_psa.lims_job = lims_job or ''

        if ship_code:
            self.seasave_psa.ship = f'{self.ships.get_code(ship_code)} {self.ships.get_name(ship_code)}'

        if cruise_nr and ship_code and year:
            self.seasave_psa.cruise = f'{self.ships.get_code(ship_code)}-{year}-{cruise_nr.zfill(2)}'

        self.seasave_psa.position = position

        self.seasave_psa.pumps = pumps

        self.seasave_psa.event_ids = event_ids

        self.seasave_psa.add_samp = add_samp

        self.seasave_psa.metadata_admin = metadata_admin
        self.seasave_psa.metadata_conditions = metadata_conditions

        self.seasave_psa.save()

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

    def get_pressure_mapping_for_station(self, station: str) -> dict[int, float]:
        return self.auto_fire_station_pressure.get_depth_pressure_mapping_for_station(station)

    def get_current_auto_fire_bottles(self) -> psa.AUTO_FIRE_DATA_DATATYPE:
        return self.seasave_psa.auto_fire_bottles

    def get_bottle_order(self, nr_active_bottles: int, nr_bottles: int = 24) -> list[int]:
        bottle_order = self.auto_fire_bottle_order.get_bottle_order(nr_bottles)
        return bottle_order[:nr_active_bottles][::-1]

    def get_auto_fire_info_for_station(self, station: str, nr_bottles: int = 24, nr_active_bottles: int = None) -> psa.AUTO_FIRE_DATA_DATATYPE:
        pressure_mapping = self.get_pressure_mapping_for_station(station)
        if not nr_active_bottles:
            nr_active_bottles = len([True for pres in pressure_mapping.values() if pres])
        new_pressure_mapping = {}
        for depth, pres in pressure_mapping.items():
            if not pres:
                continue
            if len(new_pressure_mapping) >= nr_active_bottles:
                break
            new_pressure_mapping[depth] = pres
        new_bottle_order = self.get_bottle_order(nr_active_bottles, nr_bottles=nr_bottles)
        data = []
        index = 0
        for depth, pres in new_pressure_mapping.items():
            #if not pres:
            #    continue
            data.append(dict(
                depth=depth,
                index=index,
                # BottleNumber=bottle_order[index],
                BottleNumber=new_bottle_order[index],
                FireAt=pres
            ))
            index += 1
        return data

    def set_auto_fire_bottles(self, data: psa.AUTO_FIRE_DATA_DATATYPE, station: str) -> None:
        pressure_mapping = self.get_pressure_mapping_for_station(station)
        data_with_pressure = []
        for i, d in enumerate(sorted(data, reverse=True, key=lambda x: x['depth'])):
            offset = d.get('offset') or 0
            row_data= dict(
                index=i,
                BottleNumber=d['BottleNumber'],
                FireAt=pressure_mapping[int(d['depth'])] + offset
            )
            data_with_pressure.append(row_data)
        self._set_auto_fire_bottles(data_with_pressure)

    def set_auto_fire_default_bottles_for_station(self, station: str):
        data = self.get_auto_fire_info_for_station(station)
        self._set_auto_fire_bottles(data)

    def _set_auto_fire_bottles(self, data: psa.AUTO_FIRE_DATA_DATATYPE) -> None:
        self.check_valid_auto_fire_data(data)
        self.seasave_psa.auto_fire_bottles = data
        # self.seasave_psa.save(path=r"C:\mw\git\ctd_config\SBE\seasave_psa\svea\Seasave_mod.psa")

    def check_valid_auto_fire_data(self, data: psa.AUTO_FIRE_DATA_DATATYPE):

        tot_nr_btl = self.seasave_psa.nr_of_water_bottles
        if len(data) > tot_nr_btl:
            raise exceptions.ToManyAutoFireDepths(f'Nr of depths are more than nr of water bottles')

        bottles = [item['BottleNumber'] for item in data]
        if len(bottles) != len(set(bottles)):
            raise exceptions.DuplicatedAutoFireBottles

    def enable_auto_fire(self):
        self.seasave_psa.auto_fire = True

    def disable_auto_fire(self):
        self.seasave_psa.auto_fire = False

    def set_auto_fire(self, value: bool):
        self.seasave_psa.auto_fire = value
        self.seasave_psa.auto_fire_allow_manual_firing = value

    @property
    def auto_fire_min_pressure_or_depth(self) -> str:
        return self.seasave_psa.min_pressure_or_depth

    @auto_fire_min_pressure_or_depth.setter
    def auto_fire_min_pressure_or_depth(self, press: int | str | float):
        self.seasave_psa.min_pressure_or_depth = press





if __name__ == '__main__':
    sbe_paths = paths.SBEPaths()
    c = Controller(paths_object=sbe_paths)
    c.ctd_config_root_directory = r'C:\mw\git\ctd_config'
    c.ctd_data_root_directory = r'C:\mw\temp_ctd_pre_system_data_root'
    c.update_main_psa_file(instrument='sbe09', cruise_nr='01', ship_code='77SE', serno='0001')
    # c.run_seasave()
