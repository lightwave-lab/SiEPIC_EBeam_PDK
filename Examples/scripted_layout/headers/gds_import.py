import os

from SiEPIC.utils.pcells import CellWithPosition
from SiEPIC.utils.geometry import Port
from SiEPIC.utils.gds_import import GDSCell as DefaultGDSCell

LOCAL_GDS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'gds_cells')


def GDSCell(cell_name, filename=None, from_library=False, gds_dir=LOCAL_GDS_DIR):
    '''
        Args:
            cell_name: cell within that file.
            filename: is the gds file name. Ignored if from_library is set.
            from_library: True if from EBeam library

        Returns:
            (class) a GDS_cell_base class that can be inherited
    '''
    if from_library:
        from_library = 'EBeam'
    else:
        from_library = None

    return DefaultGDSCell(cell_name, filename=filename, from_library=from_library, gds_dir=gds_dir)


class ebeam_adiabatic_te1550(GDSCell('ebeam_adiabatic_te1550', from_library=True)):
    """
    The PCell version of directional coupler
    """
    # def initialize_default_params(self):
    #     self.define_param("layout_ports", self.TypeDouble,
    #                       "layout_ports", default=True, readonly=True)

    def pcell(self, layout, cell=None, params=None):
        cell, _ = super().pcell(layout, cell=cell, params=params)

        _, ex, ey = CellWithPosition.origin_ex_ey(self, params)

        opt1_position = 0.1 * ex + 1.5 * ey
        opt2_position = 0.1 * ex + - 1.5 * ey
        opt3_position = 195.9 * ex + 1.5 * ey
        opt4_position = 195.9 * ex + - 1.5 * ey

        ports = [Port("opt1", opt1_position, -ex, 0.5),
                 Port("opt2", opt2_position, -ex, 0.5),
                 Port("opt3", opt3_position, ex, 0.5),
                 Port("opt4", opt4_position, ex, 0.5)]

        return cell, {port.name: port for port in ports}


class YBranch_te1550(GDSCell('ebeam_y_1550', from_library=True)):
    """
    The PCell version of YBranch, mainly for use in scripts.
    """
    # def initialize_default_params(self):
    #     self.define_param("layout_ports", self.TypeDouble,
    #                       "layout_ports", default=True, readonly=True)

    def pcell(self, layout, cell=None, params=None):
        cell, _ = super().pcell(layout, cell=cell, params=params)

        _, ex, ey = CellWithPosition.origin_ex_ey(self, params)

        opt1_position = -7.4 * ex + 0 * ey

        opt2_position = 7.4 * ex + 2.75 * ey
        opt3_position = 7.4 * ex + -2.75 * ey

        ports = [Port("opt1", opt1_position, -ex, 0.5),
                 Port("opt2", opt2_position, ex, 0.5),
                 Port("opt3", opt3_position, ex, 0.5)]

        return cell, {port.name: port for port in ports}
