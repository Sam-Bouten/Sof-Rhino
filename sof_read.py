#TODO add function to get element groups
#TODO add coupling elements
#TODO translate bitcode for node support conditions
#TODO add more information to beam/cable/truss elements (section numbers etc)

# -*- coding: utf-8 -*-
import os
import glob
import platform
from ctypes import *
from collections import namedtuple
from sof_data_access import *


__all__ = [
    "read_cdb",
    "read_nodes",
    "read_beams",
    "read_trusses",
    "read_cables",
    "read_springs",
    "read_quads",
    "read_brics",
    "read_geometry"
    ]


def read_cdb(cdb_path, read_records=tuple(), sof_path=None, cdb_dll=None):
    """ Read SOFiSTiK database.

    Parameters
    ----------
    cdb_path : string
        Path to SOFiSTiK database to read out.
    read_records : iterable(callable)
        Iterable of compatible access functions to be called on reading the cdb.
    sof_path : string (=None)
        Path to installation directory of desired SOFiSTiK version.
        If no path is provided, the default SOFiSTiK installation path is looked up.
    cdb_dll : string (=None)
        Name of SOFiSTiK C library containing database access functions.
    
    Returns
    -------
    cdb_dict : dictionary
        All cdb data serialized in a dictionary.
    """
    # validate input file
    if not _validate_file(cdb_path): return
    print("Reading SOFiSTiK database from:\n{0}".format(cdb_path))

    # open cdb and store its access functions 
    cdb = _get_cdb_functions(cdb_path, sof_path, cdb_dll)

    # validate cdb and status
    status = c_int()
    status.value = cdb.status(cdb.index.value)
    if not _validate_cdb(cdb.index.value): return
    _get_cdb_status(status.value)

    # serialize cdb dictionary
    cdb_dict = {}
    for read_func in read_records:
        cdb_dict.update(read_func(cdb))

    # close cdb and validate status
    cdb.close(0)
    _get_cdb_status(cdb.status(cdb.index))

    return cdb_dict


def _get_cdb_functions(cdb_path, sof_path, dll_name):
    """Open cdb and store its access functions.

    Parameters
    ----------
    cdb_path : string
        Path to SOFiSTiK database to read out.
    sof_path : string
        Path to installation directory of desired SOFiSTiK version.
        If no path is provided, the default SOFiSTiK installation path is looked up.
    cdb_dll : string
        Name of SOFiSTiK C library containing database access functions.
    
    Returns
    -------
    cdb : namedtuple
        Tuple containing database and its access functions.
    """
    # add dll files to local environment and get cdb access function library
    install_path = sof_path if sof_path else _get_sof_version()
    bit_width = _get_bit_width()
    os.environ["Path"] += install_path + "\\interfaces\\{0}bit".format(bit_width) + ";" + install_path
    func_dll = dll_name if dll_name else _get_dll_name(install_path)
    sof_dll = cdll.LoadLibrary(func_dll)

    # open cdb
    index = c_int()
    cdb_path_encoded =  bytes(str(cdb_path).encode("utf-8"))
    index.value = sof_dll.sof_cdb_init(cdb_path_encoded, 99)

    # store library access functions
    cdb_access = namedtuple("access", ["index", "status", "get_cdb", "keys_exist", "close"])
    cdb = cdb_access(index, sof_dll.sof_cdb_status, sof_dll.sof_cdb_get,
                     sof_dll.sof_cdb_kexist, sof_dll.sof_cdb_close)
    
    return cdb


def _get_sof_version():
    """Look up directory of installed latest SOFiSTiK version.

    Returns
    -------
    sof_dir : string
        Path to the SOFiSTiK latest version installation directory.
    """
    drive = os.path.splitdrive(os.getcwd())[0]
    sof_dir = glob.glob(drive + "/*/SOFiSTiK/")[0]
    sof_year = max([f for f in os.listdir(sof_dir) if f.isdigit()])
    sof_dir = sof_dir + sof_year + "\\" + "SOFiSTiK {0}".format(sof_year)
    return sof_dir


def _get_bit_width():
    """Get system architecture bit width.
    
    Returns
    -------
    bit_width : integer
        System architecture bit width.
    """
    sof_platform = str(platform.architecture())
    bit_width = 64 if sof_platform.find("32Bit") < 0 else 32
    return bit_width


def _get_dll_name(sof_path):
    """Lookup database access library name in SOFiSTiK install directory.
    Parameters
    ----------
    sof_path: string
        Path to installation directory of desired SOFiSTiK version.
    Returns
    -------
    dll_name : string
        Path to the SOFiSTiK installation directory.
    """
    dll_name = [f for f in glob.glob(sof_path + "\\cdb_w_*.dll")][0].split("\\")[-1]
    return dll_name


def _validate_file(cdb_path):
    """Validate if file is an existing (.cdb) SOFiSTiK database file.

    Parameters
    ----------
    cdb_path : string
        Path to SOFiSTiK database to read out.

    Returns
    -------
    is_valid_cdb : Boolean
    """
    if not os.path.exists(cdb_path):
        print("ERROR: input file does not exist")
        return False
    if not cdb_path.endswith(".cdb"):
        print("ERROR: input file is not a SOFiSTiK database (.cdb)")
        return False
    return True


def _validate_cdb(cdb_index):
    """Validate if SOFiSTiK cdb is valid.

    Parameters
    ----------
    cdb_index : integer
        cdb global error identifier.
    
    Returns
    -------
    is_valid_cdb : Boolean
    """
    if cdb_index < 0:
        print("ERROR: cdb index: " + str(cdb_index) + " - see clib1.h for CDB error codes")
        return False
    elif cdb_index == 0:
        print("ERROR: cdb index: " + str(0) + " - invalid database")
        return False
    else:
        print("CDB  index: " + str(cdb_index) + " - database opened")
        return True


