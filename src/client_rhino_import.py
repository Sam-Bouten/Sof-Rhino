# -*- coding: utf-8 -*-
import os
import sys
sys.path += [os.getcwd()]

import System
import Rhino.UI as ui
import rhinoscriptsyntax as rs
import scriptcontext as sc

import io_manager as iom
from sof_read import SofReader
import rhino_write as rw
import rhino_misc as rm


def import_sof_cdb():
    "Import SOFiSTiK database (.cdb) file into current Rhino document."
    browser = ui.OpenFileDialog()
    browser.Title = "Select SOFiSTiK database .cdb file to import."
    browser.Filter = "SOFiSTiK database files (*.cdb)|*.cdb"
    if browser.ShowDialog() == System.Windows.Forms.DialogResult.OK:
        cdb_path = browser.FileName

        with SofReader(cdb_path) as cdb:
            cdb.read_geometry()
            cdb.read_bric_stresses()
            cdb_dict = cdb.data
        rm.scale_xyz(cdb_dict)
        rw.write_sof_geometry(cdb_dict)
        rw.write_sof_results(cdb_dict)

        rs.ZoomExtents(all=True)
        sc.doc.Objects.UnselectAll()
        sc.doc.Views.Redraw()



if __name__ == "__main__":
    import_sof_cdb()

    # obj = sc.doc.Objects.FindByUserString("name", "B110062", True)
    # print(obj)[0].Geometry.PointAtStart