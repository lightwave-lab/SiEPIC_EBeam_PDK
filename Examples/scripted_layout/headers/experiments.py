from siepic_tools.utils.geometry import Port, \
    manhattan_intersection
from siepic_tools.utils.pcells import port_to_pin_helper, place_cell
from siepic_tools.utils.pcells import CellWithPosition
from siepic_tools.utils.layout import  \
    layout_box, \
    layout_path


from . import EBeamCellWithLayers, cache_cell
from .cells import \
    GCArrayTE, \
    DCPadArray, \
    MZI

from .route_utils import bus_route_Z, \
    connect_ports_L, \
    append_Z_trace_vertical, \
    layout_manhattan_traces, \
    layout_ebeam_waveguide_from_points


def makeOpticFanRightCell(cell_class):
    """ Takes a cell that has one optical port to the left
        and routes it to the right.
    """

    class OpticFanRight(cell_class):

        def initialize_default_params(self):
            cell_class.initialize_default_params(self)
            self.define_param("layout_ports", self.TypeBoolean,
                              "Layout Pins?", default=True)

        def pcell(self, layout, cell=None, params=None):
            if cell is None:
                cell = layout.create_cell(self.name)
            cp = self.parse_param_args(params)
            lay = EBeamCellWithLayers.pre_pcell(self, layout, params)
            origin, ex, ey = CellWithPosition.origin_ex_ey(self, params)

            pcell, ports_dict = cell_class(f'{cell_class.__name__}_exp', cp).pcell(layout, params={'layout_ports': False})

            # filter optical, signal and ground ports
            opt_left_ports = list()
            opt_right_ports = list()
            other_ports = list()
            for portname, port in ports_dict.items():
                if portname.startswith('opt') and port.direction == ex:
                    opt_right_ports.append(port)
                elif portname.startswith('opt') and port.direction == -ex:
                    opt_left_ports.append(port)
                else:
                    other_ports.append(port)

            if len(opt_left_ports) < 1:
                return pcell, ports_dict  # do nothing
            elif len(opt_left_ports) > 1:
                raise NotImplementedError('This only takes cells with one optical port to the left.')

            cell_placement_origin = origin
            cell_ports = place_cell(cell, pcell, ports_dict, cell_placement_origin, relative_to=None)

            clearance_silicon = 10
            bbox = cell.bbox_per_layer(lay.Si).to_dtype(layout.dbu)
            bbox += cell.bbox_per_layer(lay.Si_p6nm).to_dtype(layout.dbu)
            max_silicon_y = max(bbox.p1 * ey, bbox.p2 * ey)
            max_silicon_x = max(bbox.p1 * ex, bbox.p2 * ex)
            min_silicon_x = min(bbox.p1 * ex, bbox.p2 * ex)

            ports = list()
            ports.extend(opt_right_ports)
            ports.extend(other_ports)

            max_right_ports_x = max([port.position * ex for port in opt_right_ports])
            max_right_ports_x = min(max_silicon_x, max_right_ports_x)

            # route from left to right from top
            port_left = opt_left_ports[0]
            point_list = [port_left.position]
            point_list.append(manhattan_intersection(point_list[-1], (min_silicon_x - 10) * ex, ey))
            point_list.append(manhattan_intersection(point_list[-1], (max_silicon_y + 20) * ey, ex))
            point_list.append(manhattan_intersection(max_right_ports_x * ex, point_list[-1], ex))
            layout_ebeam_waveguide_from_points(cell, list(reversed(point_list)))
            port_left.position = point_list[-1]
            port_left.direction = ex
            ports.append(port_left)

            ports_dict = {port.name: port for port in ports}

            if cp.layout_ports:
                port_to_pin_helper(ports, cell, lay.PinRec)

            return cell, ports_dict

    OpticFanRight.__qualname__ = 'OpticFanRight_' + cell_class.__name__
    return cache_cell(OpticFanRight)


