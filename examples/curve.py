#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

import numpy as np
from visitor import VisitInstrumentation


counter = 0
size = 100
x = np.linspace(0., 2.*np.pi-np.pi/size, size)

def wave_function(x):
    global counter
    return np.cos(x-counter/180*np.pi)

def dp(*args, **kwargs):
    y = wave_function(x)
    return x, y

def cycle_time_provider(*args, **kwargs):
    return counter, counter*np.pi/size

def step(*args, **kwargs):
    global counter
    counter += 1

def main():

    name = 'curve_data_example'
    prefix = '.'
    description = 'This example demonstrates the instrumentation of a simulation based resulting curve data.'

    v = VisitInstrumentation(name, description, prefix=prefix, step=step, cycle_time_provider=cycle_time_provider)
    v.register_curve('wave_packet', dp)
    v.run()

if __name__ == '__main__':
    main()
