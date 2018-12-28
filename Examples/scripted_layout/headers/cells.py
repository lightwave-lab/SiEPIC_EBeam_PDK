import numpy as np
import math
from math import pi
import pya

from siepic_tools.utils.pcells import CellWithPosition
from siepic_tools.utils.geometry import \
    Port,\
    bezier_optimal
from siepic_tools.utils.pcells import port_to_pin_helper, place_cell
from siepic_tools.utils.layout import \
    layout_rectangle, \
    append_relative,\
    layout_waveguide

from . import EBeamCellWithLayers, cache_cell
from .route_utils import layout_ebeam_waveguide_from_points
from .gds_import import \
    GDSCell,\
    ebeam_adiabatic_te1550,\
    YBranch_te1550


class GCArrayTE(CellWithPosition, EBeamCellWithLayers):
    """ Warning: do not cache!

        Always puts in an alignment waveguide with two extra GCs

    """

    def initialize_default_params(self):
        self.define_param("N_gc", self.TypeInt,
                          "Number of GCs", default=4)
        self.define_param("pitch", self.TypeDouble,
                          "GC array pitch", default=127, readonly=True)
        self.define_param("w", self.TypeDouble,
                          "Input waveguide width", default=0.5, readonly=True)

        CellWithPosition.initialize_default_params(self)
        EBeamCellWithLayers.initialize_default_params(self)

    def pcell(self, layout, cell=None, params=None):
        # Instantiate the cell
        if cell is None:
            cell = layout.create_cell(self.name)

        cp = self.parse_param_args(params)
        origin, ex, ey = CellWithPosition.origin_ex_ey(self, params, multiple_of_90=True)
        lay = EBeamCellWithLayers.pre_pcell(self, layout, params)

        # Instantiate GCs and rotate them accordingly
        libcell, _ = GDSCell("ebeam_gc_te1550", from_library=True)('TE_GC').pcell(layout)
        rot_DTrans = pya.DTrans.R0
        angle_multiple_90 = cp.angle_ex // 90
        rot_DTrans.rot = angle_multiple_90 % 4

        # Insert the grating couplers
        cell.insert(
            pya.DCellInstArray(libcell.cell_index(),
                               pya.DTrans(rot_DTrans, origin),
                               cp.pitch * ey, ex, cp.N_gc + 2, 1))

        # Make the waveguide points for the two outer GCs
        alignment_waveguide = append_relative([origin], 0 * ex, 0 * ey, +17 * ex)
        alignment_waveguide.extend(reversed(append_relative(
            [origin + cp.pitch * (cp.N_gc + 1) * ey], 0 * ex, 0 * ey, +17 * ex)))
        layout_ebeam_waveguide_from_points(cell, alignment_waveguide, width=cp.w)

        # instantiate ports
        port_positions, ports = ([None] * (cp.N_gc),) * 2

        # hooks
        for i in range(1, cp.N_gc + 1):
            origin_01 = origin + cp.pitch * i * ey

            four_points = append_relative([origin_01], 12 * ex, 20 * ey, -62 * ex)
            layout_ebeam_waveguide_from_points(cell, four_points, width=cp.w)
            # update the ports
            port_positions[i - 1] = origin_01 - 50 * ex + 20 * ey
            ports[i - 1] = Port(f'opt{i - 1}', port_positions[i - 1], ex, cp.w)

        port_to_pin_helper(ports, cell, lay.PinRec)

        return cell, {port.name: port for port in ports}


class GCArrayTM(CellWithPosition, EBeamCellWithLayers):
    """ Warning: do not cache!

        Always puts in an alignment waveguide with two extra GCs

    """

    def initialize_default_params(self):
        self.define_param("N_gc", self.TypeInt,
                          "Number of GCs", default=4)
        self.define_param("pitch", self.TypeDouble,
                          "GC array pitch", default=127, readonly=True)
        self.define_param("w", self.TypeDouble,
                          "Input waveguide width", default=0.5, readonly=True)

        CellWithPosition.initialize_default_params(self)
        EBeamCellWithLayers.initialize_default_params(self)

    def pcell(self, layout, cell=None, params=None):
        # Instantiate the cell
        if cell is None:
            cell = layout.create_cell(self.name)

        cp = self.parse_param_args(params)
        origin, ex, ey = CellWithPosition.origin_ex_ey(self, params, multiple_of_90=True)
        lay = EBeamCellWithLayers.pre_pcell(self, layout, params)

        # Instantiate GCs and rotate them accordingly
        libcell, _ = GDSCell("ebeam_gc_tm1550", from_library=True)('TM_GC').pcell(layout)
        rot_DTrans = pya.DTrans.R0
        angle_multiple_90 = cp.angle_ex // 90
        rot_DTrans.rot = (angle_multiple_90 + 2) % 4

        # Insert the grating couplers
        cell.insert(
            pya.DCellInstArray(libcell.cell_index(),
                               pya.DTrans(rot_DTrans, origin),
                               cp.pitch * ey, ex, cp.N_gc + 2, 1))

        # Make the outer waveguide points
        alignment_waveguide = append_relative([origin], -10 * ex, -25 * ey, +80 * ex)
        alignment_waveguide.extend(reversed(append_relative(
            [origin + cp.pitch * (cp.N_gc + 1) * ey], -10 * ex, + 25 * ey, +80 * ex)))

        layout_ebeam_waveguide_from_points(cell, alignment_waveguide, width=cp.w)

        port_positions = [origin + cp.pitch * i * ey for i in range(1, cp.N_gc + 1)]
        ports = [Port(f'opt{i}', pos, ex, cp.w) for i, pos in enumerate(port_positions)]

        port_to_pin_helper(ports, cell, lay.PinRec)

        return cell, {port.name: port for port in ports}


