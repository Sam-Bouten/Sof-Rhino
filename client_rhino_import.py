# -*- coding: utf-8 -*-
import sys
sys.path += ["C:\\Users\\sbouten\\Desktop\\Sof_Rhino"]
import System
import Rhino.UI as ui
from file_manager import *
from sof_read import *
from rhino_write import *


if __name__ == "__main__":
    browser = ui.OpenFileDialog()
    browser.Filter = "SOFiSTiK database files (*.cdb)|*.cdb"
    if browser.ShowDialog() == System.Windows.Forms.DialogResult.OK:
        cdb_path = browser.FileName
        cdb_read_records = read_geometry()
        cdb_dict = read_cdb(cdb_path, cdb_read_records)
        scale_xyz(cdb_dict)
        write_sof_geometry(cdb_dict)