# -*- coding: utf-8 -*-
#TODO add coupling elements
#TODO translate bitcode for node support conditions
#TODO read beam cross sections


import os
import glob
import platform
from ctypes import *
from collections import namedtuple

from sof_data_access import *


__all__ = ["SofReader"]


def read_sof_dtype(record_identifier, sof_dtype, sof_keys, position=None):
    """Decorator to read datatype records from SOFiSTiK cdb.

    Parameters
    ----------
    record_identifier : string
        Name for record in serialized cdb dictionary.

    sof_dtype : class
        SOFiSTiK cdb access record datatype class.

    sof_keys : tuple
        Keys identifying the record datatype.
    
    position: int
        Position of current record.
    """
    def read_dtype(store_record):

        def single_record(cdb):
            dtype_dict = {}

            # validate record keys
            if not cdb._validate_cdb_keys(sof_keys):
                return

            # set up error, position, and record length counters
            error_flag = c_int(0)
            pos = c_int(position if position != None else 1)
            record_len = c_int(sizeof(sof_dtype))

            # loop over elements in record
            while error_flag.value < 2:
                error_flag.value = cdb.get_cdb(cdb.index, sof_keys[0], sof_keys[1],
                                            byref(sof_dtype), byref(record_len), pos)
                record_data = store_record(cdb)
                pos.value = 1
                record_len.value = sizeof(sof_dtype)
                if record_data: dtype_dict.update(record_data)

            cdb.data[record_identifier] = dtype_dict


        def multiple_records(cdb):
            dtype_dict = {}

            for rec_kwl in range(9999):
                # validate record keys
                if not cdb._validate_cdb_keys( (sof_keys[0], rec_kwl), silent=True):
                    continue

                # set up error, record length counters and record dict
                error_flag = c_int(0)
                record_len = c_int(sizeof(sof_dtype))
                record_dict = {}

                # loop over elements in record
                while error_flag.value < 2:
                    error_flag.value = cdb.get_cdb(cdb.index, sof_keys[0], rec_kwl,
                                        byref(sof_dtype), byref(record_len), 1)
                    record_data = store_record(cdb)
                    record_len.value = sizeof(sof_dtype)
                    if record_data: record_dict.update(record_data)

                # store current partial record
                dtype_dict[rec_kwl] = record_dict
            
            # store all partial records
            cdb.data[record_identifier] = dtype_dict


        if sof_keys[1] != None: return single_record
        else: return multiple_records

    return read_dtype


