# -*- coding: utf-8 -*-
import Rhino as rc
import Rhino.Input as ri
import rhino_misc as rm

def scale_results():
    """Scale all SOFiSTiK result objects in Rhino file0.5."""
    res_scale = 1.0
    command_result, res_scale = ri.RhinoGet.GetNumber("Input scale factor for results.", False, res_scale)
    if command_result != rc.Commands.Result.Success: return
    if res_scale == 1.0: return
    rm.scale_centric("SOF_Results", res_scale)

if __name__ == "__main__":
    scale_results()