# -*- coding: utf-8 -*-
import os
import sys
sys.path += [os.getcwd()]

import System
import Rhino.UI as ui
import rhinoscriptsyntax as rs
import scriptcontext as sc

import io_manager as iom
import rhino_write as rw


def import_sof_json():
    "Import SOFiSTiK database JSON (.json) file into current Rhino document."
    browser = ui.OpenFileDialog()
    browser.Title = "Select SOFiSTiK database .json file to import."
    browser.Filter = "JSON files (*.json)|*.json"
    if browser.ShowDialog() == System.Windows.Forms.DialogResult.OK:
        json_path = browser.FileName
        
        cdb_dict = iom.read_from_json(json_path)
        rw.scale_xyz(cdb_dict)
        rw.write_sof_geometry(cdb_dict)

        rs.ZoomExtents(all=True)
        sc.doc.Objects.UnselectAll()
        sc.doc.Views.Redraw()


if __name__ == "__main__":
    import_sof_json()