@cache_cell
class DCPad(CellWithPosition, EBeamCellWithLayers):
    """ lays out a DC pad.

    Ports: el0
    """

    def initialize_default_params(self):
        self.define_param("pad_size", self.TypeDouble, "pad size", default=120)
        self.define_param("pad_height", self.TypeDouble,
                          "pad height", default=240)
        self.define_param("port_width", self.TypeDouble,
                          "width of ML wire", default=20)
        EBeamCellWithLayers.initialize_default_params(self)
        CellWithPosition.initialize_default_params(self)

    def pcell(self, layout, cell=None, params=None):
        if cell is None:
            cell = layout.create_cell(self.name)

        cp = self.parse_param_args(params)
        lay = EBeamCellWithLayers.pre_pcell(self, layout, params)
        origin, ex, ey = CellWithPosition.origin_ex_ey(self, params)

        def make_shape_from_dpolygon(dpoly, resize_dx, dbu, layer):
            dpoly.resize(resize_dx, dbu)
            # if resize_dx > dbu:
            #     dpoly.round_corners(resize_dx, 100)
            dpoly.layout(cell, layer)
            return dpoly

        def make_pad(origin, pad_size, pad_height, ex):
            pad_square = layout_rectangle(
                cell, lay.M_Heater, origin, pad_size, pad_height, ex)
            make_shape_from_dpolygon(pad_square, -2.5, layout.dbu, lay.ML)
            make_shape_from_dpolygon(pad_square, -2.5, layout.dbu, lay.MLOpen)

        make_pad(origin + cp.pad_height * ey / 2,
                 cp.pad_size, cp.pad_height, ex)

        ports = [Port('el0', origin + cp.port_width *
                      ey / 2, -ey, cp.port_width)]

        return cell, {port.name: port for port in ports}


@cache_cell
class DCPadArray(DCPad):

    def initialize_default_params(self):
        self.define_param("Npads", self.TypeInt, "Number of pads", default=10)
        self.define_param("dc_pad_pitch", self.TypeInt,
                          "Pitch of pads", default=150)
        DCPad.initialize_default_params(self)

    def pcell(self, layout, cell=None, params=None):
        if cell is None:
            cell = layout.create_cell(self.name)

        cp = self.parse_param_args(params)
        lay = EBeamCellWithLayers.pre_pcell(self, layout, params)
        origin, ex, _ = CellWithPosition.origin_ex_ey(self, params)

        ports = list()
        for i in range(cp.Npads):
            dc_ports = DCPad(f'pad_{i}', cp).place_cell(cell, origin + cp.dc_pad_pitch * i * ex)
            ports.append(dc_ports['el0'].rename(f'el_{i}'))

        port_to_pin_helper(ports, cell, lay.PinRec)

        return cell, {port.name: port for port in ports}