def makeExperimentCellA(cell_class, gc_array_class=GCArrayTE):
    """ Takes a cell that is of type A and creates another cell containing
    a DCPadArray and a GCArray with autorouted traces.

    Type A means that:
        - all optical ports point to ex
        - all signal electrical ports point to ey
        - all ground electrical ports point to -ey
    """

    class AutoExperiment(cell_class, gc_array_class, DCPadArray):

        def initialize_default_params(self):
            cell_class.initialize_default_params(self)
            DCPadArray.initialize_default_params(self)
            del self.param_definition['port_width']
            del self.param_definition['Npads']
            gc_array_class.initialize_default_params(self)
            del self.param_definition['N_gc']

        def pcell(self, layout, cell=None, params=None):
            if cell is None:
                cell = layout.create_cell(self.name)
            cp = self.parse_param_args(params)
            lay = EBeamCellWithLayers.pre_pcell(self, layout, params)
            origin, ex, ey = CellWithPosition.origin_ex_ey(self, params)

            pcell, ports_dict = cell_class(f'{cell_class.__name__}_exp', cp).pcell(layout)

            # filter optical, signal and ground ports
            opt_ports = list()
            signal_ports = list()
            ground_ports = list()
            unknown_ports = list()
            for portname, port in ports_dict.items():
                if portname.startswith('opt'):
                    if port.direction == ex:
                        opt_ports.append(port)
                    else:
                        unknown_ports.append(port)
                elif portname.startswith('el'):
                    if port.direction == ey:
                        signal_ports.append(port)
                    elif port.direction == -ey:
                        ground_ports.append(port)
                    else:
                        unknown_ports.append(port)

            if len(unknown_ports) > 0:
                print("Warning makeExperimentCellA: there are some unrouted ports:", unknown_ports)

            # place the gc array
            N_gc_ports = len(opt_ports)
            avg_position_y = sum([port.position * ey for port in opt_ports]) / N_gc_ports
            max_position_x = max([port.position * ex for port in opt_ports])

            cell_placement_origin = origin
            cell_ports = place_cell(cell, pcell, ports_dict, cell_placement_origin, relative_to=None)

            clearance_elec = 100
            bbox = cell.bbox().to_dtype(layout.dbu)
            min_pad_array_x = min(bbox.p1 * ex, bbox.p2 * ex) - clearance_elec

            ports = list()
            if N_gc_ports > 0:
                # place gc array so that the avg optical port position matches the middle of the gc cell
                gc_placement_origin = cell_placement_origin + avg_position_y * ey + max_position_x * ex + \
                    10 * N_gc_ports * ex - (N_gc_ports - 1) * 0.5 * cp.pitch * ey
                gc_array_cell, gc_array_ports = gc_array_class('gc_array', cp).pcell(layout, params={'N_gc': N_gc_ports})
                gc_array_ports['origin'] = Port('origin', 0 * ex, None, None)
                gc_array_ports = place_cell(cell, gc_array_cell, gc_array_ports,
                                            gc_placement_origin,
                                            relative_to='opt0')

                clearance_gc = 950
                min_pad_array_x = min(min_pad_array_x, gc_placement_origin * ex - clearance_gc)

                gc_array_displaced_origin_port = gc_array_ports.pop('origin')
                ports.append(gc_array_displaced_origin_port)

                bus_route_Z(cell, opt_ports, gc_array_ports.values(), -ey)

            # connecting electrical ports
            # ## sorting electrical ports first
            N_signal_ports = len(signal_ports)
            N_ground_ports = len(ground_ports)
            proj_ex = lambda p: p.position * ex
            proj_ey = lambda p: p.position * ey
            if N_signal_ports > 0:
                signal_ports = sorted(signal_ports, key=proj_ex)
                max_position_y = max(proj_ey(port) for port in signal_ports)

                placement_origin_x = min_pad_array_x
                port_width = cp.pad_size - 20
                placement_origin = placement_origin_x * ex + max_position_y * ey + port_width * ey
                dcpadarray_ports = DCPadArray('pad_array', cp).place_cell(cell,
                    placement_origin, params={'angle_ex': 90 + cp.angle_ex,
                                              'Npads': N_signal_ports + 1,
                                              'port_width': port_width}, relative_to='el_1')

                sorted_dcpadarray_ports = sorted(dcpadarray_ports.values(), key=proj_ey)
                ports_from = signal_ports
                ports_to = sorted_dcpadarray_ports[1:]
                connect_ports_L(cell, cp.ML, ports_from, ports_to, ex)
                connect_ports_L(cell, cp.M_Heater, ports_from, ports_to, ex)

                if N_ground_ports > 0:
                    ground_ports = sorted(ground_ports, key=proj_ex)
                    min_position_y = min(proj_ey(port) for port in ground_ports)
                    big_ground_pad_height = 100
                    point3 = min_position_y * ey + proj_ex(ground_ports[-1]) * ex + ground_ports[-1].width * 0.5 * ex
                    point1 = proj_ex(ground_ports[0]) * ex - ground_ports[0].width * 0.5 * ex + min_position_y * ey - big_ground_pad_height * ey

                    # first, create shared ground pad with thickness of big_ground_pad_height
                    for layer in (lay.ML, lay.M_Heater):
                        layout_box(cell, layer, point1, point3, ex)

                        for port in ground_ports:
                            if proj_ey(port) > min_position_y:
                                layout_path(cell, layer,
                                    [port.position, manhattan_intersection(port.position, min_position_y * ey, ex)],
                                    port.width)

                    # then, connect this giant pad to the ground pad
                        big_ground_pad_point = (point1 + big_ground_pad_height / 2 * ey, layer, big_ground_pad_height)
                        dest_point = (sorted_dcpadarray_ports[0].position, layer, sorted_dcpadarray_ports[0].width)
                        ground_trace = append_Z_trace_vertical([dest_point], big_ground_pad_point, port_width, -ey)
                        layout_manhattan_traces(cell, ground_trace, ex)

            elif N_ground_ports > 0:
                raise RuntimeError(f"Case not implemented: N_signal_ports = 0 but N_ground_ports = {N_ground_ports} > 0")

            ports_dict = {port.name: port for port in ports}

            # ensuring that there is an origin to the ports_dict
            if 'origin' not in ports_dict.keys():
                ports_dict['origin'] = Port('origin', cell_placement_origin, None, None)
            return cell, ports_dict

    AutoExperiment.__qualname__ = 'AutoExperiment_' + cell_class.__name__
    return cache_cell(AutoExperiment)


MZI_FanRight = makeOpticFanRightCell(MZI)
MZI_Experiment = makeExperimentCellA(MZI_FanRight)
