#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

import numpy as np
import os
from visitor import VisitInstrumentation, VISIT_MESHTYPE_RECTILINEAR, VISIT_VARTYPE_SCALAR, VISIT_VARCENTERING_NODE, VISIT_VARCENTERING_ZONE

__author__ = 'Christoph Statz'


data = 0.5 * np.ones(179*256*256, dtype=np.float64)
z = 0.010 * np.arange(179) - 179 * 0.01
y = 0.001875 * np.arange(256) - 256 * 0.001875
x = 0.001875 * np.arange(256) - 256 * 0.001875

def mesh_dp(*args, **kwargs):
    return x, y, z

def data_dp(*args, **kwargs):
    return data

def main():

    name = 'variable_example'
    prefix = '.'
    description = 'This example demonstrates the instrumentation of a simulation based on a rectilinear mesh'

    v = VisitInstrumentation(name, description, prefix=prefix)

    mesh_name = 'example_r3'
    mesh_type = VISIT_MESHTYPE_RECTILINEAR
    v.register_mesh(mesh_name, mesh_dp, mesh_type, 3, xunits="m", yunits="m", xlabel="a", ylabel="b", zunits="m", zlabel="c")
    v.register_variable('d', mesh_name, data_dp, VISIT_VARTYPE_SCALAR, VISIT_VARCENTERING_NODE, units='mat')
    v.run()


if __name__ == "__main__":
    main()