@cache_cell
class MZI(YBranch_te1550, ebeam_adiabatic_te1550):
    """ lays out a MZI.

    Ports: el0 el1, opt1, opt2, opt3
    """

    def initialize_default_params(self):

        self.define_param("w", self.TypeDouble, "Waveguide width", default=.5)
        self.define_param("textpolygon", self.TypeInt,
                          "Draw text polygon label? 0/1", default=1)
        self.define_param("layout_ports", self.TypeBoolean,
                          "Layout Pins?", default=True)
        self.define_param("heater_width", self.TypeDouble,
                          "width of ML wire", default=3.05)
        self.define_param("MZI_height", self.TypeDouble,
                          "The height of MZI", default=40)

        EBeamCellWithLayers.initialize_default_params(self)
        CellWithPosition.initialize_default_params(self)
        YBranch_te1550.initialize_default_params(self)
        ebeam_adiabatic_te1550.initialize_default_params(self)

    def pcell(self, layout, cell=None, params=None):

        if cell is None:
            cell = layout.create_cell(self.name)

        cp = self.parse_param_args(params)
        lay = EBeamCellWithLayers.pre_pcell(self, layout, params)
        origin, ex, ey = CellWithPosition.origin_ex_ey(self, params)

        YBranch_te1550_Cell, YBranch_Ports = YBranch_te1550(
            "YBranch", cp).pcell(layout, params={})
        YBranch_Ports = place_cell(
            cell, YBranch_te1550_Cell, YBranch_Ports, origin)

        ebeam_adiabatic_te1550_Cell, ebeam_adiabatic_te1550_Ports = ebeam_adiabatic_te1550(
            "adiabatic", cp).pcell(layout, params={})
        ebeam_adiabatic_te1550_Ports = place_cell(
            cell, ebeam_adiabatic_te1550_Cell, ebeam_adiabatic_te1550_Ports, origin + 150 * ex)
        MZI_height = cp.MZI_height

        waveguide_points = []
        waveguide_points = [origin + 30 * ex + MZI_height / 2 *
                            ey, origin + (100 + 30) * ex + MZI_height / 2 * ey]

        layout_waveguide(cell, lay.Si, waveguide_points, cp.w)

        layout_waveguide(cell, lay.M_Heater, waveguide_points, cp.heater_width)
        layout_waveguide(cell, lay.M_Heater, [waveguide_points[0] + 1 / 2 * cp.heater_width * ex,
                                              waveguide_points[0] + 1 / 2 * cp.heater_width * ex + 30 * ey], [cp.heater_width, 3 * cp.heater_width])
        layout_waveguide(cell, lay.M_Heater, [waveguide_points[1] - 1 / 2 * cp.heater_width * ex,
                                              waveguide_points[1] - 1 / 2 * cp.heater_width * ex - 50 * ey], [cp.heater_width, 3 * cp.heater_width])

        waveguide_points_1 = []
        waveguide_points_1 = [origin + 30 * ex - MZI_height /
                              2 * ey, origin + (100 + 30) * ex - MZI_height / 2 * ey]

        layout_waveguide(cell, lay.Si, waveguide_points_1, cp.w)

        def layout_bezier(point1_position, point2_position, point1_direction, point2_direction):
            dbu = cell.layout().dbu
            P0 = point1_position - dbu * point1_direction
            P3 = point2_position - dbu * point2_direction
            angle_from = np.arctan2(
                point1_direction.y, point1_direction.x) * 180 / pi
            angle_to = np.arctan2(-point2_direction.y, -
                                  point2_direction.x) * 180 / math.pi
            curve = bezier_optimal(P0, P3, angle_from, angle_to)
            layout_waveguide(cell, lay.Si, curve, [cp.w, cp.w], smooth=True)

        layout_bezier(YBranch_Ports['opt2'].position, origin + 30 *
                      ex + MZI_height / 2 * ey, YBranch_Ports['opt2'].direction, -ex)
        layout_bezier(YBranch_Ports['opt3'].position, origin + 30 *
                      ex - MZI_height / 2 * ey, YBranch_Ports['opt3'].direction, -ex)

        layout_bezier(origin + (100 + 30) * ex + MZI_height / 2 * ey, ebeam_adiabatic_te1550_Ports[
                      'opt1'].position, -ebeam_adiabatic_te1550_Ports['opt1'].direction, -ex)
        layout_bezier(origin + (100 + 30) * ex - MZI_height / 2 * ey, ebeam_adiabatic_te1550_Ports[
                      'opt2'].position, -ebeam_adiabatic_te1550_Ports['opt2'].direction, -ex)

        ports = []

        ports.append(YBranch_Ports["opt1"].rename("opt1"))
        ports.append(Port(
            "opt2", ebeam_adiabatic_te1550_Ports["opt3"].position, ex, ebeam_adiabatic_te1550_Ports["opt3"].width))
        ports.append(Port(
            "opt3", ebeam_adiabatic_te1550_Ports["opt4"].position, ex, ebeam_adiabatic_te1550_Ports["opt4"].width))
        ports.append(Port(
            "el1", waveguide_points[0] + 1 / 2 * cp.heater_width * ex + 30 * ey, ey, 3 * cp.heater_width))
        ports.append(Port(
            "el2", waveguide_points[1] - 1 / 2 * cp.heater_width * ex - 50 * ey, -ey, 3 * cp.heater_width))

        if cp.layout_ports:
            port_to_pin_helper(ports, cell, lay.PinRec)

        return cell, {port.name: port for port in ports}


@cache_cell
class MinimalCellIncluding_MZI(MZI, YBranch_te1550):

    """el1, el2, opt_in, opt_out
    """

    def initialize_default_params(self):
        MZI.initialize_default_params(self)
        YBranch_te1550.initialize_default_params(self)

    def pcell(self, layout, cell=None, params=None):

        if cell is None:
            cell = layout.create_cell(self.name)

        cp = self.parse_param_args(params)
        lay = EBeamCellWithLayers.pre_pcell(self, layout, params)
        origin, ex, ey = CellWithPosition.origin_ex_ey(self, params)

        MZI_Cell, MZI_Ports = MZI(
            "MZI", cp).pcell(layout, params={'layout_ports': False})
        MZI_Ports = place_cell(cell, MZI_Cell, MZI_Ports, origin)

        ports = []

        ports.append(MZI_Ports["el1"].rename("el1"))
        ports.append(MZI_Ports["el2"].rename("el2"))
        ports.append(MZI_Ports["opt1"].rename("opt_in"))
        ports.append(MZI_Ports["opt2"].rename("opt_out1"))
        ports.append(MZI_Ports["opt3"].rename("opt_out2"))

        if cp.layout_ports:
            port_to_pin_helper(ports, cell, lay.PinRec)

        return cell, {port.name: port for port in ports}
