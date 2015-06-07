# -*- coding: utf-8 -*-

from __future__ import division

import subprocess
import numpy as np

from enum import Enum

__author__ = 'Christoph Statz'


def get_dtype_size_owner(data, owner, repl_owner):

    dtype = None
    size = None

    if isinstance(data, list):
        tmp = type(data[0]).__name__
        if tmp.startswith('int'):
            dtype = 'I'
        if tmp.startswith('float'):
            dtype = 'D'

        size = len(data)
        owner = repl_owner

    elif isinstance(data, np.ndarray):
        tmp = data.dtype.name
        if tmp.startswith('int'):
            dtype='I'
        elif tmp == 'float64':
            dtype='D'
        elif tmp == 'float32':
            dtype='F'
        size = data.size

    return dtype, size, owner


def get_visit_dirs():

    lib_path = None
    visit_home = None

    try:
        p = subprocess.Popen(['visit', '-env'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        raise OSError("Path to visit executable is not set!")

    out = p.communicate()[0].split('\n')

    for line in out:
        tmp = line.strip().split('=')
        if tmp[0].startswith("LIBPATH"):
            lib_path = tmp[1].strip()
        if tmp[0].startswith("VISITHOME"):
            visit_home = tmp[1].strip()

    return lib_path, visit_home


class S(Enum):
    """
    VisItDetectInput return codes as described in
    http://www.visitusers.org/index.php?title=Simulation_Control_Interface#VisItDetectInput
    """
    FTAC = -5
    NDBB = -4
    SSNS = -3
    ERROR = -2
    EINTR = -1
    OKAY = 0
    LSI = 1
    ESI = 2
    CSI = 3


class P(Enum):
    PROCESS = 0
    SUCCESS = 1
    FAILURE = 2
