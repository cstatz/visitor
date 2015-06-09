# -*- coding: utf-8 -*-

from __future__ import division

import logging

from .serial import VisitInstrumentation
from .parallel import ParallelVisitInstrumentation

from simV2 import *


__author__ = "Christoph Statz"
__copyright__ = "Copyright 2015, Technische Universität Dresden"
__credits__ = []
__license__ = "BSD, 2-clause, see included LICENSE file."
__version__ = "0.0.1"
__maintainer__ = "Christoph Statz"
__email__ = "christoph.statz@tu-dresden.de"
__status__ = "Development"


try:
    from nicelog.formatters import ColorLineFormatter
    import sys
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorLineFormatter(show_date=True, show_function=True, show_filename=True, message_inline=True))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
except:
    pass