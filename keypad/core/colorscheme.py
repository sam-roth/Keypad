
from .color import Color
from ..util import clamp, deprecated, scopedict
import random
import logging
import collections.abc

class LexcatDict(scopedict.ScopeDict):

    adapt = {
        'type': 'identifier.type',
        'function': 'identifier.function',
        'escape': 'literal.string.escape',
    }

    @classmethod
    def make_key(cls, key):
        v = cls.adapt.get(key)
        if v is not None:
            return super().make_key(v)
        else:
            return super().make_key(key)

    def __setitem__(self, key, val):
        if not isinstance(val, collections.abc.Mapping):
            raise TypeError('Each lexcat must be a mapping.')
        for k, v in val.items():
            if not isinstance(k, str):
                raise TypeError('The keys of each lexcat must be strings, not {}.'.format(type(k)))
            if k in ('color', 'bgcolor', 'sel_bgcolor', 'sel_color') and not isinstance(v, (Color, str)):
                raise TypeError('Keys representing colors must be strings or Colors, not {}.'.format(type(v)))
        super().__setitem__(key, val)


class Colorscheme(object):

    fg = Color.from_hex('#000')
    bg = Color.from_hex('#FFF')

    nontext_bg = Color.from_hex('#333')

    cur_line_bg = bg

    selection_bg = fg
    selection_fg = bg

    fallback_sat = 0.5
    fallback_val = 128

    def __init__(self):
        self.lexical_categories = LexcatDict()

    def lexcat_attrs(self, lexcat):
        return self.lexical_category_attrs(lexcat)

    def lexical_category_attrs(self, lexcat):
        if lexcat not in self.lexical_categories:
            if lexcat == 'punctuation.match':
                self.lexcats[lexcat] = dict(color=self.matching_brace_fg,
                                            bgcolor=self.matching_brace_bg)
            elif lexcat == 'punctuation.mismatch':
                self.lexcats[lexcat] = dict(color=self.brace_mismatch_fg,
                                            bgcolor=self.brace_mismatch_bg)
            else:
                self.lexcats[lexcat] = dict(color=Color.from_hsv(random.random(),
                                                                 self.fallback_sat,
                                                                 self.fallback_val))


        return self.lexcats[lexcat]

    @property
    def brace_mismatch_bg(self):
        return self.fg

    @property
    def brace_mismatch_fg(self):
        return self.bg

    @property
    def matching_brace_bg(self):
        return self.fg

    @property
    def matching_brace_fg(self):
        return self.bg

    @property
    def extra_line_bg(self):
        return self.nontext_bg

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

    @property
    def cursor_inverse_color(self):
        return self.bg

    @property
    def lexcats(self):
        return self.lexical_categories

    @lexcats.setter
    def lexcats(self, value):
        self.lexical_categories = value

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
        self.lexcats.update(
            preprocessor=dict(color=self._orange),
            keyword=dict(color=self._green),
            function=dict(color=self._blue),
            literal=dict(color=self._cyan),
            escape=dict(color=self._red),
            todo=dict(color=self._magenta),
            docstring=dict(color=self._violet),
#             type=dict(color=self._yellow),
            identifier=dict(color=self._blue)
        )

        self.lexcats.update({
            'keyword.context': dict(color=self._blue),
            'keyword.modulesystem': dict(color=self._orange),
            'identifier.type': dict(color=self._yellow),
            'punctuation.sigil': dict(color=self._red),
            'comment.documentation': dict(color=self._violet),
        })

#         self.lexcats['identifier.reserved'] = self._blue
#         self.lexcats['keyword.context'] = dict(color=self._blue)
#         self.lexcats['identifier.type'] = dict(color=self._yellow)

    @property
    def matching_brace_bg(self):
        return self.selection_bg

    @property
    def matching_brace_fg(self):
        return self._red

    @property
    def brace_mismatch_bg(self):
        return self._orange

    @property
    def brace_mismatch_fg(self):
        return self._base03

def extrap_value(color1, color2):
    _, _, v1 = color1.hsv
    _, _, v2 = color2.hsv
    return color2.brighter(v2/v1)

