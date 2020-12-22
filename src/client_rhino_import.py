# -*- coding: utf-8 -*-
import os
import sys
sys.path += [os.getcwd()]
import System
import Rhino.UI as ui
from file_manager import *
from sof_read import *
from rhino_write import *


def import_sof_cdb():
    "Import SOFiSTiK database (.cdb) file into current Rhino document."
    browser = ui.OpenFileDialog()
    browser.Title = "Select SOFiSTiK database .cdb file to import."
    browser.Filter = "SOFiSTiK database files (*.cdb)|*.cdb"
    if browser.ShowDialog() == System.Windows.Forms.DialogResult.OK:
        cdb_path = browser.FileName
        cdb_read_records = read_geometry()
        cdb_dict = read_cdb(cdb_path, cdb_read_records)
        scale_xyz(cdb_dict)
        write_sof_geometry(cdb_dict)


if __name__ == "__main__":
    import_sof_cdb()