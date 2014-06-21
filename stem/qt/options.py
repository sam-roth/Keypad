
import math
import logging
import warnings
import importlib

from PyQt4.Qt import QFont, QFontMetricsF

from ..options import GeneralSettings
from ..core import (Signal, 
                    Color,
                    Colorscheme,
                    Config)

from .qt_util import to_q_color, qcolor_marshaller

CompletionViewOpacity = 1

class TextViewSettings(object):
    def __init__(self, scheme=Colorscheme, settings=None):
        self.default_scheme = scheme
        if not isinstance(settings, Config):
            warnings.warn(DeprecationWarning('The settings parameter must now receive an argument of '
                'type Config'))
            settings = None
        self.tab_glyph = '\N{MATHEMATICAL RIGHT ANGLE BRACKET}'
        self.config = config = settings or Config.root

        settings = GeneralSettings.from_config(config)
        settings.value_changed += self.reload_settings
        self.settings = settings   
        self.reload_settings()

        self.font_yoffset = settings.font_yoffset


        
    def reload_settings(self, *args):
        
        s = self.settings
        
        self.scheme = s.colorscheme()
        fontname, fontsize = s.font_family, s.font_size
        self.double_strike = s.double_strike

        font = QFont(fontname)
        font.setPointSizeF(fontsize)

        if s.integer_metrics:
            font.setStyleStrategy(QFont.ForceIntegerMetrics | font.styleStrategy())
        if not s.antialias:
            font.setStyleStrategy(QFont.NoAntialias|font.styleStrategy())

        font.setHintingPreference(s.hinting_level)


        stretch = int(100 * s.font_xstretch)
        if stretch != 100:
            font.setStretch(stretch)

        spacing = int(100 * s.letter_spacing)
        if spacing != 100:
            font.setLetterSpacing(QFont.PercentageSpacing, spacing)

        weight = int(100 * s.weight)
        if weight != 100:
            font.setWeight(weight)

        self._line_spacing_factor = s.line_spacing

        self.q_font = font

        self.q_completion_bgcolor = to_q_color(self.scheme.bg)
        self.q_completion_bgcolor.setAlphaF(CompletionViewOpacity)

        self.q_bgcolor = to_q_color(self.scheme.bg)
        self.q_fgcolor = to_q_color(self.scheme.fg)
        self.tab_stop = s.tab_stop
        self.q_tab_color = to_q_color(self.scheme.bg.mean(self.scheme.fg))
        self.tab_glyph = s.tab_glyph
        self.word_wrap = False
        self.reloaded()

    @Signal
    def reloaded(self):
        pass
        
    
    completion_bgcolor = qcolor_marshaller('q_completion_bgcolor')
    bgcolor = qcolor_marshaller('q_bgcolor')
    fgcolor = qcolor_marshaller('q_fgcolor')

    @property
    def q_font(self):
        return self._q_font

    @q_font.setter
    def q_font(self, value):
        self._q_font = value
        # assume monospace
        self.font_metrics = fm = QFontMetricsF(value)
        self.char_width = fm.width('X')


    @property
    def line_spacing(self):
        return self.font_metrics.lineSpacing() * self._line_spacing_factor

    @property
    def baseline(self):
        return self.font_metrics.ascent() + 1 + self.font_yoffset

    def expand_tabs(self, text):
        return text.expandtabs(self.tab_stop)

        