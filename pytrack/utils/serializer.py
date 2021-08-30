"""
This program and the accompanying materials are made available under the terms of the
Eclipse Public License v2.0 which accompanies this distribution, and is available at
https://www.eclipse.org/legal/epl-v20.html
SPDX-License-Identifier: EPL-2.0

Copyright Contributors to the Zincware Project.

Description: List of functions that are applied to serialize and deserialize Python Objects

Notes
-----
    These functions can be used for e.g., small numpy arrays.
    The content will be converted to json serializable data.
    Converting e.g., large numpy arrays can cause major slow downs and is not recommended!
    Please consider using DVC.outs() and save them in a binary file format.

"""
from pathlib import Path
import numpy as np


def conv_path_to_str(value):
    """Convert Path to str"""
    if isinstance(value, Path):
        value = value.as_posix()
    return value


def conv_numpy_to_dict(value):
    """Convert numpy to a list, marked by a dictionary"""
    if isinstance(value, np.ndarray):
        value = {'np': value.tolist()}
    return value


def conv_dict_to_numpy(value):
    """Convert marked dictionary to a numpy array"""
    if isinstance(value, dict):
        if len(value) == 1 and 'np' in value:
            value = np.array(value['np'])
    return value


def serializer(data):
    """Serialize data so it can be stored in a json file"""
    data = conv_path_to_str(data)
    data = conv_numpy_to_dict(data)

    if isinstance(data, list):
        return [serializer(x) for x in data]
    elif isinstance(data, dict):
        return {key: serializer(val) for key, val in data.items()}
    else:
        return data


def deserializer(data):
    """Deserialize data from the json file back to python objects"""
    data = conv_dict_to_numpy(data)
    if isinstance(data, list):
        return [deserializer(x) for x in data]
    elif isinstance(data, dict):
        return {key: deserializer(val) for key, val in data.items()}
    else:
        return data
