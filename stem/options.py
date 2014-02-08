import os
import os.path
import pathlib
import platform

from .core import colorscheme


OnPosixSystem       = os.name == 'posix'
OnOSX               = platform.system() == 'Darwin'
OnWindows           = platform.system() == 'Windows'

UserConfigHome      = pathlib.Path(os.path.expanduser('~/.stem'))
DefaultColorScheme  = colorscheme.SolarizedDark()
DefaultDriverMod    = 'stem.qt.driver'



DefaultOtherFont                = 'Monospace', 10
DefaultOSXFont                  = 'Menlo', 12
DefaultWinFont                  = 'Consolas', 10

if OnOSX:
    TextViewFont                = DefaultOSXFont
elif OnWindows:
    TextViewFont                = DefaultWinFont
else:
    TextViewFont                = DefaultOtherFont

TextViewIntegerMetrics          = False
