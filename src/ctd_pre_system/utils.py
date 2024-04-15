import json
import numpy as np


def load_json(file_path):
    with open(file_path, 'r') as fid:
        return json.load(fid)


def save_json(data=None, file_path=None, indent=4):
    with open(file_path, 'w') as fid:
        json.dump(data, fid, indent=indent)


def decdeg_to_decmin(pos, string_type=False, decimals=False):
    # TODO, add if else for negative position (longitude west of 0 degrees)
    if type(pos) in [set, list, tuple]:
        output = []
        for p in pos:
            p = float(p)
            deg = np.floor(p)
            minut = p % deg * 60.0
            if string_type:
                if decimals is not False:
                    output.append('%%2.%sf' % decimals % (deg * 100.0 + minut))
                else:
                    output.append(str(deg * 100.0 + minut))
            else:
                output.append(deg * 100.0 + minut)
    else:
        pos = float(pos)
        deg = np.floor(pos)
        minut = pos % deg * 60.0
        if string_type:
            if decimals is not False:
                output = ('%%2.%sf' % decimals % (deg * 100.0 + minut))
            else:
                output = (str(deg * 100.0 + minut))
        else:
            output = (deg * 100.0 + minut)

    return output


def decmin_to_decdeg(pos, return_string=False):
    #    print type(pos),pos
    try:
        if type(pos) in [set, list, tuple]:
            output = []
            for p in pos:
                p = float(p)
                if p >= 0:
                    output.append(np.floor(p / 100.) + (p % 100) / 60.)
                else:
                    output.append(np.ceil(p / 100.) - (-p % 100) / 60.)
        else:
            pos = float(pos)
            if pos >= 0:
                output = np.floor(pos / 100.) + (pos % 100) / 60.
            else:
                output = np.ceil(pos / 100.) - (-pos % 100) / 60.

        if return_string:
            if type(output) is list:
                return map(str, output)
            else:
                return str(output)
        else:
            return output
    except:
        return pos