# Python script

"""
This file is part of the SiEPIC_EBeam_PDK
by Lukas Chrostowski (c) 2015-2017

This Python file implements a library called "SiEPIC_EBeam", consisting of mature components that have Layouts and Compact Models for circuit simulations:
 - Fixed GDS cell components: imported from SiEPIC-EBeam.gds
 - PCells:
    - ebeam_dc_halfring_straight
    - ebeam_bragg_te1550: waveguide Bragg grating
        - ebeam_taper_te1550: Waveguide Taper
        - Waveguide_bump
        - Waveguide_SBend
        - Waveguide_Bend

NOTE: after changing the code, the macro needs to be rerun to install the new
implementation. The macro is also set to "auto run" to install the PCell
when KLayout is run.

Crash warning:
 https://www.klayout.de/forum/comments.php?DiscussionID=734&page=1#Item_13
 This library has nested PCells. Running this macro with a layout open may
 cause it to crash. Close the layout first before running.

Version history:

Lukas Chrostowski           2015/11/05 - 2015/11/10
 - Double-bus ring resonator
 - waveguide bends
 - PCell parameter functions
 - polygon text
 - PCell calling another PCell - TestStruct_DoubleBus_Ring

Lukas Chrostowski           2015/11/14
 - fix for rounding error in "DoubleBus_Ring"

Lukas Chrostowski           2015/11/15
 - fix for Python 3.4: print("xxx")

Lukas Chrostowski           2015/11/17
 - update "layout_waveguide_rel" to use the calculated points_per_circle(radius)

Lukas Chrostowski           2015/11/xx
 - Waveguide based on bends, straight waveguide.

Lukas Chrostowski           2015/12/3
 - Bragg grating

Lukas Chrostowski           2016/01/17
 - Taper, matching EBeam CML component

Lukas Chrostowski           2016/01/20
 - (sinusoidal) Bragg grating

Lukas Chrostowski           2016/05/27
 - SWG_waveguide
 - SWG_to_strip_waveguide

S. Preble                   2016/08/26
 - Double Bus Ring Pin's shifted - text now is in the middle of the pin path

Lukas Chrostowski           2016/11/06
 - waveguide bump, to provide a tiny path length increase

Lukas Chrostowski           2017/02/14
 - renaming "SiEPIC" PCells library to "SiEPIC-EBeam PCells", update for Waveguide_Route
 - code simplifications: Box -> Box

Lukas Chrostowski           2017/03/08
 - S-Bend - Waveguide_SBend

Lukas Chrostowski           2017/03/18
 - ebeam_dc_halfring_straight, with TE/TM support.  Zeqin Lu adding CML for this component.

Lukas Chrostowski 2017/12/16
 - compatibility with KLayout 0.25 and SiEPIC-Tools

todo:
replace:
 layout_arc_wg_dbu(self.cell, Layerm1N, x0,y0, r_m1_in, w_m1_in, angle_min_doping, angle_max_doping)
with:
 self.cell.shapes(Layerm1N).insert(Polygon(arc(w_m1_in, angle_min_doping, angle_max_doping) + [Point(0, 0)]).transformed(t))


"""
import math
from SiEPIC.utils import get_technology, get_technology_by_name

# Import KLayout Python API methods:
# Box, Point, Polygon, Text, Trans, LayerInfo, etc
from pya import Box, Point, Polygon, Text, Trans, LayerInfo, \
    PCellDeclarationHelper, DPoint, DPath, Path, ShapeProcessor, \
    Library, CellInstArray


