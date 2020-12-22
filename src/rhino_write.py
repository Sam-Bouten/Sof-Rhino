# -*- coding: utf-8 -*-
from collections import namedtuple
import System.Drawing.Color as color
import Rhino as rc
import Rhino.Geometry as rg
import scriptcontext as sc


__all__ = [
    "write_sof_geometry",
    "add_sof_layer",
    "get_unit_scale",
    "scale_xyz"
    ]


def write_sof_geometry(cdb_dict):
    """Add SOFiSTiK geometry objects and their attributes into Rhino document.
    
    Parameters
    ----------
    cdb_dict : dictionary
        All SOFiSTiK cdb data serialized in a dictionary.
    """
    print("Writing SOFiSTiK data into Rhino document...")
    for type_name, sof_data in cdb_dict.items():
        geo_type = sof_geometry_types.get(type_name)
        if not geo_type: continue

        # get layer for SOFiSTiK objects
        sof_layer = add_sof_layer(geo_type.layer_name, geo_type.layer_color)

        for sof_id, sof_atts in sof_data.items():
            # generate Rhino object
            obj = geo_type.generate(cdb_dict, sof_atts)
            if not obj: continue
            att = sc.doc.CreateDefaultAttributes()
            att.Name = geo_type.name_prefix + str(sof_id)
            att.LayerIndex = sof_layer.Index

            # add SOFiSTiK attributes as user text
            for att_key, att_value in sof_atts.items():
                if att_key in geo_type.ignore_attributes: continue
                if isinstance(att_value, list):
                    att_value = ", ".join( str(i) for i in (att_value))
                att.SetUserString(str(att_key), str(att_value))

            # add Rhino object to document
            guid = geo_type.add(obj, att)
            if not guid: print("SOFiSTiK object {0} could not be added.".format(att.Name))
    
    sc.doc.Objects.UnselectAll()
    sc.doc.Views.Redraw()


def add_sof_layer(layer_name, layer_color):
    """Add layer to Rhino document, or clear object from layer if pre-existing.
    
    Parameters
    ----------
    layer_name : string
        Layer name in Rhino document.
    layer_color: string
        Layer color in Rhino document.
    
    Returns
    -------
    sof_layer : RhinoDoc.DocObjects.Layer
        Rhino layer object with input properties.
    """
    sof_layer = sc.doc.Layers.FindName(layer_name)
    if sof_layer:
        obj_to_clear = sc.doc.Objects.FindByLayer(layer_name)
        for obj in obj_to_clear:
            sc.doc.Objects.Delete(obj, True)
    else:
        sof_layer = rc.DocObjects.Layer()
        sof_layer.Name = layer_name
        sof_layer.Color = layer_color
        sc.doc.Layers.Add(sof_layer)
        sof_layer = sc.doc.Layers.FindName(layer_name)
    return sof_layer


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


def generate_node(cdb_dict, sof_atts):
    """Generate Rhino Point3d geometry for SOFiSTiK node."""
    try: return rg.Point3d(*sof_atts["xyz"])
    except: return None


def generate_beam(cdb_dict, sof_atts):
    """Generate Rhino Line geometry for SOFiSTiK beam."""
    sof_sp, sof_ep = sof_atts["nodes"]
    sp = rg.Point3d(*cdb_dict["nodes"][sof_sp]["xyz"])
    ep = rg.Point3d(*cdb_dict["nodes"][sof_ep]["xyz"])
    try: return rg.Line(sp, ep)
    except: return None


def generate_truss(cdb_dict, sof_atts):
    """Generate Rhino Line geometry for SOFiSTiK truss."""
    sof_sp, sof_ep = sof_atts["nodes"]
    sp = rg.Point3d(*cdb_dict["nodes"][sof_sp]["xyz"])
    ep = rg.Point3d(*cdb_dict["nodes"][sof_ep]["xyz"])
    try: return rg.Line(sp, ep)
    except: return None


def generate_cable(cdb_dict, sof_atts):
    """Generate Rhino Line geometry for SOFiSTiK cable."""
    sof_sp, sof_ep = sof_atts["nodes"]
    sp = rg.Point3d(*cdb_dict["nodes"][sof_sp]["xyz"])
    ep = rg.Point3d(*cdb_dict["nodes"][sof_ep]["xyz"])
    try: return rg.Line(sp, ep)
    except: return None


