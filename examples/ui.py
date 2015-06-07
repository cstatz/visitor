#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

import numpy as np
from time import sleep
from visitor import *
from visitor import VisitInstrumentation, VISIT_MESHTYPE_POINT


counter = 0


def dp(*args, **kwargs):
    x = np.linspace(-5.,4.,100)
    y = np.linspace(0.,10.,100)
    return x, y

def cycle_time_provider(*args, **kwargs):
    return counter, counter/1e9

def step(*args, **kwargs):
    global counter
    sleep(0.2)
    counter += 1

def count(*arg, **kwargs):
    return counter

def message(*arg, **kwargs):
    return str(counter/1e9)

def number(arg, *args, **kwargs):
    print arg

def main():

    name = 'ui_example'
    prefix = '.'
    description = 'This example demonstrates the ui capabilities of libsim.'

    v = VisitInstrumentation(name, description, prefix=prefix, step=step, cycle_time_provider=cycle_time_provider, ui="./example.ui", )
    v.register_mesh('point_mesh_2d', dp, VISIT_MESHTYPE_POINT, 2, number_of_domains=1, domain_title="Domains", domain_piece_name="domain", num_of_groups=0, xunits="cm", yunits="cm", xlabel="a", ylabel="b")
    v.register_ui_set_int("progress", count)
    v.register_ui_set_string("text", message)
    v.register_ui_value("spin", number, None)
    v.register_ui_value("dial", number, None)

    v.run()

if __name__ == '__main__':
    main()
