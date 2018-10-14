import pya
import os
import sys
from contextlib import contextmanager
from SiEPIC.utils import get_technology_by_name


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


WAVEGUIDE_RADIUS = 10
WAVEGUIDE_WIDTH = 0.5


def layout_ebeam_waveguide_from_points(cell, points_list, radius=None, width=None):
    """ Takes a list of points and calls SiEPIC Waveguide Pcell
        The points_list should be a rough shape of the waveguide.
        The points_list must be a manhattan path!
        This function will create a smooth waveguide by rounding the trace
        at every corner with a particular radius.

        For example, if points_list has three points forming a square of size
        R, then the output will be a 90-degree arc of radius R.
    """
    from math import floor
    TECHNOLOGY = get_technology_by_name('EBeam')
    if radius is None:
        radius = WAVEGUIDE_RADIUS
    if width is None:
        width = WAVEGUIDE_WIDTH
    for point in points_list:
        point.x = floor(point.x * 1000) / 1000
        point.y = floor(point.y * 1000) / 1000

    for i in range(0, len(points_list) - 1):
        """
        Calculate the x distance and the y distance to the next point.
        Get the max of the above two numbers
        Set the other number to zero
        """
        posx = abs(points_list[i + 1].x - points_list[i].x)
        posy = abs(points_list[i + 1].y - points_list[i].y)
        if abs(points_list[i + 1].x - points_list[i].x) > 0 and abs(points_list[i + 1].y - points_list[i].y) > 0:
            if posx < posy:
                points_list[i + 1].x = points_list[i].x
            else:
                points_list[i + 1].y = points_list[i].y

    wg_dpath = pya.DPath(points_list, 0.5)
    layout = cell.layout()
    with suppress_stdout():
        wg_cell = layout.create_cell("Waveguide", TECHNOLOGY['technology_name'],
                                     {"path": wg_dpath,
                                      "radius": radius,
                                      "width": width,
                                      "layers": ['Si'],
                                      "widths": [width],
                                      "offsets": [0]})

    layerSi = layout.layer(TECHNOLOGY['Si'])
    # let's just get the shapes
    cell.shapes(layerSi).insert(wg_cell.shapes(layerSi))

    layout.delete_cell(wg_cell.cell_index())

    return cell
