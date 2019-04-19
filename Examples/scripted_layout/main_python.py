import pya  # this is the main module of klayout

# system imports
import os
import sys

pwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(pwd)
from siepic_tools.utils.gitpath import root
try:
    sys.path.append(root())
except IOError:
    print("WARNING: this is not a git repository (not adding root to sys.path)")
    print("         if you don't know what this is, please ignore.")
sys.path.append(os.path.join(root(), 'klayout_dot_config', 'python'))

# siepic and global imports
from siepic_ebeam_pdk import EBEAM_TECH

from headers import EX, EY
from headers.experiments import \
    MZI, \
    MZI_FanRight, \
    MZI_Experiment


TECHNOLOGY = EBEAM_TECH
# TECHNOLOGY
# {'technology_name': 'EBeam',
#  'dbu': 0.001,
#  'base_path': '/Users/tlima/.klayout/tech/EBeam',
#  'INTC_CML': 'EBeam_v2018_03_04.cml',
#  'INTC_CML_path': '/Users/tlima/.klayout/tech/EBeam/EBeam_v2018_03_04.cml',
#  'INTC_CML_version': 'v2018_03_04.cml',
#  'Si': 1/0,
#  'Text': 10/0,
#  '26_SEM_ROI': 26/0,
#  '31_Si_p6nm': 31/0,
#  '32_Si_p4nm': 32/0,
#  '33_Si_p2nm': 33/0,
#  'M1': 11/0,
#  '12_M2': 12/0,
#  '13_MLopen': 13/0,
#  'FloorPlan': 99/0,
#  'DevRec': 68/0,
#  'PinRec': 1/10,
#  'FbrTgt': 81/0,
#  'Errors': 999/0,
#  'Lumerical': 733/0,
#  'Waveguide': 1/0}

if __name__ == '__main__':
    layout = pya.Layout()
    dbu = layout.dbu = 0.001
    TOP = layout.create_cell("TOP")

    # laySi = layout.layer(TECHNOLOGY['Si'])
    # lay_ML = layout.layer(TECHNOLOGY['13_MLopen'])
    # lay_M2 = layout.layer(TECHNOLOGY['12_M2'])
    # lay_M1 = layout.layer(TECHNOLOGY['M1'])
    # lay_DevRec = layout.layer(TECHNOLOGY['DevRec'])
    # lay_Pin = layout.layer(TECHNOLOGY['PinRec'])
    lay_Text = layout.layer(TECHNOLOGY['Text'])
    # lay_FloorPlan = layout.layer(TECHNOLOGY["FloorPlan"])
    # lay_SEM_ROI = layout.layer(TECHNOLOGY["26_SEM_ROI"])
    # lay_Si_p6nm = layout.layer(TECHNOLOGY["31_Si_p6nm"])
    # lay_Si_p4nm = layout.layer(TECHNOLOGY["32_Si_p4nm"])
    # lay_Si_p2nm = layout.layer(TECHNOLOGY["33_Si_p2nm"])

    origin = pya.DPoint(0, 0)

    def place_text(cell, text, position):
        trans = pya.DTrans(pya.DTrans.R0, position)
        text = pya.DText(text, trans)
        text_shape = cell.shapes(lay_Text).insert(text)
        text_shape.text_size = 12 / cell.layout().dbu

    MZI('MZI').place_cell(TOP, origin + 53.84000 * EY)
    place_text(TOP, 'Basic cell', origin + 123.5 * EY)
    MZI_FanRight('MZI_FanRight').place_cell(TOP, origin - 132.12000 * EY)
    place_text(TOP, 'Basic cell with optical routing', origin - 60 * EY)
    MZI_Experiment('MZI_Experiment').place_cell(TOP, origin - 500 * EY)
    place_text(TOP, 'Basic cell with optical/electrical routing', origin - 230 * EY)

    layout.write('example_mask.gds')
