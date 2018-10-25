import SiEPIC  # do this first to trigger extend.py

import pya
from pya import PCellDeclarationHelper, DPath, DPoint, Trans, Path, Point, Text, Polygon

from lytest import contained_pyaCell, difftest_it

from SiEPIC.utils.gds_import import GDSCell

import os

origin = pya.DPoint(0, 0)
ex = pya.DVector(1, 0)


root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
example_dir = os.path.join(root_dir, 'Examples')

#: these are formatted like (relpath, filename, cell_name)
cells_of_interest = [
                     ('.', 'RingResonator.gds', 'Ring'),
                     ('.', 'UBC_Logo.gds', 'UBC_Logo'),
                     ('.', 'mzi_adjustable_splitter.gds', 'f'),
                     ('.', 'Bragg.gds', 'f'),
                     # ('.', 'Crossings.gds', 'a'),
                     # ('GSiP/Transceiver', 'GSiP_RingMod_Transceiver.gds', 'GSiP_RingMod_Transceiver'),
                     # ('CustomComponentTutorial', 'ebeam_taper_475_500_te1550_testcircuit.gds', 'taper_test_circuit'),
                    ]

def do_fixed_cell(topcell, relpath, filename, cell_name):
    ly = topcell.layout()
    gds_dir = os.path.join(example_dir, relpath)
    ly.read(os.path.join(gds_dir, filename))
    gdscell2 = ly.cell(cell_name)
    rot_DTrans = pya.DTrans.R0
    topcell.insert(pya.DCellInstArray(gdscell2.cell_index(),
                                  pya.DTrans(rot_DTrans, origin)))

@contained_pyaCell
def Fixed_RingResonator(TOP):
    do_fixed_cell(TOP, '.', 'RingResonator.gds', 'Ring')

def test_Fixed_RingResonator(): difftest_it(Fixed_RingResonator, file_ext='.oas')()


@contained_pyaCell
def Fixed_UBC_Logo(TOP):
    do_fixed_cell(TOP, '.', 'UBC_Logo.gds', 'UBC_Logo')

def test_Fixed_UBC_Logo(): difftest_it(Fixed_UBC_Logo, file_ext='.oas')()


@contained_pyaCell
def Fixed_mzi_adjustable_splitter(TOP):
    do_fixed_cell(TOP, '.', 'mzi_adjustable_splitter.gds', 'f')

def test_Fixed_mzi_adjustable_splitter(): difftest_it(Fixed_mzi_adjustable_splitter, file_ext='.oas')()


@contained_pyaCell
def Fixed_Bragg(TOP):
    do_fixed_cell(TOP, '.', 'Bragg.gds', 'f')

def test_Fixed_Bragg(): difftest_it(Fixed_Bragg, file_ext='.oas')()
