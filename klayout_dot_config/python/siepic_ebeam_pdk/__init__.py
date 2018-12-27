from os.path import join
from siepic_tools.utils import register_siepic_technology as register

# Load technologies included in the pdk
tech_list = []
tech_path = join('..', '..', 'klayout_dot_config', 'tech')
tech_list.append(register(join(tech_path, 'EBeam', 'EBeam.lyt')))
