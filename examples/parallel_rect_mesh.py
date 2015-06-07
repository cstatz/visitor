#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

import numpy as np
from visitor import ParallelVisitInstrumentation, VISIT_MESHTYPE_RECTILINEAR
from mpi4py import MPI


comm_world = MPI.COMM_WORLD
comm_rank = comm_world.Get_rank()
comm_size = comm_world.Get_size()


__author__ = 'Christoph Statz'


def dp(*args, **kwargs):

    x = np.linspace(4*comm_rank, 4*comm_rank+4., 10)
    y = np.linspace(0., 10., 10)
    z = np.linspace(-20., -10., 10)

    return x, y, z


def main():

    name = 'rectilinear_mesh_example'
    prefix = '.'
    description = 'This example demonstrates the instrumentation of a simulation based on a rectilinear mesh'

    v = ParallelVisitInstrumentation(name, description, prefix=prefix)

    mesh_name = 'parallel_example_r3'
    mesh_type = VISIT_MESHTYPE_RECTILINEAR
    v.register_mesh(mesh_name, dp, mesh_type, 3, xunits="cm", yunits="cm", xlabel="a", ylabel="b", zunits="cm", zlabel="c")
    v.run()


if __name__ == "__main__":
    main()
