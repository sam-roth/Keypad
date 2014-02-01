
import os.path
import pathlib
from .core import colorscheme

UserConfigHome      = pathlib.Path(os.path.expanduser('~/.stem'))
DefaultColorScheme  = colorscheme.SolarizedDark()


TextViewFont        = 'Menlo', 12
