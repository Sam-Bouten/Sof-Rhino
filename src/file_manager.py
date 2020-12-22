# -*- coding: utf-8 -*-
import os
import json


__all__ = [
    "write_to_json",
    "read_from_json"
    ]


def write_to_json(cdb_dict, json_path):
    """Write cdb dictionary to JSON file.

    Attributes
    ----------
    cdb_dict : dictionary
        All SOFiSTiK cdb data serialized in a dictionary.
    json_path : string
        Full path to JSON file.
    """
    with open(json_path, "w") as out_file:
        json.dump(cdb_dict, out_file, indent=4)


def read_from_json(json_path):
    """Read from JSON file format and return as dictionary.

    Attributes
    ----------
    json_path : string
        Full path to JSON file.

    Returns
    -------
    cdb_dict : dictionary
        Serialized dictionary from JSON data.
    """
    if not json_path.endswith(".json"):
        raise ValueError("Input file is not of valid JSON format")
    with open(json_path) as in_file:
        data = json.load(in_file, parse_int=int)
    data = _convert_dict_integers(data)
    return data


def _convert_dict_integers(json_data):
    """Convert dictionary key data to integer data if possible."""
    correctedDict = {}

    for key, value in json_data.items():
        if isinstance(value, list):
            value = ([_convert_dict_integers(item) if isinstance(item, dict)
                    else item for item in value])
        elif isinstance(value, dict):
            value = _convert_dict_integers(value)
        try:
            key = int(key)
        except Exception as ex:
            pass
        correctedDict[key] = value
    return correctedDict



if __name__ == "__main__":
    pass