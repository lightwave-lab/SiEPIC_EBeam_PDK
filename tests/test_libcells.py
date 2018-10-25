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

LOCAL_GDS_DIR = os.path.join(root_dir, example_gds)
gds_name = 'GSiP_RingMod_Transceiver.gds'
cell_name = 'GSiP_RingMod_Transceiver'

#: these are formatted like (path, filename, cell_name)
cells_of_interest = [
                     ('.', 'RingResonator.gds', 'Ring'),
                     # ('.', 'UBC_Logo.gds', 'UBC_Logo'),
                     # ('.', 'mzi_adjustable_splitter.gds', 'f'),
                     # ('.', 'Bragg.gds', 'f'),
                     # ('.', 'Crossings.gds', 'a'),
                     # ('GSiP/Transceiver', 'GSiP_RingMod_Transceiver.gds', 'GSiP_RingMod_Transceiver'),
                     # ('CustomComponentTutorial', 'ebeam_taper_475_500_te1550_testcircuit.gds', 'taper_test_circuit'),
                    ]

@contained_pyaCell
def Fixed_Cells(TOP):
    ''' Using klayout's traditional read gds, insert cell method '''
    ly = TOP.layout()
    for path, filename, cell_name in cells_of_interest:
        cell = GDSCell(cell_name, filename=filename, gds_dir=path)
        ly.read(os.path.join(path, filename))
        gdscell2 = ly.cell(cell_name)
        rot_DTrans = pya.DTrans.R0
        TOP.insert(pya.DCellInstArray(gdscell2.cell_index(),
                                      pya.DTrans(rot_DTrans, origin)))

def test_Fixed_Cells(): difftest_it(Fixed_Cells, file_ext='.oas')()
