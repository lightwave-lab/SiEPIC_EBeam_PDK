import numpy as np
import math
from math import pi

from SiEPIC.utils.geometry import Port, bezier_optimal
from SiEPIC.utils.pcells import port_to_pin_helper, place_cell
from SiEPIC.utils.pcells import CellWithPosition
from SiEPIC.utils.layout import  \
    layout_waveguide


from . import EBeamCellWithLayers, cache_cell
from .gds_import import \
    ebeam_adiabatic_te1550,\
    YBranch_te1550


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
