# -*- coding: utf-8 -*-
from collections import namedtuple, OrderedDict

import System
import System.Drawing.Color as color
import Rhino as rc
import Rhino.Geometry as rg
import scriptcontext as sc
import rhinoscriptsyntax as rs
import rhino_misc as rm


__all__ = [
    "write_sof_geometry",
    "write_sof_results"
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
            att.SetUserString("name", att.Name)
            att.LayerIndex = sof_layer.Index

            # add SOFiSTiK attributes as user text
            for att_key, att_value in sof_atts.items():
                if att_key in geo_type.ignore_attributes: continue
                if isinstance(att_value, list):
                    att_value = ", ".join(str(i) for i in (att_value))
                att.SetUserString(str(att_key), str(att_value))

            # add Rhino object to document
            guid = geo_type.add(obj, att)
            if not guid: print("SOFiSTiK object {0} could not be added.".format(att.Name))


def write_sof_results(cdb_dict):
    """Add SOFiSTiK result objects and their attributes into Rhino document."""
    return generate_bric_stresses(cdb_dict)
    #TODO add generalized result processor which calls result generation functions,
    #   similar to write_sof_geometry()


def add_sof_layer(layer_name, layer_color=color.Black, parent_layer=None):
    """Add layer to Rhino document, clear all objects from layer if pre-existing.
    
    Parameters
    ----------
    layer_name : string
        Layer name in Rhino document.
    
    layer_color: string
        Layer color in Rhino document.
    
    parent_layer : string
        Parent layer name in Rhino document.
    
    Returns
    -------
    sof_layer : RhinoDoc.DocObjects.Layer
        Rhino layer object with input properties.
    """
    purge_sof_layers()
    master_layer = add_sof_master_layer()
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
    
    if parent_layer:
        p_layer = sc.doc.Layers.FindName(parent_layer)
        if p_layer:
            sof_layer.ParentLayerId = p_layer.Id
    else:
        sof_layer.ParentLayerId = master_layer.Id
        
    return sof_layer


def add_sof_master_layer():
    """Add topmost SOFiSTiK parent layer to Rhino document."""
    master_name = "SOF"
    check_layer = sc.doc.Layers.FindName(master_name)
    if check_layer: return check_layer
    master_layer = rc.DocObjects.Layer()
    master_layer.Name = master_name
    sc.doc.Layers.Add(master_layer)
    master_layer = sc.doc.Layers.FindName(master_name)
    return master_layer


def purge_sof_layers():
    """Clear all SOFiSTiK layers."""
    if "sof_purged" in globals(): return
    master_name = "SOF"
    check_layer = sc.doc.Layers.FindName(master_name)
    if check_layer:
        existing_layers = rm.get_layer_progeny(master_name)
        for layer_name in reversed(existing_layers):
            rs.PurgeLayer(layer_name)

    global sof_purged
    sof_purged = True


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
        try: return rg.Line(sp, direction, 0.1 * rm.get_unit_scale())
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
    pts = list(OrderedDict.fromkeys(pts))
    try: return rg.Brep.CreateFromCornerPoints(*pts, tolerance=0.0001)
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
    
    centroid = [sum(c) / len(pts) for c in zip(*pts)] 
    sof_atts["centroid"] = centroid

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


def generate_bric_stresses(cdb_dict):
    """Generate Rhino line geometry for SOFiSTiK bric."""
    #TODO generalize result processor in write_sof_results()
    result_data = cdb_dict.get("bric_stresses")
    if not result_data: return

    # set result layers
    results_layer = add_sof_layer("SOF_Results")
    add_sof_layer("SOF_Bric_Stress", parent_layer="SOF_Results")
    for load_case, load_case_results in result_data.items():
        load_case_name = "LC" + str(load_case)
        load_case_layer = add_sof_layer(load_case_name, parent_layer="SOF_Bric_Stress")
        load_case_layer.IsVisible = False
        load_case_layer.SetPersistentVisibility(True)

        layer_names = ["σI_" + str(load_case), "σII_" + str(load_case), "σIII_" + str(load_case)]
        stress_layers =  [add_sof_layer(layer_name, parent_layer=load_case_name)
                         for layer_name in layer_names]

        for sof_id, sof_res in load_case_results.items():
            centroid = cdb_dict["brics"][sof_id].get("centroid")
            if not centroid: return

            # generate result geometry
            stresses, vectors = rm.get_principal_stresses(sof_res)
            for σ, vec, name, layer in zip(stresses, vectors, ("VσI", "VσII", "VσIII"), stress_layers):
                res = abs(σ)
                if res < 1E-3: continue  # cutoff value for small results
                vec_offset = [(res/200) * rm.get_unit_scale() * v for v in vec]
                sp = rg.Point3d(*[c - v for c, v in zip(centroid, vec_offset)])
                ep = rg.Point3d(*[c + v for c, v in zip(centroid, vec_offset)])
                obj = rg.Line(sp, ep)

                att = sc.doc.CreateDefaultAttributes()
                att.Name = name + str(sof_id)
                att.LayerIndex = layer.Index
                att.ObjectColor = color.Red if σ > 0 else color.DeepSkyBlue
                att.ColorSource = rc.DocObjects.ObjectColorSource.ColorFromObject
                att.SetUserString("stress", str(round(σ, 4)))

                # add result object to document
                guid = sc.doc.Objects.AddLine(obj, att)
                if not guid: print("SOFiSTiK result object {0} could not be added.".format(att.Name))


sof_type = namedtuple("sof_geo", ["name_prefix", "layer_name", "layer_color", "generate", "add", "ignore_attributes"])
sof_geometry_types = {
    "nodes": sof_type("N",  "SOF_Nodes",        color.DeepPink,     generate_node,     sc.doc.Objects.AddPoint,    ("xyz",)),
    "beams": sof_type("B",  "SOF_Beams",        color.MidnightBlue, generate_beam,     sc.doc.Objects.AddLine,     ("nodes", "length")),
    "trusses": sof_type("B","SOF_Trusses",      color.Turquoise,    generate_truss,    sc.doc.Objects.AddLine,     ("nodes", "length")),
    "cables": sof_type("C", "SOF_Cables",       color.Crimson,      generate_cable,    sc.doc.Objects.AddLine,     ("nodes", "length")),
    "springs": sof_type("C","SOF_Springs",      color.LimeGreen,    generate_spring,   sc.doc.Objects.AddLine,     ("nodes",)),
    "quads": sof_type("Q",  "SOF_Quads",        color.LightBlue,    generate_quad,     sc.doc.Objects.AddBrep,     ("nodes", "area")),
    "brics": sof_type("V",  "SOF_Brics",        color.Orange,       generate_bric,     sc.doc.Objects.AddMesh,     ("nodes", "volume")),
                    }

if __name__=="__main__":
    pass