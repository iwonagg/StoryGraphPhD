# path_root = r'/mnt/d/Uniwersytet Jagielloński/StoryGraph - General/materiały fabularne'
# path_root = r'/mnt/d/GitHub/StoryGraphPython/examples'

from pathlib import Path
from library.tools import get_project_root

path_root = get_project_root() / Path('examples')