class Waveguide(PCellDeclarationHelper):

    def __init__(self):
        # Important: initialize the super class
        super(Waveguide, self).__init__()
        # declare the parameters
        TECHNOLOGY = get_technology_by_name('EBeam')
        self.param("path", self.TypeShape, "Path", default=DPath(
            [DPoint(0, 0), DPoint(10, 0), DPoint(10, 10)], 0.5))
        self.param("radius", self.TypeDouble, "Radius", default=5)
        self.param("width", self.TypeDouble, "Width", default=0.5)
        self.param("adiab", self.TypeBoolean, "Adiabatic", default=False)
        self.param("bezier", self.TypeDouble, "Bezier Parameter", default=0.35)
        self.param("layers", self.TypeList, "Layers", default=['Waveguide'])
        self.param("widths", self.TypeList, "Widths", default=[0.5])
        self.param("offsets", self.TypeList, "Offsets", default=[0])

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Waveguide_%s" % self.path

    def coerce_parameters_impl(self):
        from SiEPIC.extend import to_itype
        print("EBeam.Waveguide coerce parameters")

        if 0:
            TECHNOLOGY = get_technology_by_name('EBeam')
            dbu = self.layout.dbu
            wg_width = to_itype(self.width, dbu)
            for lr in range(0, len(self.layers)):
                layer = self.layout.layer(TECHNOLOGY[self.layers[lr]])
                width = to_itype(self.widths[lr], dbu)
                # check to make sure that the waveguide with parameters are consistent in
                # both places
                if self.layout.layer(TECHNOLOGY['Waveguide']) == layer:
                    if width != wg_width:
                        self.widths[lr] = self.width
                # check to make sure that the DevRec is bigger than the waveguide width
                if self.layout.layer(TECHNOLOGY['DevRec']) == layer:
                    if width < wg_width:
                        self.widths[lr] = self.width * 2

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def transformation_from_shape_impl(self):
        return Trans(Trans.R0, 0, 0)

    def parameters_from_shape_impl(self):
        self.path = self.shape.dpath

    def produce_impl(self):

        from SiEPIC.utils import arc_xy, arc_bezier, angle_vector, angle_b_vectors, inner_angle_b_vectors, translate_from_normal
        from math import cos, sin, pi, sqrt
        import pya
        from SiEPIC.extend import to_itype

        print("EBeam.Waveguide")

        TECHNOLOGY = get_technology_by_name('EBeam')

        dbu = self.layout.dbu
        wg_width = to_itype(self.width, dbu)
        path = self.path.to_itype(dbu)

        if not (len(self.layers) == len(self.widths) and len(self.layers) == len(self.offsets) and len(self.offsets) == len(self.widths)):
            raise Exception("There must be an equal number of layers, widths and offsets")
        path.unique_points()
        turn = 0
        for lr in range(0, len(self.layers)):
            layer = self.layout.layer(TECHNOLOGY[self.layers[lr]])

            width = to_itype(self.widths[lr], dbu)
            offset = to_itype(self.offsets[lr], dbu)

            pts = path.get_points()
            wg_pts = [pts[0]]
            for i in range(1, len(pts) - 1):
                turn = ((angle_b_vectors(pts[i] - pts[i - 1],
                                         pts[i + 1] - pts[i]) + 90) % 360 - 90) / 90
                dis1 = pts[i].distance(pts[i - 1])
                dis2 = pts[i].distance(pts[i + 1])
                angle = angle_vector(pts[i] - pts[i - 1]) / 90
                pt_radius = to_itype(self.radius, dbu)
                # determine the radius, based on how much space is available
                if len(pts) == 3:
                    pt_radius = min(dis1, dis2, pt_radius)
                else:
                    if i == 1:
                        if dis1 <= pt_radius:
                            pt_radius = dis1
                    elif dis1 < 2 * pt_radius:
                        pt_radius = dis1 / 2
                    if i == len(pts) - 2:
                        if dis2 <= pt_radius:
                            pt_radius = dis2
                    elif dis2 < 2 * pt_radius:
                        pt_radius = dis2 / 2
                # waveguide bends:
                if(self.adiab):
                    wg_pts += Path(arc_bezier(pt_radius, 270, 270 + inner_angle_b_vectors(pts[i - 1] - pts[i], pts[i + 1] - pts[
                                   i]), self.bezier, DevRec='DevRec' in self.layers[lr]), 0).transformed(Trans(angle, turn < 0, pts[i])).get_points()
                else:
                    wg_pts += Path(arc_xy(-pt_radius, pt_radius, pt_radius, 270, 270 + inner_angle_b_vectors(pts[i - 1] - pts[i], pts[
                                   i + 1] - pts[i]), DevRec='DevRec' in self.layers[lr]), 0).transformed(Trans(angle, turn < 0, pts[i])).get_points()
            wg_pts += [pts[-1]]
            wg_pts = pya.Path(wg_pts, 0).unique_points().get_points()
            wg_polygon = Polygon(translate_from_normal(wg_pts, width / 2 + (offset if turn > 0 else - offset)) +
                                 translate_from_normal(wg_pts, -width / 2 + (offset if turn > 0 else - offset))[::-1])
            self.cell.shapes(layer).insert(wg_polygon)

            if self.layout.layer(TECHNOLOGY['Waveguide']) == layer:
                waveguide_length = wg_polygon.area() / self.width * dbu**2

        pts = path.get_points()
        LayerPinRecN = self.layout.layer(TECHNOLOGY['PinRec'])

        t1 = Trans(angle_vector(pts[0] - pts[1]) / 90, False, pts[0])
        self.cell.shapes(LayerPinRecN).insert(
            Path([Point(-50, 0), Point(50, 0)], self.width / dbu).transformed(t1))
        self.cell.shapes(LayerPinRecN).insert(Text("pin1", t1, 0.3 / dbu, -1))

        t = Trans(angle_vector(pts[-1] - pts[-2]) / 90, False, pts[-1])
        self.cell.shapes(LayerPinRecN).insert(
            Path([Point(-50, 0), Point(50, 0)], self.width / dbu).transformed(t))
        self.cell.shapes(LayerPinRecN).insert(Text("pin2", t, 0.3 / dbu, -1))

        LayerDevRecN = self.layout.layer(TECHNOLOGY['DevRec'])

        # Compact model information
        angle_vec = angle_vector(pts[0] - pts[1]) / 90
        halign = 0  # left
        angle = 0
        pt2 = pts[0]
        pt3 = pts[0]
        if angle_vec == 0:  # horizontal
            halign = 2  # right
            angle = 0
            pt2 = pts[0] + Point(0, wg_width)
            pt3 = pts[0] + Point(0, -wg_width)
        if angle_vec == 2:  # horizontal
            halign = 0  # left
            angle = 0
            pt2 = pts[0] + Point(0, wg_width)
            pt3 = pts[0] + Point(0, -wg_width)
        if angle_vec == 1:  # vertical
            halign = 2  # right
            angle = 1
            pt2 = pts[0] + Point(wg_width, 0)
            pt3 = pts[0] + Point(-wg_width, 0)
        if angle_vec == -1:  # vertical
            halign = 0  # left
            angle = 1
            pt2 = pts[0] + Point(wg_width, 0)
            pt3 = pts[0] + Point(-wg_width, 0)

        t = Trans(angle, False, pts[0])
        text = Text('Lumerical_INTERCONNECT_library=Design kits/ebeam', t, 0.1 / dbu, -1)
        text.halign = halign
        shape = self.cell.shapes(LayerDevRecN).insert(text)
        t = Trans(angle, False, pt2)
        text = Text('Component=ebeam_wg_integral_1550', t, 0.1 / dbu, -1)
        text.halign = halign
        shape = self.cell.shapes(LayerDevRecN).insert(text)
        t = Trans(angle, False, pt3)
        pts_txt = str([[round(p.to_dtype(dbu).x, 3), round(p.to_dtype(dbu).y, 3)]
                       for p in pts]).replace(', ', ',')
        text = Text(
            'Spice_param:wg_length=%.3fu wg_width=%.3fu points="%s" radius=%s' %
            (waveguide_length, self.width, pts_txt, self.radius), t, 0.1 / dbu, -1)
        text.halign = halign
        shape = self.cell.shapes(LayerDevRecN).insert(text)


