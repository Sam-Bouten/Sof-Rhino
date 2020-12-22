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
    browser.Filter = "JSON files (*.json)|*.json"
    if browser.ShowDialog() == System.Windows.Forms.DialogResult.OK:
        json_path = browser.FileName
        cdb_dict = read_from_json(json_path)
        scale_xyz(cdb_dict)
        write_sof_geometry(cdb_dict)