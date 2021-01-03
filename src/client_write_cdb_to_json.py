import os
import json
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from sof_read import SofReader
import io_manager as iom


def read_cdb():
    root = Tk()
    root.withdraw()
    cdb_path = askopenfilename(filetypes = (("SOFiSTiK database", ".cdb"),))
    root.quit()

    with SofReader(cdb_path) as cdb:
        cdb.read_geometry()
        geo_dict = cdb.data

    json_path = (os.path.join(os.path.dirname(cdb_path),
                 os.path.split(cdb_path)[-1][:-4] + ".json"))
    iom.write_to_json(geo_dict, json_path)
    print("\nDatabase .cdb file exported to .json:\n{0}".format(json_path))


if __name__ == "__main__":
    read_cdb()