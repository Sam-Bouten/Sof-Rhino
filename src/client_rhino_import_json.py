# -*- coding: utf-8 -*-
import os
import sys
sys.path += [os.getcwd()]
import System
import Rhino.UI as ui
from file_manager import *
from sof_read import *
from rhino_write import *


def import_sof_json():
    "Import SOFiSTiK database JSON (.json) file into current Rhino document."
    browser = ui.OpenFileDialog()
    browser.Title = "Select SOFiSTiK database .json file to import."
    browser.Filter = "JSON files (*.json)|*.json"
    if browser.ShowDialog() == System.Windows.Forms.DialogResult.OK:
        json_path = browser.FileName
        cdb_dict = read_from_json(json_path)
        scale_xyz(cdb_dict)
        write_sof_geometry(cdb_dict)


if __name__ == "__main__":
    import_sof_json()