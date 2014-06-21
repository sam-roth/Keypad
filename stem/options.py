import os
import os.path
import pathlib
import platform
import enum

from .core import colorscheme
from .core.nconfig import Settings, Field, Factory, Conversions


OnPosixSystem       = os.name == 'posix'
OnOSX               = platform.system() == 'Darwin'
OnWindows           = platform.system() == 'Windows'

UserConfigHome      = pathlib.Path(os.path.expanduser('~/.stem'))
DefaultColorScheme  = colorscheme.SolarizedDark()
DefaultDriverMod    = 'stem.qt.driver'



DefaultOtherFont                = 'Monospace', 11
DefaultOSXFont                  = 'Menlo', 12
DefaultWinFont                  = 'Consolas', 10

if OnOSX:
    TextViewFont                = DefaultOSXFont
elif OnWindows:
    TextViewFont                = DefaultWinFont
else:
    TextViewFont                = DefaultOtherFont

# You may wish to set this to False if spacing looks strange.
TextViewIntegerMetrics          = True

# Double striking text may improve legibility under FreeType
# when using light-on-dark color schemes. Generally, it makes
# the text look "bolder" without changing its metrics.
# This option is superfluous on Mac OS X, as CoreText 
# performs appropriate gamma adjustment automatically; however, it should
# work if you wish to use it.
TextViewDoubleStrike            = False

# CursorBlinkRate_Hz controls the number of blink cycles per second.
# CursorDutyCycle  controls the fraction of time each period during which the
# cursor should be visible. CursorDutyCycle is 0.8 by default to make it
# easier to find the cursor. There's a distinct lack of research on this
# topic, and my intuition might be wrong about it, so YMMV, but I did find
# this: https://twitter.com/ID_AA_Carmack/status/266267089596198912 .
CursorBlinkRate_Hz  = 1
CursorDutyCycle     = 0.8


class HintingLevel(enum.IntEnum):
    default = 0
    none = 1
    medium = 2
    full = 3

    @classmethod
    def from_literal(cls, value):
        if isinstance(value, str):
            return cls[value]
        else:
            return cls(value)

Conversions.register(HintingLevel, HintingLevel.from_literal)

class GeneralSettings(Settings):
    _ns_ = 'general'
    
    integer_metrics = Field(bool, TextViewIntegerMetrics,
                            docs='You may wish to set this to False if spacing looks strange.')
    double_strike = Field(bool, TextViewDoubleStrike,
                          docs='Double striking text may improve legibility under FreeType '
                               'when using light-on-dark color schemes. Generally, it makes '
                               'the text look "bolder" without changing its metrics. '
                               'This option is superfluous on Mac OS X, as CoreText '
                               'performs appropriate gamma adjustment automatically; '
                               'however, it should work if you wish to use it.')
    antialias = Field(bool, True)
    
    cursor_blink_rate = Field(float, CursorBlinkRate_Hz,
                              docs='Controls the number of blink cycles per second')
    cursor_duty_cycle = Field(float, CursorDutyCycle,
                              docs='Controls the fraction of time each period during which the '
                                   'cursor should be visible.'
                                   'CursorDutyCycle is 0.8 by default to make it '
                                   'easier to find the cursor. There\'s a distinct lack '
                                   'of research on this topic, and my intuition might be wrong '
                                   'about it, so YMMV, but I did find this: '
                                   'https://twitter.com/ID_AA_Carmack/status/266267089596198912 .')
    
    tab_stop = Field(int, 4, safe=True)
    indent_text = Field(str, '    ', safe=True)
    expand_tabs = Field(bool, True, safe=True)
    
    driver_mod = Field(str, 'stem.qt.driver')
    colorscheme = Field(Factory, 'stem.core.colorscheme.SolarizedDark')
    user_config_home = Field(pathlib.Path, pathlib.Path(os.path.expanduser('~/.stem')))
    
    font_family = Field(str, TextViewFont[0],
                        docs='The font for text views. If you\'re looking at the Sphinx docs, '
                             'the default value you\'ll see applies only to the platform on which '
                             'the documentation was compiled. For Mac OS X, the default is "Menlo", '
                             'for Windows the default is "Consolas", and for others the default is '
                             '"Monospace", which often resolves to some variant of Bitstream Vera '
                             'Mono.')

    font_size   = Field(int, TextViewFont[1])
    font_yoffset = Field(float, 0.0)
    font_xstretch = Field(float, 1.0)
    hinting_level = Field(HintingLevel, HintingLevel.default)
    letter_spacing = Field(float, 1.0)
    line_spacing = Field(float, 1.0)
    weight = Field(float, 0.5)
    tab_glyph = Field(str, '\N{MATHEMATICAL RIGHT ANGLE BRACKET}')

    selection = Field(Factory, 'stem.buffers.selection.BacktabSelection')

    elide_cmdline_history = Field(bool, True, docs='combine consecutive identical history items')
    
class CallTipSettings(Settings):
    _ns_ = 'call_tip'
    
    auto = Field(bool, True) # TODO: implement
    enable = Field(bool, True) # TODO: implement
    
    view_opacity = Field(float, 0.7)
    


GeneralConfig = GeneralSettings # deprecated alias