def generate_spring(cdb_dict, sof_atts):
    """Generate Rhino Line geometry for SOFiSTiK spring."""
    sof_sp, sof_ep = sof_atts["nodes"]
    sp = rg.Point3d(*cdb_dict["nodes"][sof_sp]["xyz"])
    if sof_ep == 0: # support spring
        direction = rg.Vector3d(*sof_atts["normal"])
        try: return rg.Line(sp, direction, 0.1 * get_unit_scale())
        except: return None
    else: # connective spring
        ep = rg.Point3d(*cdb_dict["nodes"][sof_ep]["xyz"])
        try: return rg.Line(sp, ep)
        except: return None


def generate_quad(cdb_dict, sof_atts):
    """Generate Rhino Brep geometry for SOFiSTiK quad."""
    sof_pts = sof_atts["nodes"]
    pts = [rg.Point3d(*xyz) for xyz in
          [cdb_dict["nodes"][sof_pt]["xyz"] for sof_pt in sof_pts]]
    try: return rg.Brep.CreateFromCornerPoints(*set(pts), tolerance=0.0001)
    except: return None


def generate_bric(cdb_dict, sof_atts):
    """Generate Rhino Mesh geometry for SOFiSTiK bric."""
    sof_pts = sof_atts["nodes"]
    if sof_pts[3] == 0: # tetrahedral geometry
        lookup_pts = [sof_pts[i] for i in (0,1,2,5)]
        generate_func = _generate_tetrahedron
    else: # hexahedral geometry
        lookup_pts = sof_pts
        generate_func = _generate_hexahedron
    
    pts = [rg.Point3d(*xyz) for xyz in
          [cdb_dict["nodes"][sof_pt]["xyz"] for sof_pt in lookup_pts]]
    return generate_func(pts)


def _generate_tetrahedron(points):
    """Generate Rhino Mesh geometry for SOFiSTiK tetrahedral bric."""
    try:
        mesh = rg.Mesh()
        for pt in points:
            mesh.Vertices.Add(pt)
        for pt_set in ((0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)):
            mesh.Faces.AddFace(*pt_set)
        return mesh
    except: return None


def _generate_hexahedron(points):
    """Generate Rhino Mesh geometry for SOFiSTiK hexahedral bric."""
    try:
        mesh = rg.Mesh()
        for pt in points:
            mesh.Vertices.Add(pt)
        for pt_set in ((0, 1, 2, 3), (0, 3, 7, 4), (4, 7, 6, 5),
                    (1, 5, 6, 2), (0, 4, 5, 1), (2, 6, 7, 3)):
            mesh.Faces.AddFace(*pt_set)
        return mesh
    except: return None


sof_geo_type = namedtuple("sof_geo", ["name_prefix", "layer_name", "layer_color", "generate", "add", "ignore_attributes"])
sof_geometry_types = {
    "nodes": sof_geo_type("N",  "SOF_nodes",    color.MediumBlue,   generate_node,     sc.doc.Objects.AddPoint,    ("xyz",)),
    "beams": sof_geo_type("B",  "SOF_beams",    color.DarkBlue,     generate_beam,     sc.doc.Objects.AddLine,     ("nodes", "length")),
    "trusses": sof_geo_type("B","SOF_trusses",  color.Turquoise,    generate_truss,    sc.doc.Objects.AddLine,     ("nodes", "length")),
    "cables": sof_geo_type("C", "SOF_cables",   color.Crimson,      generate_cable,    sc.doc.Objects.AddLine,     ("nodes", "length")),
    "springs": sof_geo_type("C","SOF_springs",  color.Lime,         generate_spring,   sc.doc.Objects.AddLine,     ("nodes",)),
    "quads": sof_geo_type("Q",  "SOF_quads",    color.LightBlue,    generate_quad,     sc.doc.Objects.AddBrep,     ("nodes", "area")),
    "brics": sof_geo_type("V",  "SOF_brics",    color.Orange,       generate_bric,     sc.doc.Objects.AddMesh,     ("nodes", "volume"))
}


if __name__=="__main__":
    pass