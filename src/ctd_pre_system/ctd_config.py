from pathlib import Path
import yaml


class CtdConfig:
    def __init__(self, root_directory):

        self.root_directory = Path(root_directory)

        self.resource_settings_file_path = Path(Path(__file__).parent, 'resources', 'ctd_config.yaml')

        self._config = {}

        self._load_config_file()
        self._save_paths()

    def _load_config_file(self):
        with open(self.resource_settings_file_path, 'r') as fid:
            try:
                self._config = yaml.safe_load(fid)
            except yaml.YAMLError as exc:
                self.root_directory = None
                raise exc

    def _get_path(self, *args, must_exist=True, path_if_not_paths=False, suffix=''):
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
        if must_exist and not full_path.exists():
            raise FileNotFoundError(full_path)
        if full_path.is_dir():
            full_path = self._get_paths_in_directory(full_path, path_if_not_paths=path_if_not_paths, suffix=suffix)
        else:
            if not full_path.suffix.lower().endswith(suffix.lower()):
                return None
        return full_path

    def _get_paths_in_directory(self, directory, path_if_not_paths=False, suffix=''):
        if not directory.is_dir():
            raise NotADirectoryError
        paths = []
        for path in directory.iterdir():
            if not path.is_file():
                continue
            if not path.suffix.lower().endswith(suffix.lower()):
                continue
            paths.append(path)

        if len(paths) == 1 and path_if_not_paths:
            paths = paths[0]
        return paths

    def _save_paths(self):
        self.seasave_program_path = self._get_path('seasave', 'program')
        self.seasave_psa_main_file = self._get_path('seasave', 'psa_main_file')

        self._save_path_sbe09()
        self._save_path_sbe19()

    def _save_path_sbe09(self):
        self.seasave_sbe09_xmlcon_file = self._get_path('seasave', 'xmlcon_files', 'SBE09', path_if_not_paths=True, suffix='xmlcon')
        if not self.seasave_sbe09_xmlcon_file:
            raise FileNotFoundError(f'No xmlcon file found for SEB09')
        if type(self.seasave_sbe09_xmlcon_file) == list:
            raise FileExistsError(f'Too many xmlcon files found for SBE09 in directory: {self.seasave_sbe09_xmlcon_file[0].parent}')

    def _save_path_sbe19(self):
        self.seasave_sbe19_xmlcon_file = self._get_path('seasave', 'xmlcon_files', 'SBE19', path_if_not_paths=True, suffix='xmlcon')
        if not self.seasave_sbe19_xmlcon_file:
            raise FileNotFoundError(f'No xmlcon file found for SEB19')
        if type(self.seasave_sbe19_xmlcon_file) == list:
            raise FileExistsError(f'Too many xmlcon files found for SBE19 in directory: {self.seasave_sbe19_xmlcon_file[0].parent}')


if __name__ == '__main__':
    r = CtdConfig(r'C:\mw\git\ctd_config')
