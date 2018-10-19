'''
For now, this file must be called by pytest within the klayout interpreter::

    klayout -e -z launch_python_test.py

or

    make test

In order for it to be called directly from pytest,
1. klayout.db must be installed
2. headers must get pya via `from lygadgets import pya`
3. we figure out a way to expose EBeam PCells to the regular python interpreter

Then, remove the 'fake_' from this filename and it will be run automatically.
'''

import os
import sys
import pya

import lytest
from lytest import contained_pyaCell, difftest_it

makefile_dir = os.path.dirname(__file__)
lytest.utest_buds.test_root = makefile_dir

from headers.experiments import MZI


@contained_pyaCell
def BasicCell(TOP):
    MZI('MZI').place_cell(TOP, pya.DPoint(0, 0))
def test_BasicCell(): difftest_it(BasicCell, file_ext='.oas')()
