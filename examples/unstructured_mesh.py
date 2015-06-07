#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

import numpy as np
from visitor import VisitInstrumentation, VISIT_CELL_BEAM, VISIT_MESHTYPE_UNSTRUCTURED


def dp(*args, **kwargs):

    x = np.linspace(-5., 4., 10)
    y = np.linspace(0., 10., x.size)
    z = np.linspace(-20., -10., x.size)
    c = np.zeros(3*(x.size-1), dtype=np.int32)

    for i in range(c.size//3):
        c[3*i] = VISIT_CELL_BEAM
        c[3*i+1] = i
        c[3*i+2] = i+1

    return x, y, c, c.size, z


def main():

    name = 'unstructure_mesh_example'
    prefix = '.'
    description = 'This example demonstrates the instrumentation of a simulation based on an unstructured mesh'

    v = VisitInstrumentation(name, description, prefix=prefix)

    mesh_name = 'example_u3'
    mesh_type = VISIT_MESHTYPE_UNSTRUCTURED
    v.register_mesh(mesh_name, dp, mesh_type, 3, xunits="cm", yunits="cm", xlabel="a", ylabel="b", zunits="cm", zlabel="c")
    v.run()


if __name__ == "__main__":
    main()
