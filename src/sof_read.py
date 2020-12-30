#TODO fix pylint makrup on ctypes
#TODO add function to get element groups
#TODO add coupling elements
#TODO translate bitcode for node support conditions
#TODO add more data to beam/cable/truss elements (section numbers etc)

# -*- coding: utf-8 -*-
import os
import glob
import platform
from ctypes import *
from collections import namedtuple
from sof_data_access import *


__all__ = ["SofReader"]


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
    """
    def read_dtype(read_record):
        def wrapper(cdb):
            dtype_dict = {}

            # validate record keys
            if not cdb._validate_cdb_keys(sof_keys):
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

            cdb.data[record_identifier] = dtype_dict
        
        return wrapper
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


    def _validate_cdb_keys(self, sof_keypair):
        """Validate if cdb record key entries exist and contain data.

        Attributes
        ----------
        sof_keypair : iterable(integer)
            List of integer keys identifying cdb record type to be accessed.

        Returns
        -------
        is_valid_keypair : Boolean
        """
        if self.keys_exist(*sof_keypair) == 0:
            print("Key {0:>3} {1:>2} does not exist".format(sof_keypair[0], sof_keypair[1]))
            return False
        elif self.keys_exist(*sof_keypair) == 1:
            print("Key {0:>3} {1:>2} exists, but does not contain data".format(sof_keypair[0], sof_keypair[1]))
            return False
        elif self.keys_exist(*sof_keypair) == 2:
            print("Key {0:>3} {1:>2} read".format(sof_keypair[0], sof_keypair[1]))
            return True
    

    @read_sof_dtype("nodes", cnode, (20, 0))
    def read_nodes(self):
        #TODO parse bitcodes of DoF supports:
        # https://www.sofistik.de/documentation/2020/en/cdb_interfaces/vba/examples/vba_example3.html
        if cnode.m_nr <= 0: return None
        return {cnode.m_nr : {"xyz" : list(cnode.m_xyz),
                              "dof" : cnode.m_kfix
                             }}


    @read_sof_dtype("beams", cbeam, (100, 0))
    def read_beams(self):
        #TODO read other records to get beam properties
        if cbeam.m_nr <= 0: return None
        return {cbeam.m_nr : {"nodes"  : list(cbeam.m_node),
                              "length" : cbeam.m_dl
                             }}


    @read_sof_dtype("trusses", ctrus, (150, 0))
    def read_trusses(self):
        if ctrus.m_nr <= 0: return None
        return {ctrus.m_nr : {"nodes"  : list(ctrus.m_node),
                              "length" : ctrus.m_dl,
                              "section": ctrus.m_nrq,
                              "pre"    : ctrus.m_pre,
                              "ulti"   : ctrus.m_riss,
                              "yield"  : ctrus.m_flie
                             }}


    @read_sof_dtype("cables", ccabl, (160, 0))
    def read_cables(self):
        if ccabl.m_nr <= 0: return None
        return {ccabl.m_nr : {"nodes"  : list(ccabl.m_node),
                              "length" : ccabl.m_dl,
                              "section": ccabl.m_nrq,
                              "pre"    : ccabl.m_pre,
                              "ulti"   : ccabl.m_riss,
                              "yield"  : ccabl.m_flie
                             }}


    @read_sof_dtype("springs", cspri, (170, 0))
    def read_springs(self):
        if cspri.m_nr <= 0: return None
        return {cspri.m_nr : {"nodes"  : list(cspri.m_node),
                              "normal" : list(cspri.m_t),
                              "k_long" : cspri.m_cp,
                              "k_trvs" : cspri.m_cq,
                              "k_rot"  : cspri.m_cm
                             }}


    @read_sof_dtype("quads", cquad, (200, 0))
    def read_quads(self):
        if cquad.m_nr <= 0: return None
        det_multiplier = 4
        return {cquad.m_nr : {"nodes"  : list(cquad.m_node),
                              "type"   : cquad.m_nra,
                              "thick"  : cquad.m_thick[0],
                              "mat"    : cquad.m_mat,
                              "area"   : cquad.m_det[0] * det_multiplier
                             }}


    @read_sof_dtype("brics", cbric, (300, 0))
    def read_brics(self):
        if cbric.m_nr <= 0: return None
        # multiplier for Jacobian determinant
        if (cbric.m_node[-1] == cbric.m_node[-2]): # tetrahedron
            det_multiplier = 4 / 3
        else: # hexahedron
            det_multiplier = 8
        return {cbric.m_nr : {"nodes"  : list(cbric.m_node),
                              "type"   : cbric.m_nra,
                              "mat"    : cbric.m_mat,
                              "volume" : cbric.m_det[0] * det_multiplier
                             }}


    def read_geometry(self):
        """Read out all geometry data in cdb.
        Collection method.
        """
        self.read_nodes()
        self.read_beams()
        self.read_trusses()
        self.read_cables()
        self.read_springs()
        self.read_quads()
        self.read_brics()



if __name__ == "__main__":
    pass