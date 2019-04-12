from os.path import join, realpath, dirname

from siepic_tools.utils import register_siepic_technology as register

# Load technologies included in the pdk
current_path = dirname(realpath(__file__))
tech_path = join(current_path, '..', '..', 'tech')
EBEAM_TECH = register(join(tech_path, 'EBeam', 'EBeam.lyt'))


# Load libraries
from .library import SiEPIC_EBeam  # noqa
SiEPIC_EBeam(verbose=False)
