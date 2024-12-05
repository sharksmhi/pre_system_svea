import pathlib
from typing import Dict

import pandas as pd
import numpy as np
from ctd_pre_system import resource
import yaml

resources = resource.Resources()


class StationBasin:

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = pathlib.Path(path)
        self._station_to_basin = {}
        self._basin_to_station = {}

        self._load_file()

    def _load_file(self) -> None:
        with open(self._path, encoding='cp1252') as fid:
            for line in fid:
                if not line.strip():
                    continue
                split_line = [item.strip() for item in line.upper().split('\t')]
                if len(split_line) != 2:
                    print(f'No station or basin found in line: {split_line}')
                    continue
                stat, bas = split_line
                self._station_to_basin[stat] = bas
                self._basin_to_station[bas] = stat

    def get_basin(self, station: str) -> str | None:
        return self._station_to_basin.get(station.upper())

    def get_station(self, basin: str) -> str | None:
        return self._basin_to_station.get(basin.upper())


class PressureMatrix:

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = pathlib.Path(path)
        self._data: pd.DataFrame | None = None

        self._load_file()
        self._filter_data()

    def _load_file(self) -> None:
        self._data = pd.read_csv(self._path, encoding='cp1252', sep='\t', comment='#')

    def _filter_data(self) -> None:
        self._data = self._data.loc[~self._data['djup'].isna(), :]
        # self._data.fillna('', inplace=True)
        self._data = self._data.replace(np.nan, '')

    def get_depth_list(self) -> list[int]:
        return [int(item) for item in self._data.loc[:, 'djup'].values]

    def get_basin_list(self) -> list[str]:
        return [col for col in self._data.columns if col not in ['djup']]

    def get_depth_pressure_mapping_for_basin(self, basin: str) -> dict[int, float]:
        data = {}
        for depth, pressure in zip(self._data['djup'], self._data[basin]):
            data[depth] = pressure
        return data


class StationPressures:

    def __init__(self,
                 station_basin: StationBasin,
                 pressure_matrix: PressureMatrix,
                 ):
        self._station_basin = station_basin
        self._pressure_matrix = pressure_matrix

    def get_depth_pressure_mapping_for_basin(self, basin: str) -> dict[str, dict[int, float] | str]:
        mapping = self._pressure_matrix.get_depth_pressure_mapping_for_basin(basin)
        return dict(pressure_mapping=mapping, basin=basin)

    def get_depth_pressure_mapping_for_station(self, station: str) -> dict[str, dict[int, float] | str | None]:
        basin = self._station_basin.get_basin(station)
        mapping = self._pressure_matrix.get_depth_pressure_mapping_for_basin(basin)
        return dict(pressure_mapping=mapping, basin=basin)
        # return mapping


class BottleOrder:

    def __init__(self, path: str | pathlib.Path):
        self._path = pathlib.Path(path)
        self._data = {}

        self._load_file()

    def _load_file(self):
        with open(self._path) as fid:
            self._data = yaml.safe_load(fid)

    def get_bottle_order(self, nr_bottles: int) -> list[int]:
        return self._data.get(nr_bottles, [])


def get_station_pressure_object():
    stat_bas = StationBasin(resources.station_filter_file)
    pres_mat = PressureMatrix(resources.pressure_matrix_file)
    return StationPressures(stat_bas, pres_mat)


def get_bottle_order_object():
    return BottleOrder(resources.auto_fire_bottle_order_file)

if __name__ == '__main__':
    # sb = StationBasin(r'c:\mw\git\pre_system_svea\src\ctd_pre_system\resources\stationslista_matprogram.txt')
    # pm = PressureMatrix(r'c:\mw\git\pre_system_svea\src\ctd_pre_system\resources\pressure_matrix.txt')
    # sp = StationPressures(sb, pm)

    sp = get_station_pressure_object()

    print(sp.get_depth_pressure_mapping_for_station('by10'))


