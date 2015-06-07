#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

__author__ = 'Christoph Statz'

from setuptools import find_packages, setup

setup(name='visitor',
      version='0.0.1',
      description='This module implements a wrapper for libsimV2, in order to facilitate an VisIt instrumentation for a simulation.',
      author='Christoph Statz',
      author_email='christoph.statz@tu-dresden.de',
      url='http://www.cstatz.de/python',
      packages=find_packages(),
      install_requires=['numpy>=1.8.0', 'enum34', 'mpi4py'],
      )