def _validate_cdb_keys(sof_keys, validation_func):
    """ Validate if cdb record key entries exist and contain data.

    Attributes
    ----------
    sof_keys : iterable(integer)
        List of integer keys identifying cdb record type to be accessed.
    validation_func : callable
        Callback function to validate keys.

    Returns
    -------
    is_valid_keyset : Boolean
    """
    if validation_func(*sof_keys) == 0:
        print("Key {0:>3} {1:>2} does not exist".format(sof_keys[0], sof_keys[1]))
        return False
    elif validation_func(*sof_keys) == 1:
        print("Key {0:>3} {1:>2} exists, but does not contain data".format(sof_keys[0], sof_keys[1]))
        return False
    elif validation_func(*sof_keys) == 2:
        print("Key {0:>3} {1:>2} read".format(sof_keys[0], sof_keys[1]))
        return True


def _get_cdb_status(cdb_status):
    """Validate status of cdb.

    Parameters
    ----------
    cdb_status : integer
        cdb status identifier.
    """
    if cdb_status == 0:
        print("CDB status: 0 - database closed")
    else:
        print("CDB status: {}".format(cdb_status))


def read_sof_dtype(record_identifier, sof_dtype, sof_keys):
    """Decorator to read datatype record from SOFiSTiK cdb.

    Parameters
    ----------
    record_identifier : string
        Name for record in serialized cdb dictionary.
    sof_dtype : class
        SOFiSTiK cdb access record datatype class.
    sof_keys : tuple
        Keys identifying the record datatype.

    Returns
    -------
    dtype_dict : dictionary
        Serialized cdb data per record type key.
    """
    def read_dtype(read_record):
        def wrapper(cdb):
            dtype_dict = {}

            # validate record keys
            if not _validate_cdb_keys(sof_keys, cdb.keys_exist):
                return {record_identifier: dtype_dict}

            # set up error and length counters
            error_flag = c_int(0)
            record_len = c_int(sizeof(sof_dtype))

            # loop over elements in record
            while error_flag.value == 0:
                error_flag.value = cdb.get_cdb(cdb.index, sof_keys[0], sof_keys[1],
                                               byref(sof_dtype), byref(record_len), 1)
                record_data = read_record(cdb)
                record_len = c_int(sizeof(sof_dtype))
                if not record_data: continue
                dtype_dict.update(record_data)

            return {record_identifier: dtype_dict}
        return wrapper
    return read_dtype


@read_sof_dtype("nodes", cnode, (20, 0))
def read_nodes(cdb):
    #TODO parse bitcodes of DoF supports  https://www.sofistik.de/documentation/2020/en/cdb_interfaces/vba/examples/vba_example3.html
    if cnode.m_nr <= 0: return None
    return {cnode.m_nr : {"xyz" : list(cnode.m_xyz),
                          "dof" : cnode.m_kfix
                          }}


@read_sof_dtype("beams", cbeam, (100, 0))
def read_beams(cdb):
    #TODO read other records to get beam properties
    if cbeam.m_nr <= 0: return None
    return {cbeam.m_nr : {"nodes"  : list(cbeam.m_node),
                          "length" : cbeam.m_dl
                          }}


@read_sof_dtype("trusses", ctrus, (150, 0))
def read_trusses(cdb):
    if ctrus.m_nr <= 0: return None
    return {ctrus.m_nr : {"nodes"  : list(ctrus.m_node),
                          "length" : ctrus.m_dl,
                          "section": ctrus.m_nrq,
                          "pre"    : ctrus.m_pre,
                          "ulti"   : ctrus.m_riss,
                          "yield"  : ctrus.m_flie
                          }}


@read_sof_dtype("cables", ccabl, (160, 0))
def read_cables(cdb):
    if ccabl.m_nr <= 0: return None
    return {ccabl.m_nr : {"nodes"  : list(ccabl.m_node),
                          "length" : ccabl.m_dl,
                          "section": ccabl.m_nrq,
                          "pre"    : ccabl.m_pre,
                          "ulti"   : ccabl.m_riss,
                          "yield"  : ccabl.m_flie
                          }}


@read_sof_dtype("springs", cspri, (170, 0))
def read_springs(cdb):
    if cspri.m_nr <= 0: return None
    return {cspri.m_nr : {"nodes"  : list(cspri.m_node),
                          "normal" : list(cspri.m_t),
                          "k_long" : cspri.m_cp,
                          "k_trvs" : cspri.m_cq,
                          "k_rot"  : cspri.m_cm
                          }}


@read_sof_dtype("quads", cquad, (200, 0))
def read_quads(cdb):
    if cquad.m_nr <= 0: return None
    det_multiplier = 4
    return {cquad.m_nr : {"nodes"  : list(cquad.m_node),
                          "type"   : cquad.m_nra,
                          "thick"  : cquad.m_thick[0],
                          "mat"    : cquad.m_mat,
                          "area"   : cquad.m_det[0] * det_multiplier
                          }}


@read_sof_dtype("brics", cbric, (300, 0))
def read_brics(cdb):
    if cbric.m_nr <= 0: return None
    # multiplier for Jacobian determinant depending on tetrahedron or hexahedron
    det_multiplier = ((4/3) if cbric.m_node[-1] == cbric.m_node[-2] else 8)
    return {cbric.m_nr : {"nodes"  : list(cbric.m_node),
                          "type"   : cbric.m_nra,
                          "mat"    : cbric.m_mat,
                          "volume" : cbric.m_det[0] * det_multiplier
                          }}


def read_geometry():
    """Return iterable of all geometric read record functions."""
    return [read_nodes, read_beams, read_trusses, read_cables, read_springs, read_quads, read_brics]



if __name__ == "__main__":
    pass