class ebeam_dc_halfring_straight(PCellDeclarationHelper):
    """
    The PCell declaration for the ebeam_dc_halfring_straight.
    Consists of a half-ring with 1 waveguides.
    """

    def __init__(self):

        # Important: initialize the super class
        super(ebeam_dc_halfring_straight, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("silayer", self.TypeLayer, "Si Layer", default=TECHNOLOGY['Waveguide'])
        self.param("r", self.TypeDouble, "Radius", default=10)
        self.param("w", self.TypeDouble, "Waveguide Width", default=0.5)
        self.param("g", self.TypeDouble, "Gap", default=0.2)
        self.param("Lc", self.TypeDouble, "Coupler Length", default=0.0)
        self.param("orthogonal_identifier", self.TypeInt,
                   "Orthogonal identifier (1=TE, 2=TM)", default=1)
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])
        self.param("textl", self.TypeLayer, "Text Layer", default=TECHNOLOGY['Text'])

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "ebeam_dc_halfring_straight(R=" + ('%.3f' % self.r) + ",g=" + ('%g' % (1000 * self.g)) + ",Lc=" + ('%g' % (1000 * self.Lc)) + ",orthogonal_identifier=" + ('%s' % self.orthogonal_identifier) + ")"

    def can_create_from_shape_impl(self):
        return False

    def produce_impl(self):
        # This is the main part of the implementation: create the layout

        from math import pi, cos, sin
        from SiEPIC.utils import arc_wg, arc_wg_xy
        from SiEPIC._globals import PIN_LENGTH

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout
        shapes = self.cell.shapes

        LayerSiN = ly.layer(self.silayer)
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)
        TextLayerN = ly.layer(self.textl)

        w = int(round(self.w / dbu))
        r = int(round(self.r / dbu))
        g = int(round(self.g / dbu))
        Lc = int(round(self.Lc / dbu))

        # draw the half-circle
        x = 0
        y = r + w + g
        self.cell.shapes(LayerSiN).insert(arc_wg_xy(x - Lc / 2, y, r, w, 180, 270))
        self.cell.shapes(LayerSiN).insert(arc_wg_xy(x + Lc / 2, y, r, w, 270, 360))

        # Pins on the top side:
        pin = Path([Point(-r - Lc / 2, y - PIN_LENGTH / 2),
                    Point(-r - Lc / 2, y + PIN_LENGTH / 2)], w)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, -r - Lc / 2, y)
        text = Text("pin2", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        pin = Path([Point(r + Lc / 2, y - PIN_LENGTH / 2),
                    Point(r + Lc / 2, y + PIN_LENGTH / 2)], w)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, r + Lc / 2, y)
        text = Text("pin4", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        if Lc > 0:
            wg1 = Box(-Lc / 2, -w / 2 + w + g, Lc / 2, w / 2 + w + g)
            shapes(LayerSiN).insert(wg1)

        # Create the waveguide
        wg1 = Box(-r - w / 2 - w - Lc / 2, -w / 2, r + w / 2 + w + Lc / 2, w / 2)
        shapes(LayerSiN).insert(wg1)

        # Pins on the bus waveguide side:
        pin = Path([Point(-r - w / 2 - w + PIN_LENGTH / 2 - Lc / 2, 0),
                    Point(-r - w / 2 - w - PIN_LENGTH / 2 - Lc / 2, 0)], w)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, -r - w / 2 - w - Lc / 2, 0)
        text = Text("pin1", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        pin = Path([Point(r + w / 2 + w - PIN_LENGTH / 2 + Lc / 2, 0),
                    Point(r + w / 2 + w + PIN_LENGTH / 2 + Lc / 2, 0)], w)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, r + w / 2 + w + Lc / 2, 0)
        text = Text("pin3", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Merge all the waveguide shapes, to avoid any small gaps
        layer_temp = self.layout.layer(LayerInfo(913, 0))
        shapes_temp = self.cell.shapes(layer_temp)
        ShapeProcessor().merge(self.layout, self.cell, LayerSiN, shapes_temp, True, 0, True, True)
        self.cell.shapes(LayerSiN).clear()
        shapes_SiN = self.cell.shapes(LayerSiN)
        ShapeProcessor().merge(self.layout, self.cell, layer_temp, shapes_SiN, True, 0, True, True)
        self.cell.shapes(layer_temp).clear()

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        dev = Box(-r - w / 2 - w - Lc / 2, -w / 2 - w, r + w / 2 + w + Lc / 2, y)
        shapes(LayerDevRecN).insert(dev)

        # Compact model information
        t = Trans(Trans.R0, r / 4, 0)
        text = Text("Lumerical_INTERCONNECT_library=Design kits/ebeam", t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = self.r * 0.017 / dbu
        t = Trans(Trans.R0, r / 4, r / 4)
        text = Text('Component=ebeam_dc_halfring_straight', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = self.r * 0.017 / dbu
        t = Trans(Trans.R0, r / 4, r / 2)

        text = Text('Spice_param:wg_width=%.3fu gap=%.3fu radius=%.3fu Lc=%.3fu orthogonal_identifier=%s' % (
            self.w, self.g, self.r, self.Lc, self.orthogonal_identifier), t)

        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = self.r * 0.017 / dbu

        print("Done drawing the layout for - ebeam_dc_halfring_straight: %.3f-%g" % (self.r, self.g))


class Waveguide_SBend(PCellDeclarationHelper):
    """
    Input:
    """

    def __init__(self):

        # Important: initialize the super class
        super(Waveguide_SBend, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("length", self.TypeDouble, "Waveguide length", default=10.0)
        self.param("height", self.TypeDouble, "Waveguide offset height", default=2)
        self.param("wg_width", self.TypeDouble, "Waveguide width (microns)", default=0.5)
        self.param("radius", self.TypeDouble, "Waveguide bend radius (microns)", default=5)
        self.param("layer", self.TypeLayer, "Layer", default=TECHNOLOGY['Si'])
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Waveguide_SBend_%s-%.3f" % \
            (self.length, self.wg_width)

    def coerce_parameters_impl(self):
        pass

    def can_create_from_shape(self, layout, shape, layer):
        return False

    def produce_impl(self):

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout
        shapes = self.cell.shapes

        from SiEPIC.utils import points_per_circle

        LayerSi = self.layer
        LayerSiN = ly.layer(LayerSi)
        #LayerSiSPN = ly.layer(LayerSiSP)
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)
        LayerTextN = ly.layer(get_technology()['Text'])

        from math import pi, cos, sin, log, sqrt, acos

        length = self.length / dbu
        w = self.wg_width / dbu
        r = self.radius / dbu
        h = self.height / dbu
        theta = acos((r - abs(h / 2)) / r) * 180 / pi
        x = 2 * r * sin(theta / 180.0 * pi)
        straight_l = (length - x) / 2

        # define the cell origin as the left side of the waveguide sbend

        if (straight_l >= 0):
            circle_fraction = abs(theta) / 360.0
            npoints = int(points_per_circle(r) * circle_fraction)
            if npoints == 0:
                npoints = 1
            da = 2 * pi / npoints * circle_fraction  # increment, in radians
            x1 = straight_l
            x2 = length - straight_l

            if h > 0:
                y1 = r
                theta_start1 = 270
                y2 = h - r
                theta_start2 = 90
                pts = []
                th1 = theta_start1 / 360.0 * 2 * pi
                th2 = theta_start2 / 360.0 * 2 * pi
                pts.append(Point.from_dpoint(DPoint(0, w / 2)))
                pts.append(Point.from_dpoint(DPoint(0, -w / 2)))
                for i in range(0, npoints + 1):  # lower left
                    pts.append(Point.from_dpoint(
                        DPoint((x1 + (r + w / 2) * cos(i * da + th1)) / 1, (y1 + (r + w / 2) * sin(i * da + th1)) / 1)))
                for i in range(npoints, -1, -1):  # lower right
                    pts.append(Point.from_dpoint(
                        DPoint((x2 + (r - w / 2) * cos(i * da + th2)) / 1, (y2 + (r - w / 2) * sin(i * da + th2)) / 1)))
                pts.append(Point.from_dpoint(DPoint(length, h - w / 2)))
                pts.append(Point.from_dpoint(DPoint(length, h + w / 2)))
                for i in range(0, npoints + 1):  # upper right
                    pts.append(Point.from_dpoint(
                        DPoint((x2 + (r + w / 2) * cos(i * da + th2)) / 1, (y2 + (r + w / 2) * sin(i * da + th2)) / 1)))
                for i in range(npoints, -1, -1):  # upper left
                    pts.append(Point.from_dpoint(
                        DPoint((x1 + (r - w / 2) * cos(i * da + th1)) / 1, (y1 + (r - w / 2) * sin(i * da + th1)) / 1)))
                self.cell.shapes(LayerSiN).insert(Polygon(pts))
            else:
                y1 = -r
                theta_start1 = 90 - theta
                y2 = r + h
                theta_start2 = 270 - theta
                pts = []
                th1 = theta_start1 / 360.0 * 2 * pi
                th2 = theta_start2 / 360.0 * 2 * pi
                pts.append(Point.from_dpoint(DPoint(length, h - w / 2)))
                pts.append(Point.from_dpoint(DPoint(length, h + w / 2)))
                for i in range(npoints, -1, -1):  # upper right
                    pts.append(Point.from_dpoint(
                        DPoint((x2 + (r - w / 2) * cos(i * da + th2)) / 1, (y2 + (r - w / 2) * sin(i * da + th2)) / 1)))
                for i in range(0, npoints + 1):  # upper left
                    pts.append(Point.from_dpoint(
                        DPoint((x1 + (r + w / 2) * cos(i * da + th1)) / 1, (y1 + (r + w / 2) * sin(i * da + th1)) / 1)))
                pts.append(Point.from_dpoint(DPoint(0, w / 2)))
                pts.append(Point.from_dpoint(DPoint(0, -w / 2)))
                for i in range(npoints, -1, -1):  # lower left
                    pts.append(Point.from_dpoint(
                        DPoint((x1 + (r - w / 2) * cos(i * da + th1)) / 1, (y1 + (r - w / 2) * sin(i * da + th1)) / 1)))
                for i in range(0, npoints + 1):  # lower right
                    pts.append(Point.from_dpoint(
                        DPoint((x2 + (r + w / 2) * cos(i * da + th2)) / 1, (y2 + (r + w / 2) * sin(i * da + th2)) / 1)))
                self.cell.shapes(LayerSiN).insert(Polygon(pts))

        waveguide_length = (2 * pi * r * (2 * theta / 360.0) + straight_l * 2) * dbu

        from math import pi, cos, sin
        from SiEPIC.utils import arc_wg, arc_wg_xy
        from SiEPIC._globals import PIN_LENGTH as pin_length

        # Pins on the waveguide:
        x = self.length / dbu
        t = Trans(Trans.R0, x, h)
        pin = Path([Point(-pin_length / 2, 0), Point(pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin2", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        x = 0
        t = Trans(Trans.R0, x, 0)
        pin = Path([Point(pin_length / 2, 0), Point(-pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin1", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Compact model information
        t = Trans(Trans.R0, 0, 0)
        text = Text('Lumerical_INTERCONNECT_library=Design kits/EBeam', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, 0, w * 2)
        text = Text('Component=ebeam_wg_integral_1550', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, 0, -w * 2)
        text = Text \
            ('Spice_param:wg_length=%.3fu wg_width=%.3fu' %
             (waveguide_length, self.wg_width), t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        box1 = Box(0, min(-w * 3, h - w * 3), length, max(w * 3, h + w * 3))
        shapes(LayerDevRecN).insert(box1)


class Waveguide_bump(PCellDeclarationHelper):
    """
    Input:
    """

    def __init__(self):

        # Important: initialize the super class
        super(Waveguide_bump, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("length", self.TypeDouble, "Regular Waveguide length", default=10.0)
# Ideally we would just specify the delta, and the function would solve the transcendental equation.
#    self.param("delta_length", self.TypeDouble, "Extra Waveguide length", default = 10.0)
# for now, let the user specify the unknown theta
        self.param("theta", self.TypeDouble, "Waveguide angle (degrees)", default=5)
        self.param("wg_width", self.TypeDouble, "Waveguide width (microns)", default=0.5)
        self.param("waveguide", self.TypeLayer, "Waveguide Layer", default=TECHNOLOGY['Si'])
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])
        self.param("text", self.TypeLayer, "Text Layer", default=LayerInfo(10, 0))

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Waveguide_bump_%s-%.3f" % \
            (self.length, self.wg_width)

    def coerce_parameters_impl(self):
        pass

    def can_create_from_shape(self, layout, shape, layer):
        return False

    def produce_impl(self):

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout
        shapes = self.cell.shapes

        LayerSiN = ly.layer(self.waveguide)
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)
        LayerTextN = ly.layer(self.text)

        from math import pi, cos, sin, log, sqrt
        from SiEPIC.utils import arc, arc_to_waveguide, points_per_circle, arc_wg

        x = 0
        y = 0
        theta = self.theta
#    2*pi*r*(4*theta/360) = length + self.delta_length

        from SiEPIC.extend import to_itype
        w = to_itype(self.wg_width, dbu)
        length = to_itype(self.length, dbu)
        r = length / 4 / sin(theta / 180.0 * pi)
        waveguide_length = 2 * pi * r * (4 * theta / 360.0)

        # arc_to_waveguide(pts, width):
        #arc(radius, start, stop)
        t = Trans(Trans.R0, x, round(y + r))
        self.cell.shapes(LayerSiN).insert(arc_wg(r, w, 270., 270. + theta).transformed(t))

        t = Trans(Trans.R0, round(x + length / 2),
                  round(y - r + 2 * r * (1 - cos(theta / 180.0 * pi))))
        self.cell.shapes(LayerSiN).insert(arc_wg(r, w, 90. - theta, 90. + theta).transformed(t))

        t = Trans(Trans.R0, round(x + length), round(y + r))
        self.cell.shapes(LayerSiN).insert(arc_wg(r, w, 270. - theta, 270).transformed(t))

        # Create the pins on the waveguides, as short paths:
        from SiEPIC._globals import PIN_LENGTH as pin_length
        x = self.length / dbu
        t = Trans(Trans.R0, x, 0)
        pin = Path([Point(-pin_length / 2, 0), Point(pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin2", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        x = 0
        t = Trans(Trans.R0, x, 0)
        pin = Path([Point(pin_length / 2, 0), Point(-pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin1", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Compact model information
        t = Trans(Trans.R0, 0, 0)
        text = Text('Lumerical_INTERCONNECT_library=Design kits/ebeam', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, 0, w * 2)
        text = Text('Component=ebeam_wg_integral_1550', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, 0, -w * 2)
        text = Text \
            ('Spice_param:wg_length=%.3fu wg_width=%.3fu' %
             (waveguide_length * dbu, self.wg_width), t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu

        t = Trans(Trans.R0, self.length / 6, -w * 2)
        text = Text('dL = %.4f um' % ((waveguide_length - length) * dbu), t)
        shape = shapes(LayerTextN).insert(text)
        shape.text_size = 0.6 / dbu

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        box1 = Box(0, -w * 3, length, w * 3 + (2 * r * (1 - cos(theta / 180.0 * pi))))
        shapes(LayerDevRecN).insert(box1)

        print("SiEPIC EBeam: Waveguide_bump complete.")


def layout_pgtext(cell, layer, x, y, text, mag):
        # example usage:
        # cell = Application.instance().main_window().current_view().active_cellview().cell
        # layout_pgtext(cell, LayerInfo(10, 0), 0, 0, "test", 1)

        # for the Text polygon:
    textlib = Library.library_by_name("Basic")
    if textlib == None:
        raise Exception("Unknown lib 'Basic'")

    textpcell_decl = textlib.layout().pcell_declaration("TEXT")
    if textpcell_decl == None:
        raise Exception("Unknown PCell 'TEXT'")
    param = {
        "text": text,
        "layer": layer,
        "mag": mag
    }
    pv = []
    for p in textpcell_decl.get_parameters():
        if p.name in param:
            pv.append(param[p.name])
        else:
            pv.append(p.default)
    # "fake PCell code"
    text_cell = cell.layout().create_cell("Temp_text_cell")
    textlayer_index = cell.layout().layer(layer)
    textpcell_decl.produce(cell.layout(), [textlayer_index], pv, text_cell)

    # fetch the database parameters
    dbu = cell.layout().dbu
    t = Trans(Trans.R0, x / dbu, y / dbu)
    cell.insert(CellInstArray(text_cell.cell_index(), t))
    # flatten and delete polygon text cell
    cell.flatten(True)

    print("Done layout_pgtext")


class Waveguide_Bend(PCellDeclarationHelper):
    """
    The PCell declaration for the waveguide bend.
    """

    def __init__(self):

        # Important: initialize the super class
        super(Waveguide_Bend, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("silayer", self.TypeLayer, "Si Layer", default=TECHNOLOGY['Si'])
        self.param("radius", self.TypeDouble, "Radius", default=10)
        self.param("wg_width", self.TypeDouble, "Waveguide Width", default=0.5)
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])
        # hidden parameters, can be used to query this component:
        self.param("p1", self.TypeShape, "DPoint location of pin1",
                   default=Point(-10000, 0), hidden=True, readonly=True)
        self.param("p2", self.TypeShape, "DPoint location of pin2",
                   default=Point(0, 10000), hidden=True, readonly=True)

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Waveguide_Bend(R=" + ('%.3f' % self.radius) + ")"

    def can_create_from_shape_impl(self):
        return False

    def produce(self, layout, layers, parameters, cell):
        """
        coerce parameters (make consistent)
        """
        self._layers = layers
        self.cell = cell
        self._param_values = parameters
        self.layout = layout

        # cell: layout cell to place the layout
        # LayerSiN: which layer to use
        # r: radius
        # w: waveguide width
        # length units in dbu

        from math import pi, cos, sin
        from SiEPIC.utils import arc, arc_to_waveguide, points_per_circle, arc_wg

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout
        shapes = self.cell.shapes

        LayerSi = self.silayer
        LayerSiN = self.silayer_layer
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)

        w = int(round(self.wg_width / dbu))
        r = int(round(self.radius / dbu))

        # draw the quarter-circle
        x = -r
        y = r
       # layout_arc_wg_dbu(self.cell, LayerSiN, x, y, r, w, 270, 360)
        t = Trans(Trans.R0, x, y)
        self.cell.shapes(LayerSiN).insert(arc_to_waveguide(arc(r, 270, 360), w).transformed(t))

        # Create the pins on the waveguides, as short paths:
        from SiEPIC._globals import PIN_LENGTH as pin_length

        # Pin on the top side:
        p2 = [Point(0, y - pin_length / 2), Point(0, y + pin_length / 2)]
        p2c = Point(0, y)
        self.set_p2 = p2c
        self.p2 = p2c
        pin = Path(p2, w)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, 0, y)
        text = Text("pin2", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Pin on the left side:
        p1 = [Point(pin_length / 2 + x, 0), Point(-pin_length / 2 + x, 0)]
        p1c = Point(x, 0)
        self.set_p1 = p1c
        self.p1 = p1c
        pin = Path(p1, w)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, x, 0)
        text = Text("pin1", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        t = Trans(Trans.R0, x, y)
        self.cell.shapes(LayerDevRecN).insert(
            arc_to_waveguide(arc(r, 270, 360), w * 3).transformed(t))
        #layout_arc_wg_dbu(self.cell, LayerDevRecN, x, y, r, w*3, 270, 360)

        # Compact model information
        t = Trans(Trans.R0, x + r / 10, 0)
        text = Text("Lumerical_INTERCONNECT_library=Design kits/EBeam", t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = r / 100
        t = Trans(Trans.R0, x + r / 10, r / 4)
        text = Text('Component=ebeam_bend_1550', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = r / 100
        t = Trans(Trans.R0, x + r / 10, r / 2)
        text = Text('Spice_param:radius=%.3fu wg_width=%.3fu' % (self.radius, self.wg_width), t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = r / 100


class ebeam_bragg_te1550(PCellDeclarationHelper):
    """
    Input: length, width
    """

    def __init__(self):

        # Important: initialize the super class
        super(ebeam_bragg_te1550, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("number_of_periods", self.TypeInt, "Number of grating periods", default=300)
        self.param("grating_period", self.TypeDouble, "Grating period (microns)", default=0.317)
        self.param("corrugation_width", self.TypeDouble,
                   "Corrugration width (microns)", default=0.05)
        self.param("misalignment", self.TypeDouble, "Grating misalignment (microns)", default=0.0)
        self.param("sinusoidal", self.TypeBoolean,
                   "Grating Type (Rectangular=False, Sinusoidal=True)", default=False)
        self.param("wg_width", self.TypeDouble, "Waveguide width", default=0.5)
        self.param("layer", self.TypeLayer, "Layer", default=TECHNOLOGY['Waveguide'])
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])
#    self.param("textl", self.TypeLayer, "Text Layer", default = LayerInfo(10, 0))

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "ebeam_bragg_te1550_%s-%.3f-%.3f-%.3f" % \
            (self.number_of_periods, self.grating_period, self.corrugation_width, self.misalignment)

    def coerce_parameters_impl(self):
        pass

    def can_create_from_shape(self, layout, shape, layer):
        return False

    def produce_impl(self):

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout
        shapes = self.cell.shapes

        LayerSi = self.layer
        LayerSiN = ly.layer(LayerSi)
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)

        from SiEPIC.extend import to_itype

        # Draw the Bragg grating:
        box_width = self.grating_period / 2 / dbu
        grating_period = self.grating_period / dbu
        w = to_itype(self.wg_width, dbu)
        half_w = w / 2
        half_corrugation_w = self.corrugation_width / 2 / dbu
        misalignment = int(self.misalignment / dbu)
        if self.sinusoidal:
            npoints_sin = 40
            for i in range(0, self.number_of_periods):
                x = ((i * self.grating_period) / dbu)
                box1 = Box(x, 0, x + box_width, half_w + half_corrugation_w)
                pts1 = [Point(x, 0)]
                pts3 = [Point(x + misalignment, 0)]
                for i1 in range(0, npoints_sin + 1):
                    x1 = i1 * 2 * math.pi / npoints_sin
                    y1 = half_corrugation_w * math.sin(x1)
                    x1 = x1 / 2 / math.pi * grating_period
#          print("x: %s, y: %s" % (x1,y1))
                    pts1.append(Point(x + x1, half_w + y1))
                    pts3.append(Point(x + misalignment + x1, -half_w - y1))
                pts1.append(Point(x + grating_period, 0))
                pts3.append(Point(x + grating_period + misalignment, 0))
                shapes(LayerSiN).insert(Polygon(pts1))
                shapes(LayerSiN).insert(Polygon(pts3))
            length = x + grating_period + misalignment
            if misalignment > 0:
                # extra piece at the end:
                box2 = Box(x + grating_period, 0, length, half_w)
                shapes(LayerSiN).insert(box2)
                # extra piece at the beginning:
                box3 = Box(0, 0, misalignment, -half_w)
                shapes(LayerSiN).insert(box3)

        else:
            for i in range(0, self.number_of_periods):
                x = (i * self.grating_period) / dbu
                box1 = Box(x, 0, x + box_width, half_w + half_corrugation_w)
                box2 = Box(x + box_width, 0, x + grating_period, half_w - half_corrugation_w)
                box3 = Box(x + misalignment, 0, x + box_width +
                           misalignment, -half_w - half_corrugation_w)
                box4 = Box(x + box_width + misalignment, 0, x + grating_period +
                           misalignment, -half_w + half_corrugation_w)
                shapes(LayerSiN).insert(box1)
                shapes(LayerSiN).insert(box2)
                shapes(LayerSiN).insert(box3)
                shapes(LayerSiN).insert(box4)
            length = x + grating_period + misalignment
            if misalignment > 0:
                # extra piece at the end:
                box2 = Box(x + grating_period, 0, length, half_w)
                shapes(LayerSiN).insert(box2)
                # extra piece at the beginning:
                box3 = Box(0, 0, misalignment, -half_w)
                shapes(LayerSiN).insert(box3)

        # Create the pins on the waveguides, as short paths:
        from SiEPIC._globals import PIN_LENGTH as pin_length

        t = Trans(Trans.R0, 0, 0)
        pin = Path([Point(pin_length / 2, 0), Point(-pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin1", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        t = Trans(Trans.R0, length, 0)
        pin = Path([Point(-pin_length / 2, 0), Point(pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin2", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Compact model information
        t = Trans(Trans.R0, 0, 0)
        text = Text('Lumerical_INTERCONNECT_library=Design kits/ebeam', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, length / 10, 0)
        text = Text('Component=ebeam_bragg_te1550', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, length / 9, 0)
        text = Text \
            ('Spice_param:number_of_periods=%s grating_period=%.3fu corrugation_width=%.3fu misalignment=%.3fu sinusoidal=%s' %
             (self.number_of_periods, self.grating_period, self.corrugation_width, self.misalignment, int(self.sinusoidal)), t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        t = Trans(Trans.R0, 0, 0)
        path = Path([Point(0, 0), Point(length, 0)], 3 * w)
        shapes(LayerDevRecN).insert(path.simple_polygon())


class ebeam_taper_te1550(PCellDeclarationHelper):
    """
    The PCell declaration for the strip waveguide taper.
    """

    def __init__(self):

        # Important: initialize the super class
        super(ebeam_taper_te1550, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("silayer", self.TypeLayer, "Si Layer", default=TECHNOLOGY['Si'])
        self.param("wg_width1", self.TypeDouble,
                   "Waveguide Width1 (CML only supports 0.4, 0.5, 0.6)", default=0.5)
        self.param("wg_width2", self.TypeDouble,
                   "Waveguide Width2 (CML only supports 1, 2, 3)", default=3)
        self.param("wg_length", self.TypeDouble,
                   "Waveguide Length (CML only supports a range of 1-10)", default=10)
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])
        # hidden parameters, can be used to query this component:
        self.param("p1", self.TypeShape, "DPoint location of pin1",
                   default=Point(-10000, 0), hidden=True, readonly=True)
        self.param("p2", self.TypeShape, "DPoint location of pin2",
                   default=Point(0, 10000), hidden=True, readonly=True)

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "ebeam_taper_te1550(R=" + ('%.3f-%.3f-%.3f' % (self.wg_width1, self.wg_width2, self.wg_length)) + ")"

    def can_create_from_shape_impl(self):
        return False

    def produce(self, layout, layers, parameters, cell):
        """
        coerce parameters (make consistent)
        """
        self._layers = layers
        self.cell = cell
        self._param_values = parameters
        self.layout = layout
        shapes = self.cell.shapes

        # cell: layout cell to place the layout
        # LayerSiN: which layer to use
        # w: waveguide width
        # length units in dbu

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout

        LayerSi = self.silayer
        LayerSiN = self.silayer_layer
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)

        w1 = int(round(self.wg_width1 / dbu))
        w2 = int(round(self.wg_width2 / dbu))
        length = int(round(self.wg_length / dbu))

        pts = [Point(0, -w1 / 2), Point(0, w1 / 2), Point(length, w2 / 2), Point(length, -w2 / 2)]
        shapes(LayerSiN).insert(Polygon(pts))

        # Create the pins on the waveguides, as short paths:
        from SiEPIC._globals import PIN_LENGTH as pin_length

        # Pin on the left side:
        p1 = [Point(pin_length / 2, 0), Point(-pin_length / 2, 0)]
        p1c = Point(0, 0)
        self.set_p1 = p1c
        self.p1 = p1c
        pin = Path(p1, w1)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, 0, 0)
        text = Text("pin1", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Pin on the right side:
        p2 = [Point(length - pin_length / 2, 0), Point(length + pin_length / 2, 0)]
        p2c = Point(length, 0)
        self.set_p2 = p2c
        self.p2 = p2c
        pin = Path(p2, w2)
        shapes(LayerPinRecN).insert(pin)
        t = Trans(Trans.R0, length, 0)
        text = Text("pin2", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        path = Path([Point(0, 0), Point(length, 0)], w2 + w1 * 2)
        shapes(LayerDevRecN).insert(path.simple_polygon())

        # Compact model information
        t = Trans(Trans.R0, w1 / 10, 0)
        text = Text("Lumerical_INTERCONNECT_library=Design kits/ebeam", t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = length / 100
        t = Trans(Trans.R0, length / 10, w1 / 4)
        text = Text('Component=ebeam_taper_te1550', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = length / 100
        t = Trans(Trans.R0, length / 10, w1 / 2)
        text = Text('Spice_param:wg_width1=%.3fu wg_width2=%.3fu wg_length=%.3fu' %
                    (self.wg_width1, self.wg_width2, self.wg_length), t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = length / 100

        return "ebeam_taper_te1550(" + ('%.3f-%.3f-%.3f' % (self.wg_width1, self.wg_width2, self.wg_length)) + ")"


class Waveguide_Straight(PCellDeclarationHelper):
    """
    Input: length, width
    draws a straight waveguide with pins. centred at the instantiation point.
    Usage: instantiate, and use transformations (rotation)
    """

    def __init__(self):

        # Important: initialize the super class
        super(Waveguide_Straight, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("wg_length", self.TypeInt, "Waveguide Length", default=10000)
        self.param("wg_width", self.TypeInt, "Waveguide width", default=500)
        self.param("layer", self.TypeLayer, "Layer", default=TECHNOLOGY['Si'])
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Waveguide_Straight_%.3f-%.3f" % (self.wg_length / 1000, self.wg_width / 1000)

    def coerce_parameters_impl(self):
        pass

    def can_create_from_shape(self, layout, shape, layer):
        return False

    def produce_impl(self):
        ly = self.layout
        LayerSiN = ly.layer(self.layer)
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout
        shapes = self.cell.shapes

        LayerSi = self.layer
        LayerSiN = ly.layer(LayerSi)
        #LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)

#    print("Waveguide_Straight:")
        w = self.wg_width
        length = self.wg_length
        points = [[-length / 2, 0], [length / 2, 0]]
        path = Path([Point(-length / 2, 0), Point(length / 2, 0)], w)
#    print(path)

        shapes(LayerSiN).insert(path.simple_polygon())

        from SiEPIC._globals import PIN_LENGTH

        # Pins on the bus waveguide side:
        pin_length = PIN_LENGTH
        if length < pin_length + 1:
            pin_length = int(length / 3)
            pin_length = math.ceil(pin_length / 2.) * 2
        if pin_length == 0:
            pin_length = 2

        t = Trans(Trans.R0, -length / 2, 0)
        pin = Path([Point(pin_length / 2, 0), Point(-pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin1", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        t = Trans(Trans.R0, length / 2, 0)
        pin = Path([Point(-pin_length / 2, 0), Point(pin_length / 2, 0)], w)
        pin_t = pin.transformed(t)
        shapes(LayerPinRecN).insert(pin_t)
        text = Text("pin2", t)
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Compact model information
        t = Trans(Trans.R0, 0, 0)
        text = Text('Lumerical_INTERCONNECT_library=Design kits/EBeam', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, length / 10, 0)
        text = Text('Lumerical_INTERCONNECT_component=ebeam_wg_integral_1550', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu
        t = Trans(Trans.R0, length / 9, 0)
        text = Text('Spice_param:wg_width=%.3fu wg_length=%.3fu' %
                    (self.wg_width * dbu, self.wg_length * dbu), t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = 0.1 / dbu

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        path = Path([Point(-length / 2, 0), Point(length / 2, 0)], w * 3)
        shapes(LayerDevRecN).insert(path.simple_polygon())


class ebeam_dc_te1550(PCellDeclarationHelper):
    """
    The PCell declaration for the Directional Coupler
    by Lukas Chrostowski, 2018/09
    compact model in INTERCONNECT based on:
     - https://kx.lumerical.com/t/lcml-directional-coupler-based-on-lookup-table-lcml-dc-strip-1550-lookuptable/2094
     - only parameterized for Lc, for the 500 x 220 nm waveguide with 200 nm gap, and 5 micron radius
     could be improved:
     - https://kx.lumerical.com/t/lcml-directional-coupler-based-on-analytical-functions-lcml-dc-strip-1550-analytical/2091

    """

    def __init__(self):

        # Important: initialize the super class
        super(ebeam_dc_te1550, self).__init__()
        TECHNOLOGY = get_technology_by_name('EBeam')

        # declare the parameters
        self.param("Lc", self.TypeDouble, "Coupler Length", default=10.0)
        self.param("silayer", self.TypeLayer, "Si Layer", default=[TECHNOLOGY['Waveguide']])
        self.param("pinrec", self.TypeLayer, "PinRec Layer", default=TECHNOLOGY['PinRec'])
        self.param("devrec", self.TypeLayer, "DevRec Layer", default=TECHNOLOGY['DevRec'])
        self.param("textl", self.TypeLayer, "Text Layer", default=LayerInfo(10, 0))

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "ebeam_dc_te1550(Lc=" + ('%.3f' % self.Lc) + ")"

    def can_create_from_shape_impl(self):
        return False

    def produce_impl(self):
        # This is the main part of the implementation: create the layout

        # Fixed PCell parameters
        # spacing of the two ports, determines the angle required by the s-bend.
        port_spacing = 2000
        r = 5000  # radius
        w = 500  # waveguide width
        g = 200  # gap

        from math import pi, cos, sin, acos
        from SiEPIC.utils import arc_wg, arc_wg_xy
        from SiEPIC._globals import PIN_LENGTH

        # fetch the parameters
        dbu = self.layout.dbu
        ly = self.layout
        shapes = self.cell.shapes
        LayerSiN = ly.layer(self.silayer)
        LayerPinRecN = ly.layer(self.pinrec)
        LayerDevRecN = ly.layer(self.devrec)
        TextLayerN = ly.layer(self.textl)

        Lc = int(round(self.Lc / dbu))

        # Create the parallel waveguides
        if Lc > 0:
            wg1 = Box(-Lc / 2, -w / 2 + (w + g) / 2, Lc / 2, w / 2 + (w + g) / 2)
            shapes(LayerSiN).insert(wg1)
            wg1 = Box(-Lc / 2, -w / 2 - (w + g) / 2, Lc / 2, w / 2 - (w + g) / 2)
            shapes(LayerSiN).insert(wg1)

        dc_angle = acos((r - abs(port_spacing / 2)) / r) * 180 / pi

        # bottom S-bends
        self.cell.shapes(LayerSiN).insert(
            arc_wg_xy(Lc / 2, -r - (w + g) / 2, r, w, 90 - dc_angle, 90))
        self.cell.shapes(LayerSiN).insert(
            arc_wg_xy(-Lc / 2, -r - (w + g) / 2, r, w, 90, 90 + dc_angle))
        y_bottom = round(-2 * (1 - cos(dc_angle / 180.0 * pi)) * r) - (w + g) / 2
        x_bottom = round(2 * sin(dc_angle / 180.0 * pi) * r)
        t = Trans(Trans.R0, -x_bottom - Lc / 2, y_bottom + r)
        self.cell.shapes(LayerSiN).insert(arc_wg(r, w, -90, -90 + dc_angle).transformed(t))
        t = Trans(Trans.R0, x_bottom + Lc / 2, y_bottom + r)
        self.cell.shapes(LayerSiN).insert(arc_wg(r, w, -90 - dc_angle, -90).transformed(t))

        # top S-bends
        self.cell.shapes(LayerSiN).insert(
            arc_wg_xy(Lc / 2, r + (w + g) / 2, r, w, 270, 270 + dc_angle))
        self.cell.shapes(LayerSiN).insert(
            arc_wg_xy(-Lc / 2, r + (w + g) / 2, r, w, 270 - dc_angle, 270))
        y_top = round(2 * (1 - cos(dc_angle / 180.0 * pi)) * r) + (w + g) / 2
        x_top = round(2 * sin(dc_angle / 180.0 * pi) * r)
        t = Trans(Trans.R0, -x_top - Lc / 2, y_top - r)
        self.cell.shapes(LayerSiN).insert(arc_wg(r, w, 90 - dc_angle, 90).transformed(t))
        t = Trans(Trans.R0, x_top + Lc / 2, y_top - r)
        self.cell.shapes(LayerSiN).insert(arc_wg(r, w, 90, 90 + dc_angle).transformed(t))

        # Pins on the bottom waveguide side:
        pin = Path([Point(-x_bottom + PIN_LENGTH / 2 - Lc / 2, y_bottom),
                    Point(-x_bottom - PIN_LENGTH / 2 - Lc / 2, y_bottom)], w)
        shapes(LayerPinRecN).insert(pin)
        text = Text("pin1", Trans(Trans.R0, -x_bottom - Lc / 2, y_bottom))
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        pin = Path([Point(x_bottom - PIN_LENGTH / 2 + Lc / 2, y_bottom),
                    Point(x_bottom + PIN_LENGTH / 2 + Lc / 2, y_bottom)], w)
        shapes(LayerPinRecN).insert(pin)
        text = Text("pin3", Trans(Trans.R0, x_bottom + Lc / 2, y_bottom))
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Pins on the top waveguide side:
        pin = Path([Point(-x_bottom + PIN_LENGTH / 2 - Lc / 2, y_top),
                    Point(-x_bottom - PIN_LENGTH / 2 - Lc / 2, y_top)], w)
        shapes(LayerPinRecN).insert(pin)
        text = Text("pin2", Trans(Trans.R0, -x_bottom - Lc / 2, y_top))
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        pin = Path([Point(x_bottom - PIN_LENGTH / 2 + Lc / 2, y_top),
                    Point(x_bottom + PIN_LENGTH / 2 + Lc / 2, y_top)], w)
        shapes(LayerPinRecN).insert(pin)
        text = Text("pin4", Trans(Trans.R0, x_bottom + Lc / 2, y_top))
        shape = shapes(LayerPinRecN).insert(text)
        shape.text_size = 0.4 / dbu

        # Merge all the waveguide shapes, to avoid any small gaps
        layer_temp = self.layout.layer(LayerInfo(913, 0))
        shapes_temp = self.cell.shapes(layer_temp)
        ShapeProcessor().merge(self.layout, self.cell, LayerSiN, shapes_temp, True, 0, True, True)
        self.cell.shapes(LayerSiN).clear()
        shapes_SiN = self.cell.shapes(LayerSiN)
        ShapeProcessor().merge(self.layout, self.cell, layer_temp, shapes_SiN, True, 0, True, True)
        self.cell.shapes(layer_temp).clear()

        # Create the device recognition layer -- make it 1 * wg_width away from the waveguides.
        dev = Box(-x_bottom - Lc / 2, y_bottom - w / 2 - w, x_bottom + Lc / 2, y_top + w / 2 + w)
        shapes(LayerDevRecN).insert(dev)

        # Compact model information
        t = Trans(Trans.R0, 0, -w)
        text = Text("Lumerical_INTERCONNECT_library=Design kits/ebeam", t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = r * 0.017
        t = Trans(Trans.R0, 0, 0)
        text = Text('Component=ebeam_dc_te1550', t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = r * 0.017
        t = Trans(Trans.R0, 0, w)
        text = Text('Spice_param:wg_width=%.3fu gap=%.3fu radius=%.3fu Lc=%.3fu' %
                    (w * dbu, g * dbu, r * dbu, self.Lc), t)
        shape = shapes(LayerDevRecN).insert(text)
        shape.text_size = r * 0.017

        print("Done drawing the layout for - ebeam_dc_te1550: %.3f" % (self.Lc))


class SiEPIC_EBeam(Library):
    """
    The library where we will put the PCells and GDS into
    """

    def __init__(self):

        tech_name = 'EBeam'
        library = tech_name
#    library = 'SiEPIC-'+tech_name

        print("Initializing '%s' Library." % library)

        # Set the description
# windows only allows for a fixed width, short description
        self.description = ""
# OSX does a resizing:
        self.description = "Components with models"

        # Import all the GDS files from the tech folder "gds"
        import os
        import fnmatch
        dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../tech/EBeam/gds/mature")
        search_str = '*' + '.gds'
        for root, dirnames, filenames in os.walk(dir_path, followlinks=True):
            for filename in fnmatch.filter(filenames, search_str):
                file1 = os.path.join(root, filename)
                print(" - reading %s" % file1)
                self.layout().read(file1)

        # Create the PCell declarations

        self.layout().register_pcell("ebeam_dc_te1550", ebeam_dc_te1550())
        self.layout().register_pcell("ebeam_dc_halfring_straight", ebeam_dc_halfring_straight())
        self.layout().register_pcell("ebeam_bragg_te1550", ebeam_bragg_te1550())
        self.layout().register_pcell("ebeam_taper_te1550", ebeam_taper_te1550())
        self.layout().register_pcell("Waveguide_bump", Waveguide_bump())
        self.layout().register_pcell("Waveguide_SBend", Waveguide_SBend())
        self.layout().register_pcell("Waveguide_Bend", Waveguide_Bend())
        self.layout().register_pcell("Waveguide_Straight", Waveguide_Straight())
        self.layout().register_pcell("Waveguide", Waveguide())

        # Register us the library with the technology name
        # If a library with that name already existed, it will be replaced then.
        self.register(library)

        # self.register('SiEPIC-EBeam')

        # if int(Application.instance().version().split('.')[1]) > 24:
        #     # KLayout v0.25 introduced technology variable:
        #     self.technology = tech_name

        # Assuming klayout v0.25 or above
        self.technology = tech_name

# # Instantiate and register the library
# SiEPIC_EBeam()