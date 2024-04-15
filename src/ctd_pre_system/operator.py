
from ctd_pre_system.resource import Resources
from ctd_pre_system import utils


class Operators:
    def __init__(self, root_directory=None):
        self._resources = Resources(root_directory=root_directory)
        self.file_path = self._resources.operator_file

        self._data = {}
        self._load_file()

    def _load_file(self):
        self._data = utils.load_json(self.file_path)

    def _save_file(self):
        utils.save_json(self._data, self.file_path)

    def get_operator_list(self):
        return sorted(self._data)

    def get_full_name(self, short_name, default=None):
        return self._data.get(short_name, default)
