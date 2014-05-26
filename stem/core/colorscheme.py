
from .color import Color
from ..util import clamp, deprecated
import random
import logging

class Colorscheme(object):
    
    fg = Color.from_hex('#000')
    bg = Color.from_hex('#FFF')

    cur_line_bg = bg
    
    selection_bg = fg
    selection_fg = bg
    
    fallback_sat = 0.5
    fallback_val = 128

    def __init__(self):
        self.lexical_categories = {
        }

    def lexical_category_attrs(self, lexcat):
        if lexcat not in self.lexical_categories:
            self.lexical_categories[lexcat] = dict(
                color=Color.from_hsv(random.random(), self.fallback_sat, self.fallback_val))

        return self.lexical_categories[lexcat]

    @deprecated
    def emphasize(self, color, steps):
        
        color = Color.from_hex(color)
        h,s,v = color.hsv
        
        v = (v + 16 * steps) % 256
        
        return Color.from_hsv(h, s, v, color.alpha)

    def emphasize_pair(self, fg, bg, steps):
        
        steps *= 16

        bh, bs, bv = Color(bg).hsv
        fh, fs, fv = Color(fg).hsv

        # We'll need to choose a strategy for this based on the value
        # of the colors.

        max_v = max(bv, fv)
        min_v = min(bv, fv)

        if max_v + steps <= 255:
            # increase the value of both colors
            bv += steps
            fv += steps
        elif min_v - steps >= 0:
            # decrease the value of both colors
            bv -= steps
            fv -= steps

        elif min_v - steps/2 >= 0 and max_v + steps/2 <= 255:
            # increase the value of one color and decrease
            # the value of the other
            min_v -= steps/2
            max_v += steps/2
            if bv < fv:
                bv = min_v
                fv = max_v
            else:
                bv = max_v
                fv = min_v
        
        else:
            # admit defeat
            pass

        return Color.from_hsv(fh, fs, fv), Color.from_hsv(bh, bs, bv)

    @property
    def cursor_color(self):
        return self.fg


class AbstractSolarized(Colorscheme):
    '''
    Abstract colorscheme based on
    http://ethanschoonover.com/solarized .

    The concrete colorschemes are :py:class:`SolarizedDark`
    and :py:class:SolarizedLight.

    '''
    _base03     = Color.from_hex('#002b36')
    _base02     = Color.from_hex('#073642')
    _base01     = Color.from_hex('#586e75')
    _base00     = Color.from_hex('#657b83')
    _base0      = Color.from_hex('#839496')
    _base1      = Color.from_hex('#93a1a1')
    _base2      = Color.from_hex('#eee8d5')
    _base3      = Color.from_hex('#fdf6e3')
    _yellow     = Color.from_hex('#b58900')
    _orange     = Color.from_hex('#cb4b16')
    _red        = Color.from_hex('#dc322f')
    _magenta    = Color.from_hex('#d33682')
    _violet     = Color.from_hex('#6c71c4')
    _blue       = Color.from_hex('#268bd2')
    _cyan       = Color.from_hex('#2aa198')
    _green      = Color.from_hex('#859900')


    fallback_sat = _blue.hsv[1]
    
    def __init__(self):
        super().__init__()
        self.lexical_categories.update(
            preprocessor=dict(color=self._orange),
            keyword=dict(color=self._green),
            function=dict(color=self._blue),
            literal=dict(color=self._cyan),
            escape=dict(color=self._red),
            todo=dict(color=self._magenta),
            docstring=dict(color=self._violet),
            type=dict(color=self._yellow)
        )


class SolarizedDark(AbstractSolarized):
    
    fg = AbstractSolarized._base0
    bg = AbstractSolarized._base03

    selection_fg = AbstractSolarized._base03
    selection_bg = AbstractSolarized._base01

    cur_line_bg = AbstractSolarized._base02

    fallback_val = fg.hsv[2]

    def __init__(self):
        super().__init__()
        self.lexical_categories.update(
            comment=dict(color=self._base01),
            search=dict(bgcolor=self._yellow, color=self.selection_fg),
        )


class SolarizedLight(AbstractSolarized):

    fg = AbstractSolarized._base00
    bg = AbstractSolarized._base3

    selection_fg = AbstractSolarized._base3
    selection_bg = AbstractSolarized._base0

    cur_line_bg = AbstractSolarized._base2

    fallback_val = fg.hsv[2]

    def __init__(self):
        super().__init__()

        bold = ['todo', 'type', 'keyword', 'escape',
                'function']

        lc = self.lexical_categories
        lc.update(comment=dict(color=self._base1),
                  search=dict(bgcolor=self._yellow, color=self._base01))
        for key in bold:
            lc[key].update(bold=True)

            
