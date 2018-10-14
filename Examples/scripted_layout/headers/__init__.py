import pya
import os
from functools import partial
from SiEPIC.utils import get_technology_by_name
from SiEPIC.utils.pcells import cache_cell as siepic_cache_cell
from SiEPIC.utils.pcells import KLayoutPCell, objectview

TECHNOLOGY = get_technology_by_name('EBeam')
EX = pya.DVector(1, 0)
EY = pya.DVector(0, 1)


cache_cell = partial(siepic_cache_cell, cache_dir=os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'cache'))


class EBeamCell(KLayoutPCell):
    """ Main layout class for instantiating PDK-compatible cells """

    TECHNOLOGY = TECHNOLOGY


class EBeamCellWithLayers(EBeamCell):
    ''' Abstract class with more concise layer handling

        @atait says:

        Why not just use global variables for layers?
        This way allows any layer to be overriden through the params argument;
        however, that is very rare, so it makes the default case pretty concise.

        This pattern/abstract was made for two reasons
        1. Verbose to specify all these params – should be done only once
        2. Easy to define non-TECH layers. For example, lay.emitter = lay.SiNpp
        3. Portable across scope. Old version examples:
            No problem within `pcell` -- `layerCollector = layerSiN`
            Awful within `helperMethod` --  `getattr(self.pcell, 'locals')().update(layerCollector=layerSi)`

        I think the previous pattern was to allow easy typing access in the placement procedure.
        This new version is still pretty keyboard friendly.
        Instead of `layerSi` a.k.a `locals()['layerSi']`, it's `lay.Si`

        @tlima says:

        TODO: the only issue with this implementation is that all
        pcells in the IME library will have useless layers defined,
        which will confuse users placing pcells in klayout.
    '''

    def initialize_default_params(self):
        self.define_param("silayer", self.TypeLayer,
                          "Si Layer",
                          default=TECHNOLOGY['Si'])
        self.define_param("MLOpen", self.TypeLayer,
                          "ML Open Layer",
                          default=TECHNOLOGY['13_MLopen'])
        self.define_param("ML", self.TypeLayer,
                          "ML Layer",
                          default=TECHNOLOGY['12_M2'])
        self.define_param("M_Heater", self.TypeLayer,
                          "M Heater Layer",
                          default=TECHNOLOGY['M1'])
        self.define_param("devrec", self.TypeLayer,
                          "DevRec Layer",
                          default=TECHNOLOGY['DevRec'])
        self.define_param("pinrec", self.TypeLayer,
                          "Pin Layer",
                          default=TECHNOLOGY['PinRec'])
        self.define_param("textl", self.TypeLayer,
                          "Text Layer",
                          default=TECHNOLOGY['Text'])
        self.define_param("SEM", self.TypeLayer,
                          "SEM Layer",
                          default=TECHNOLOGY['SEM'])
        self.define_param("Si_p6nm", self.TypeLayer,
                          "Si_p6nm Layer",
                          default=TECHNOLOGY['31_Si_p6nm'])
        self.define_param("FloorPlan", self.TypeLayer,
                          "FloorPlan Layer",
                          default=TECHNOLOGY['FloorPlan'])

    def pre_pcell(self, layout, params=None):  # pylint: disable=unused-argument
        ''' Everything updates params and object views them
        '''
        cp = self.parse_param_args(params)

        lay = objectview({})
        lay.Si = layout.layer(cp.silayer)
        lay.MLOpen = layout.layer(cp.MLOpen)
        lay.M_Heater = layout.layer(cp.M_Heater)
        lay.ML = layout.layer(cp.ML)
        lay.DevRec = layout.layer(cp.devrec)
        lay.PinRec = layout.layer(cp.pinrec)
        lay.Text = layout.layer(cp.textl)
        lay.SEM = layout.layer(cp.SEM)
        lay.Si_p6nm = layout.layer(cp.Si_p6nm)
        lay.FloorPlan = layout.layer(cp.FloorPlan)

        return lay
