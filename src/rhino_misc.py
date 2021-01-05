# -*- coding: utf-8 -*-
import System
import clr
clr.AddReference("MathNet.Numerics.dll")
import MathNet.Numerics.LinearAlgebra as num
import Rhino.Geometry as rg
import scriptcontext as sc


__all__ = [
    "get_unit_scale",
    "scale_xyz",
    "scale_centric",
    "get_layer_progeny",
    "get_principal_stresses"
    ]


def get_unit_scale():
    """Return scale factor according to active Rhino document unit system."""
    if "scale" not in globals():
        global scale
        units = sc.doc.ModelUnitSystem
        if str(units) == "Meters": scale = 1.0
        elif str(units) == "Millimeters": scale = 1000.0
        elif str(units) == "Centimeters": scale = 100.0
        elif str(units) == "Feet": scale = 3.28084
        elif str(units) == "Inches": scale = 39.3701
        else: scale = 1.0
    return globals()["scale"]


def scale_xyz(cdb_dict):
    """Scale nodal coordinates in cdb dictionary, in place."""
    scale = get_unit_scale()
    for node_id in cdb_dict["nodes"].keys():
        cdb_dict["nodes"][node_id]["xyz"] = [scale * c for c in cdb_dict["nodes"][node_id]["xyz"]]


def scale_centric(layer_name, scale):
    """Scale objects in layer its progeny layers about their centroid."""
    sc.doc.Views.RedrawEnabled = False
    
    for layer in get_layer_progeny(layer_name):
        objs = (o for o in sc.doc.Objects.FindByLayer(layer))
        if not objs: continue
        for obj in objs:
            geo = obj.Geometry.Duplicate()
            if isinstance(geo, rg.Curve):
                centroid = geo.PointAtNormalizedLength(0.5)
            elif isinstance(geo, rg.Brep):
                am = rg.AreaMassProperties.Compute(geo)
                centroid = am.Centroid
            elif isinstance(geo, rg.TextDot):
                continue
            xs = rg.Transform.Scale(centroid, scale)
            geo.Transform(xs)
            sc.doc.Objects.Add(geo, obj.Attributes)
            sc.doc.Objects.Delete(obj)
    
    sc.doc.Objects.UnselectAll()
    sc.doc.Views.RedrawEnabled = True
    sc.doc.Views.Redraw()


def get_layer_progeny(layer_name, layer_list=None):
    """Recursively get child layer names of layer."""
    layers = layer_list or [layer_name]
    parent_layer = sc.doc.Layers.FindName(layer_name)
    child_layers = parent_layer.GetChildren()
    if child_layers:
        for child in child_layers:
            layers.append(child.Name)
            get_layer_progeny(child.Name, layer_list=layers)
    return layers


def get_principal_stresses(stress_dict):
    """Get principal stress eigenvalues and corresponding eigenvectors."""
    # unpack global coordinate stress components
    σx = stress_dict["sigx"]  ; σy = stress_dict["sigy"]  ; σz = stress_dict["sigz"]
    τxy = stress_dict["tauxy"]; τxz = stress_dict["tauxz"]; τyz = stress_dict["tauyz"]

    stress_tensor = [ [σx, τxy, τxz],
                      [τxy, σy, τyz],
                      [τxz, τyz, σz] ]

    stress_mat = _convert_list_mat(stress_tensor)

    # get principal stresses as tensor eigenvalues
    stress_EVD = stress_mat.Evd()
    principal_stresses = [ev.real for ev in _convert_mat_list(stress_EVD.EigenValues)]
    principal_vectors = _convert_mat_list(stress_EVD.EigenVectors)
    return principal_stresses, principal_vectors


def _convert_list_mat(nested_list, row_major=True):
    """Convert a nested list to a math.NET matrix."""
    array = []
    if row_major:
        for in_list in nested_list:
            array.append(System.Array[float](in_list))
        return num.Double.Matrix.Build.DenseOfColumnArrays(tuple(array))
    else:
        for in_list in nested_list:
            array.append(System.Array[float](in_list))
        return num.Double.Matrix.Build.DenseOfRowArrays(tuple(array))


def _convert_mat_list(dn_mat):
    """Convert a math.NET matrix or vector into a (column major) list."""
    if "Vector" in str(type(dn_mat)):
        dn_list = [var for var in dn_mat]
    elif "Matrix" in str(type(dn_mat)):
        dn_list = [ [var for var in dn_mat.Column(col)]
                    for col in range(dn_mat.ColumnCount) ]
    elif isinstance(dn_mat, list):
        dn_list = dn_mat
    return dn_list


if __name__ == "__main__":
    pass