class SolarizedDark(AbstractSolarized):

    fg = AbstractSolarized._base0
    bg = AbstractSolarized._base03

    selection_fg = AbstractSolarized._base03
    selection_bg = AbstractSolarized._base01

    cur_line_bg = AbstractSolarized._base02

    nontext_bg = extrap_value(AbstractSolarized._base02,
                              AbstractSolarized._base03)


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

    nontext_bg = AbstractSolarized._base2

    cur_line_bg = AbstractSolarized._base2

    fallback_val = fg.hsv[2]

    def __init__(self, high_contrast=False, enable_bold=True):
        super().__init__()

        if high_contrast:
            self.fg = AbstractSolarized._base01

        if enable_bold:
            bold = ['keyword']
        else:
            bold = []

        lc = self.lexcats

        lc.update(comment=dict(color=self._base1),
                  search=dict(bgcolor=self._yellow, color=self.selection_fg))
        for key in bold:
            lc[key].update(bold=True)

class SolarizedLightHighContrast(SolarizedLight):
    '''
    This is the high contrast version of the Solarized light theme, based on
    the high contrast mode provided in the Vim implementation of Solarized.
    '''

    def __init__(self, *args, **kw):
        kw.update(high_contrast=True)
        super().__init__(*args, **kw)

class EnhancedContrastMixin:

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        min_contrast = kw.pop('min_contrast', 0.4)

        bg_lightness, _, _ = Color.from_hex(self.bg).lab

        for k, v in self.lexcats.items():
            if 'bgcolor' in v:
                continue # skip entries with explicit background color

            if 'color' in v:
                color = Color.from_hex(v['color'])
                l, a, b = color.lab

                if abs(l - bg_lightness) < min_contrast:
                    if l > bg_lightness:
                        # light foreground color too dark
                        v['color'] = Color.from_lab(l - abs(l - bg_lightness) + min_contrast, a, b)
                    else:
                        # dark foreground color too light
                        v['color'] = Color.from_lab(l + abs(l - bg_lightness) - min_contrast, a, b)

class TextMateTheme(Colorscheme):
    '''
    Use a TextMate/Sublime Text color scheme.
    '''

    scopes = scopedict.splitkeys({
        'comment': 'comment',

        'constant.numeric': 'literal.numeric',
        'constant.character': 'literal.character',
        'string': 'literal',

        'constant.language': 'identifier.constant',
        # we'll consider this to be the default
        'entity.name.function': 'identifier', 
        'support.function': 'identifier.function',

        'support.type': 'identifier.type',
        'support.class': 'identifier.type',
        'storage.type': 'identifier.type',
        'storage.modifier': 'identifier.type',

        'variable.parameter': 'identifier.local.parameter',

        'keyword': 'keyword',

        'invalid': 'error',
    })

    def __init__(self, theme):
        super().__init__()
        import plistlib
        data = plistlib.readPlist(theme)
        lc = self.lexical_categories
        self.unassigned = []

        for group in data.settings:
            if 'settings' not in group:
                continue

            s = group.settings
            if 'scope' not in group:
                try:
                    self.bg = Color.from_hex(s.background)
                except AttributeError:
                    pass

                try:
                    self.fg = Color.from_hex(s.foreground)
                except AttributeError:
                    pass

                try:
                    self.selection_bg = Color.from_hex(s.selection)
                except AttributeError:
                    pass

                self.selection_fg = self.fg
                try:
                    self.cur_line_bg = Color.from_hex(s.lineHighlight).composite(self.bg)
                except AttributeError:
                    pass
                self.nontext_bg = self.bg
            else:

                attrs = {}
                try:

                    if 'background' in s:
                        attrs['bgcolor'] = Color.from_hex(s.background)
                    if 'foreground' in s:
                        attrs['color'] = Color.from_hex(s.foreground)
                    if s.get('fontStyle') == 'bold':
                        attrs['bold'] = True
                except ValueError:
                    pass
                else:
                    assigned = False
                    for scope in group.scope.split(','):
                        lcname = scopedict.most_specific(self.scopes, scope.strip(), default=None)
                        if lcname is not None and lcname not in lc:
                            lc[lcname] = attrs
                            assigned = True

                    if not assigned:
                        self.unassigned.append(attrs)





    def lexical_category_attrs(self, lexcat):
        if lexcat not in self.lexical_categories:
            if self.unassigned:
                self.lexical_categories[lexcat] = self.unassigned.pop()
            else:
                self.lexical_categories[lexcat] = dict(color=Color.from_hex('#F0F'))

        return self.lexical_categories[lexcat]
