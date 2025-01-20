from pathlib import Path
import yaml


class Resources:
    def __init__(self, root_directory=None):
        if root_directory:
            self.root_directory = Path(root_directory)
        else:
            self.root_directory = Path(Path(__file__).parent, 'resources')

        self.resource_settings_file_path = Path(Path(__file__).parent, 'resources', 'resources.yaml')

        self.operator_file = None
        self.operator_file_encoding = None
        self.ship_file = None
        self.ship_file_encoding = None
        self.backup_station_file = None
        self.backup_station_file_encoding = None
        self.primary_station_file_url = None
        self.primary_station_file_url_encoding = None
        self.update_primary_station_file = False
        self.station_filter_file = None
        self.station_filter_file_encoding = None
        self.pressure_matrix_file = None
        self.auto_fire_bottle_order_file = None

        self._config = {}

        self._load_resources()
        self._save_paths()

    def _load_resources(self):
        with open(self.resource_settings_file_path, 'r') as fid:
            try:
                self._config = yaml.safe_load(fid)
            except yaml.YAMLError as exc:
                print(exc)

    def _get_path(self, *args, must_exist=True):
        item = self._config
        for arg in args:
            item = item.get(arg, {})
        path = item.get('path', '')
        if not path:
            raise ValueError
        if path.startswith('root'):
            full_path = Path(self.root_directory, path[5:])
        else:
            full_path = Path(path)
        try:
            if must_exist and not full_path.exists():
                raise FileNotFoundError(full_path)
            if full_path.is_dir():
                full_path = self._get_paths_in_directory(full_path)
        except OSError:
            pass
        except Exception:
            raise
        return full_path

    def _get_encoding(self, *args):
        item = self._config
        for arg in args:
            item = item.get(arg, {})
        return item.get('encoding', '')

    def _get_paths_in_directory(self, directory):
        if not directory.is_dir():
            raise NotADirectoryError
        return [path for path in directory.iterdir()]

    def _save_paths(self):
        # self.operator_file = self._get_path('operators')
        # self.station_file = self._get_path('stations', 'sekundär_stationslista')
        # self.station_filter_file = self._get_path('stations', 'filter')
        # self.ship_file = self._get_path('ships')

        self.operator_file = self._get_path('operators')
        self.operator_file_encoding = self._get_encoding('operators')
        self.ship_file = self._get_path('ships')
        self.ship_file_encoding = self._get_encoding('ships')
        self.backup_station_file = self._get_path('stations', 'backup_station_list')
        self.backup_station_file_encoding = self._get_encoding('stations', 'backup_station_list')
        self.primary_station_file_url = self._get_path('stations', 'primary_station_list_url', must_exist=False)
        self.primary_station_file_url_encoding = self._get_encoding('stations', 'primary_station_list_url')
        self.update_primary_station_file = self._config.get('stations', {}).get('primary_station_list_url', {}).get('update', False)
        self.station_filter_file = self._get_path('stations', 'filter')
        self.station_filter_file_encoding = self._get_encoding('stations', 'filter')
        self.pressure_matrix_file = self._get_path('auto_fire', 'pressure_matrix')
        self.auto_fire_bottle_order_file = self._get_path('auto_fire', 'bottle_order')

        
if __name__ == '__main__':
    r = Resources()