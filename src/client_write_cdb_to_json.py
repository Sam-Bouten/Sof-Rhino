import os
import json
from sof_read import *
from file_manager import *
from tkinter import Tk
from tkinter.filedialog import askopenfilename


if __name__ == "__main__":
    Tk().withdraw()
    cdb_path = askopenfilename(filetypes = (("SOFiSTiK database", ".cdb"),))

    cdb_records = read_geometry()
    cdb_dict = read_cdb(cdb_path, cdb_records)

    json_path = (os.path.dirname(cdb_path) + "/"
               + os.path.split(cdb_path)[-1][:-4] + ".json")
    write_to_json(cdb_dict, json_path)

    print("\nDatabase .cdb file exported into .json format:\n{0}".format(json_path))