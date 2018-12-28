from os.path import join
from siepic_tools.utils import register_siepic_technology as register

# Load technologies included in the pdk
tech_path = join('..', '..', 'klayout_dot_config', 'tech')
EBEAM_TECH = register(join(tech_path, 'EBeam', 'EBeam.lyt'))


# Load libraries
from .library import SiEPIC_EBeam  # noqa
SiEPIC_EBeam(verbose=False)