class SofReader(object):
    """ Read SOFiSTiK database.

    Constructor Parameters
    ----------------------
    cdb : string
        Path to SOFiSTiK database to read out.

    sof_path : string (optional)
        Path to installation directory of desired SOFiSTiK version.
        If no path is provided, the default SOFiSTiK installation path is looked up.

    dll_name : string (optional)
        File name of SOFiSTiK C library containing database access functions.
    """

    def __init__(self, cdb, sof_path=None, dll_name=None):
        self.cdb = cdb
        self.sof_path = sof_path
        self.dll_name = dll_name
        self.index = c_int()
        self.status = c_int()
        self.data = {}

        self._fix_flags = [ (1024,   "", ""),               # warping
                             (512,   "", ""),               # relative rotation
                             (256,   "", ""),               # relative rotation
                             (128,   "", ""),               # split continuous beams
                              (64,   "", "PxPyPzMxMyMz"),   # free rotation and translation
                              (32, "Mz", ""),               # rotation over local Z
                              (16, "My", ""),               # rotation over local Y
                               (8, "Mx", ""),               # rotation over local X
                               (4, "Pz", ""),               # translation along local Z
                               (2, "Py", ""),               # translation along local Y
                               (1, "Px", "")                # translation along local X
                          ]
    

    def __enter__(self):
        """Open and validate cdb, get access functionalities from external dll."""
        # validate file type
        if not self._validate_file():
            raise ValueError("Database file does not exist or is not of valid .cdb type.")

        # open cdb and store its access functions
        print("Reading SOFiSTiK database from:\n{0}".format(self.cdb))
        self._get_cdb_functions()

        # validate cdb and status
        if not self._validate_cdb():
            raise ValueError("SOFiSTiK cdb is corrupted.")
        self.status.value = self.get_status(self.index.value)
        self._validate_cdb_status()
        
        return self


    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Close cdb and validate status."""
        self.close(0)
        self._validate_cdb_status()


    def _get_cdb_functions(self):
        """Open cdb and store its access functions."""
        # add dll files to local environment and get cdb access function library
        install_path = self.sof_path or SofReader._get_sof_version()
        bit_width = SofReader._get_bit_width()
        func_dll = self.dll_name or SofReader._get_dll_path(install_path)
        sof_dll = cdll.LoadLibrary(func_dll)

        # open cdb
        cdb_path_encoded =  bytes(str(self.cdb).encode("utf-8"))
        self.index.value = sof_dll.sof_cdb_init(cdb_path_encoded, 99)

        # store library access functions
        self.get_status = sof_dll.sof_cdb_status
        self.get_cdb = sof_dll.sof_cdb_get
        self.keys_exist = sof_dll.sof_cdb_kexist
        self.close = sof_dll.sof_cdb_close


    @staticmethod
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
        sof_dir = os.path.join(sof_dir, sof_year, "SOFiSTiK {0}".format(sof_year))
        return sof_dir


    @staticmethod
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


    @staticmethod
    def _get_dll_path(sof_path):
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
        dll_path = [f for f in glob.glob(os.path.join(sof_path, "cdb_w_*.dll"))][0] #.split("\\")[-1]
        return dll_path


    def _validate_file(self):
        """Validate if file is an existing (.cdb) SOFiSTiK database file.

        Returns
        -------
        is_valid_file : Boolean
        """
        if not os.path.exists(self.cdb):
            print("ERROR: input file does not exist")
            return False
        if not self.cdb.endswith(".cdb"):
            print("ERROR: input file is not a SOFiSTiK database (.cdb)")
            return False
        return True


    def _validate_cdb(self):
        """Validate cdb.

        Returns
        -------
        is_valid_cdb : Boolean
        """
        if self.index.value < 0:
            print("ERROR: cdb index: " + str(self.index.value) + " - see clib1.h for CDB error codes")
            return False
        elif self.index.value == 0:
            print("ERROR: cdb index: " + str(0) + " - invalid database")
            return False
        else:
            print("CDB  index: " + str(self.index.value) + " - database opened")
            return True


    def _validate_cdb_status(self):
        """Validate status of cdb.

        Parameters
        ----------
        cdb_status : integer
            cdb status identifier.
        """
        status = self.get_status(self.index)
        if status == 0:
            print("CDB status: 0 - database closed")
        else:
            print("CDB status: {}".format(status))


    def _validate_cdb_keys(self, sof_keypair, silent=False):
        """Validate if cdb record key entries exist and contain data.

        Attributes
        ----------
        sof_keypair : iterable(integer)
            List of integer keys identifying cdb record type to be accessed.

        silent: Boolean
            if True, not output will be printed if keys don't exist.

        Returns
        -------
        is_valid_keypair : Boolean
        """
        if self.keys_exist(*sof_keypair) == 0:
            if not silent: print("Record {0:>4} {1:>4} does not exist".format(sof_keypair[0], sof_keypair[1]))
            return False
        elif self.keys_exist(*sof_keypair) == 1:
            if not silent: print("Record {0:>4} {1:>4} exists, but does not contain data".format(sof_keypair[0], sof_keypair[1]))
            return False
        elif self.keys_exist(*sof_keypair) == 2:
            print("Record {0:>4} {1:>4} read".format(sof_keypair[0], sof_keypair[1]))
            return True


    @read_sof_dtype("system", csyst, (10, 0))
    def read_system(self):
        return {"gdiv" : csyst.m_igdiv}


    @read_sof_dtype("nodes", cnode, (20, 0))
    def read_nodes(self):
        if cnode.m_nr <= 0: return None
        return {cnode.m_nr : {"xyz" : list(cnode.m_xyz),
                              "fix" : self._decode_node_fix(cnode.m_kfix)
                             }}


    @read_sof_dtype("beams", cbeam, (100, 0))
    def read_beams(self):
        if cbeam.m_nr <= 0: return None
        return {cbeam.m_nr : {"group"  : self._get_group(cbeam.m_nr),
                              "nodes"  : list(cbeam.m_node),
                              "length" : cbeam.m_dl,
                              "x_start": [e[0] for e in cbeam.m_ex],
                              "x_end"  : [e[1] for e in cbeam.m_ex]
                             }}


    @read_sof_dtype("beam_sections", cbeam_sct, (100, 0), 1)
    def read_beam_sections(self):
        if cbeam_sct.m_id <= 0: return None
        return {cbeam_sct.m_id : {"section"  : cbeam_sct.m_nq,
                                  "bitcodes" : cbeam_sct.m_ityp,
                                  "hinges"   : cbeam_sct.m_itp2
                                  }}


    @read_sof_dtype("trusses", ctrus, (150, 0))
    def read_trusses(self):
        if ctrus.m_nr <= 0: return None
        return {ctrus.m_nr : {"group"  : self._get_group(ctrus.m_nr),
                              "nodes"  : list(ctrus.m_node),
                              "length" : ctrus.m_dl,
                              "section": ctrus.m_nrq,
                              "pre"    : ctrus.m_pre,
                              "ulti"   : ctrus.m_riss,
                              "yield"  : ctrus.m_flie
                             }}


    @read_sof_dtype("cables", ccabl, (160, 0))
    def read_cables(self):
        if ccabl.m_nr <= 0: return None
        return {ccabl.m_nr : {"group"  : self._get_group(ccabl.m_nr),
                              "nodes"  : list(ccabl.m_node),
                              "length" : ccabl.m_dl,
                              "section": ccabl.m_nrq,
                              "pre"    : ccabl.m_pre,
                              "ulti"   : ccabl.m_riss,
                              "yield"  : ccabl.m_flie
                             }}


    @read_sof_dtype("springs", cspri, (170, 0))
    def read_springs(self):
        if cspri.m_nr <= 0: return None
        return {cspri.m_nr : {"group"  : self._get_group(cspri.m_nr),
                              "nodes"  : list(cspri.m_node),
                              "normal" : list(cspri.m_t),
                              "k_long" : cspri.m_cp,
                              "k_trvs" : cspri.m_cq,
                              "k_rot"  : cspri.m_cm
                             }}


    @read_sof_dtype("quads", cquad, (200, 0))
    def read_quads(self):
        if cquad.m_nr <= 0: return None
        det_multiplier = 4
        return {cquad.m_nr : {"group"  : self._get_group(cquad.m_nr),
                              "nodes"  : list(cquad.m_node),
                              "type"   : cquad.m_nra,
                              "thick"  : cquad.m_thick[0],
                              "mat"    : cquad.m_mat,
                              "area"   : cquad.m_det[0] * det_multiplier
                             }}


    @read_sof_dtype("brics", cbric, (300, 0))
    def read_brics(self):
        if cbric.m_nr <= 0: return None
        # get volume multiplier for Jacobian determinant
        if (cbric.m_node[-1] == cbric.m_node[-2]): # tetrahedron
            det_factor = 4 / 3
        else: # hexahedron
            det_factor = 8
        return {cbric.m_nr : {"group"  : self._get_group(cbric.m_nr),
                              "nodes"  : list(cbric.m_node),
                              "type"   : cbric.m_nra,
                              "mat"    : cbric.m_mat,
                              "volume" : cbric.m_det[0] * det_factor
                             }}


    @read_sof_dtype("bric_stresses", cbric_str, (310, None))
    def read_bric_stresses(self):
        if cbric_str.m_nr <= 0: return None
        scale = 0.001
        return {cbric_str.m_nr : {"sigx"  : cbric_str.m_sigx * scale,
                                  "sigy"  : cbric_str.m_sigy * scale,
                                  "sigz"  : cbric_str.m_sigy * scale,
                                  "tauxy" : cbric_str.m_tvxy * scale,
                                  "tauxz" : cbric_str.m_tvxz * scale,
                                  "tauyz" : cbric_str.m_tvyz * scale
                                 }}


    def _get_group(self, elem_nr):
        system_data =  self.data.get("system")
        if not system_data: return 0
        gdiv = system_data.get("gdiv")
        return int(elem_nr/gdiv)


    @property
    def fix_flags(self):
        return self._fix_flags

    def _decode_node_fix(self, bitcode):
        value = " "
        for fix in self.fix_flags:
            temp_bc = bitcode - fix[0] 
            if temp_bc >= 0:
                bitcode = temp_bc
                value = str.replace(value, fix[1], fix[2])
        return value


    def read_geometry(self):
        """Read out all geometry data in cdb.
        Collection method.
        """
        self.read_system()
        self.read_nodes()
        self.read_beams()
        # self.read_beam_sections()
        self.read_trusses()
        self.read_cables()
        self.read_springs()
        self.read_quads()
        self.read_brics()



if __name__ == "__main__":
    pass