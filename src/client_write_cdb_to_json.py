import os
import json
from sof_read import SofReader
import io_manager as iom
from tkinter import Tk
from tkinter.filedialog import askopenfilename


def read_cdb():
    Tk().withdraw()
    cdb_path = askopenfilename(filetypes = (("SOFiSTiK database", ".cdb"),))

    with SofReader(cdb_path) as cdb:
        cdb.read_geometry()
        geo_dict = cdb.data

    json_path = (os.path.join(os.path.dirname(cdb_path),
                 os.path.split(cdb_path)[-1][:-4] + ".json"))
    iom.write_to_json(geo_dict, json_path)
    print("\nDatabase .cdb file exported into .json:\n{0}".format(json_path))


if __name__ == "__main__":
    read_cdb()