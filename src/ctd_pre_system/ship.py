
from ctd_pre_system.resource import Resources


class Ships:

    def __init__(self, root_directory=None):
        self.root_directory = root_directory
        self._resources = Resources(root_directory=root_directory)
        self._code_to_name = {}
        self._name_to_code = {}
        self.all_items = []
        self._load_file()

    def _load_file(self):
        self._code_to_name = {}
        self._name_to_code = {}
        self.all_items = []
        with open(self._resources.ship_file) as fid:
            for r, line in enumerate(fid):
                line = line.strip()
                if not line:
                    continue
                split_line = line.split('\t')
                if r == 0:
                    header = split_line
                    continue
                line_dict = dict(zip(header, split_line))
                self._code_to_name[line_dict['code']] = line_dict['name']
                self._name_to_code[line_dict['name']] = line_dict['code']
                self.all_items.append(line_dict['name'])
                self.all_items.append(line_dict['code'])

    def _assert_ship(self, ship):
        if ship not in self.all_items:
            raise ValueError(f'Could not find ship: {ship}')

    def get_code(self, ship_name):
        self._assert_ship(ship_name)
        return self._name_to_code.get(ship_name, ship_name)

    def get_name(self, ship_code):
        self._assert_ship(ship_code)
        return self._code_to_name.get(ship_code, ship_code)


if __name__ == '__main__':
    s = Ships()
