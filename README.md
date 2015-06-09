# Visitor libsimV2 Python Instrumentation and Adapter
---

## Installation
    python setup.py install

## Usage
Examples are provided in the examples/ directory.
The discovery of visit env and directories is automated.
On runtime you need to have the path to the visit binary in your PATH

    PATH=<path to the directory containing the visit> python <your instrumented simulation>.py

## General definitions and remarks

* Bounds in parameters and return values are a 2-Tuple of Tuples of the lowest and the highest coordinate: ((low_x, low_y, ...), (high_x, high_y, ...)).
* Data can be passed as numpy.ndarray or as list.
* Integers should be of type int32.
