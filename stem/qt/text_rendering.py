

from PyQt4.Qt import *
from .qt_util import *
from ..util.cascade_dict import CascadeDict
from .. import options
import math
from . import options as qt_options
from ..core.conftree import ConfTree
from ..core import Signal
import logging
from ..core.color import Color
from ..core.colorscheme import Colorscheme
from ..options import GeneralConfig
from ..core.nconfig import Config

import warnings
import importlib

def resolve_dotted_name(name):
    modname, objname = name.rsplit('.', 1)
    mod = importlib.import_module(modname)
    return getattr(mod, objname)

class TextViewSettings(object):
    def __init__(self, scheme=Colorscheme, settings=None):
        self.default_scheme = scheme
        if not isinstance(settings, Config):
            warnings.warn(DeprecationWarning('The settings parameter must now receive an argument of '
                'type Config'))
            settings = None

        self.config = config = settings or Config.root

        settings = GeneralConfig.from_config(config)
        settings.value_changed += self.reload_settings
        #(settings or ConfTree()).TextView
        self.settings = settings   
        #settings.modified.connect(self._on_settings_changed)
        self.reload_settings()
        self.tab_glyph = '⟩'
        self.font_yoffset = settings.font_yoffset


        
    def reload_settings(self, *args):
        s = self.settings
        
        self.scheme = s.colorscheme()
#         self.scheme = resolve_dotted_name(s.colorscheme)()

        #s.get('Scheme', self.default_scheme)
        
        fontname, fontsize = s.font_family, s.font_size
        

        self.q_font    = QFont(fontname)
        self.q_font.setPointSizeF(fontsize)
        
        self.double_strike = s.double_strike

        #self.double_strike = s.get('DoubleStrike', options.TextViewDoubleStrike, bool)
        
        #if s.get('IntegerMetrics', options.TextViewIntegerMetrics, bool):
        if s.integer_metrics:
            self.q_font.setStyleStrategy(QFont.ForceIntegerMetrics | self.q_font.styleStrategy())
        
        #antialias = s.get('Antialias', True, bool)
        if not s.antialias:
            self.q_font.setStyleStrategy(QFont.NoAntialias|self.q_font.styleStrategy())
            
        self.q_completion_bgcolor = to_q_color(self.scheme.bg)
        self.q_completion_bgcolor.setAlphaF(qt_options.CompletionViewOpacity)

        self.q_bgcolor  = to_q_color(self.scheme.bg)
        self.q_fgcolor  = to_q_color(self.scheme.fg)
        #self.q_bgcolor = QColor(self.scheme.bg) #QColor.fromRgb(0, 43, 54)
        #self.q_fgcolor = QColor(self.scheme.fg)
        #QColor.fromRgb(131, 148, 150) 
        self.tab_stop  = s.tab_stop
        #s.get('TabStop', 8, int)
        self.q_tab_color = to_q_color(self.scheme.bg.mean(self.scheme.fg))
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
        fm = QFontMetricsF(value)
        self.char_width = fm.width('X')

    def expand_tabs(self, text):
        return text.expandtabs(self.tab_stop)


def paint_attr_text(painter, text, bounding_rect, cfg, bgcolor=None):
    fm = QFontMetricsF(cfg.q_font)

    # current coordinates
    xc = 0.0 + bounding_rect.left()
    yc = fm.ascent() + bounding_rect.top()
    raw_col = 0
    
    if bgcolor is None:
        q_bgcolor = cfg.q_bgcolor
    else:
        q_bgcolor = to_q_color(bgcolor)

    painter.setFont(cfg.q_font)
    
    # clear background (may have alpha component, so set appropriate
    # CompositionMode)
    with restoring(painter):
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(bounding_rect, q_bgcolor)


    current_attributes = {}
    current_lexcat_attributes = {}
    
    attributes = CascadeDict()
    attributes.dicts = [current_attributes, current_lexcat_attributes]

    italic = False
    underline = False
    bold = False

    for string, deltas in text.iterchunks():
    
        current_attributes.update(deltas)

        if 'lexcat' in deltas:
            lexcat = deltas['lexcat']
            current_lexcat_attributes.clear()
            if lexcat is not None:
                current_lexcat_attributes.update(cfg.scheme.lexical_category_attrs(lexcat))
        
        color       = attributes.get('color', cfg.q_fgcolor)
        bgcolor     = attributes.get('bgcolor')
        sel_bgcolor = attributes.get('sel_bgcolor')
        sel_color   = attributes.get('sel_color')
        error       = attributes.get('error', False)
        cartouche   = attributes.get('cartouche') # color of rectangle around text
        tab         = attributes.get('tab', False)

        if sel_bgcolor == 'auto':
            sel_bgcolor = cfg.scheme.selection_bg

        if sel_color == 'auto':
            sel_color = cfg.scheme.selection_fg

        
            
        actual_color = sel_color or color
        actual_bgcolor = sel_bgcolor or bgcolor

        new_italic      = attributes.get('italic', False)
        new_underline   = attributes.get('underline', False)
        new_bold        = attributes.get('bold', False)

        if new_italic != italic or new_underline != underline or new_bold != bold:
            italic = new_italic
            underline = new_underline
            bold = new_bold

            font = painter.font()
            font.setItalic(new_italic)
            font.setUnderline(new_underline)
            font.setBold(new_bold)
            painter.setFont(font)
        
        # tab_expanded_string used for width calculations
        offset_from_tstop = raw_col % cfg.tab_stop
        tab_expanded_string = cfg.expand_tabs(' ' * (offset_from_tstop) + string)[offset_from_tstop:]
        width = fm.width(tab_expanded_string)


        # draw background
        if actual_bgcolor is not None:
            painter.fillRect(
                QRectF(xc, 0, width, fm.lineSpacing()), #+1),
                to_q_color(actual_bgcolor)
            )

        if cartouche is not None:
            with restoring(painter):
                painter.setPen(to_q_color(cartouche))
                painter.drawRect(xc, 0, width-1, fm.lineSpacing()-1)
        
        painter.setPen(to_q_color(actual_color))
        
        if tab and string == '\t':
            with restoring(painter):
                pen = painter.pen()
                pen.setColor(cfg.q_tab_color)
                painter.setPen(pen)
                painter.drawText(QRectF(QPointF(xc, 0), QSizeF(width-1, fm.lineSpacing()-1)), 
                                 Qt.AlignRight,
                                 cfg.tab_glyph)
            
        painter.drawText(QPointF(xc, yc), tab_expanded_string)# string)
        if cfg.double_strike:
            # greatly improves legibility on dark backgrounds when using FreeType
            painter.drawText(QPointF(xc, yc), tab_expanded_string)
            
        if error:
            with restoring(painter):
                pen = painter.pen()
                pen.setColor(QColor(255, 0, 0, 128))    # FIXME: hardcoded color
                pen.setStyle(Qt.DotLine)
                pen.setWidth(2)                         # FIXME: hardcoded pen width
                error_y = yc + fm.underlinePos()
                painter.setPen(pen)
                painter.drawLine(xc, error_y, xc + width, error_y)


        xc += width
        raw_col += len(tab_expanded_string)



def text_size(text, cfg, window_width=None):
    # fonts can have fractional width (at least on OS X) => use -F variant of
    # QFontMetrics
    fm = QFontMetricsF(cfg.q_font)

    tab_expanded = cfg.expand_tabs(text.text)
    chwidth = fm.width('x')

    if window_width and cfg.word_wrap:
        chars_per_view_line = window_width // chwidth
        lines = int(math.ceil(len(tab_expanded) / chars_per_view_line))
    else:
        lines = 1
    
    return QSizeF(
        window_width or (chwidth * len(tab_expanded)),
        lines * fm.lineSpacing() # + 1)
        #fm.width(cfg.expand_tabs(text.text)) + 1,
        #fm.lineSpacing() + 1
    )





def render_attr_text(text, cfg, bgcolor=None):
    '''
    Renders the `AttributedString` `text` to a pixmap.

    :type text: stem.attributed_string.AttributedString
    :type cfg: stem.view.TextViewSettings
    '''

    assert isinstance(cfg, TextViewSettings)

    
    # Trying to make a pixmap of zero-width produces many annoying warnings.
    bounding_rect_size = qsizef_ceil(text_size(text, cfg).expandedTo(QSizeF(1,1)))

    
    pixmap = QPixmap(bounding_rect_size)
    
    #pixmap.setAlphaChannel(QPixmap(bounding_rect_size.toSize()))
    #assert pixmap.hasAlpha()
    painter = QPainter(pixmap)
    with ending(painter):
        paint_attr_text(painter, 
                        text,
                        QRectF(QPointF(0, 0),
                               QSizeF(bounding_rect_size.width(),
                                      bounding_rect_size.height())),
                        cfg,
                        bgcolor=bgcolor)

    return pixmap
            

def apply_overlay(text, overlay):
    text = text.clone()

    for start, end, key, value in overlay:
        if end >= len(text):
            text.append(' ' * (end - len(text)))
        text.set_attributes(start, end, **{key: value})

    return text

def tab_mark(text):
    for i, ch in enumerate(text.text):
        if ch == '\t':
            text.set_attributes(i, i+1, tab=True) 


# Updates will be overlayed with a translucent red box if set to True.
FLASH_RERENDER = False

def draw_attr_text(painter, rect, text, 
                   settings, partial=False,
                   overlay=frozenset(),
                   bgcolor=None):
    '''
    Draw the AttributedString text, rerendering it if necessary. Use the
    overlay formatting specified if any.

    The overlay formatting should be specified as a frozenset of tuples of
        start_pos, end_pos, key, value.

    The overlay formatting will be applied to the string before displaying it.

    The ``bgcolor`` parameter is the background color of the line, or ``None``
    for the default.
    '''
    cache_key = 'stem.view.draw_attr_text.pixmap'
    draw_pos_key = 'stem.view.draw_attr_text.pos'
    overlay_key = 'stem.view.draw_attr_text.overlay_formatting'
    bgcolor_key = 'stem.view.draw_attr_text.bgcolor'

    
    # Ensure that we don't get a mutable set here. That would be bad. (I'm
    # assuming that Python doesn't make a copy here if the set is already
    # frozen.)
    overlay = frozenset(overlay)

    pixmap = text.caches.get(cache_key)

    no_cache            = (pixmap is None 
                           or text.caches.get(overlay_key, frozenset()) != overlay
                           or bgcolor != text.caches.get(bgcolor_key))
    should_draw_text    = not partial or no_cache or \
                          text.caches.get(draw_pos_key, None) != rect.topLeft()



    if no_cache:
        if overlay or '\t' in text.text:
            text_to_draw = text
            if overlay:
                text_to_draw = apply_overlay(text_to_draw, overlay)
            
            tab_mark(text_to_draw)
            text.caches[overlay_key] = overlay
        else:
            text_to_draw = text
            try:
                del text.caches[overlay_key]
            except KeyError:
                pass

        pixmap = render_attr_text(text_to_draw, 
                                  settings,
                                  bgcolor=bgcolor)
        text.caches[cache_key] = pixmap
        
    if should_draw_text or (FLASH_RERENDER and text.caches.get('flashlast')):
        text.caches[bgcolor_key] = bgcolor
        if bgcolor is not None:
            q_bgcolor = to_q_color(bgcolor)
        else:
            q_bgcolor = settings.q_bgcolor

        text.caches[draw_pos_key] = rect.topLeft()
        with restoring(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(rect, q_bgcolor)
        painter.drawPixmap(rect.topLeft(), pixmap)
        if FLASH_RERENDER:
            if no_cache:
                painter.fillRect(rect, QColor.fromRgb(255, 0, 0, 64))
                text.caches['flashlast'] = True
            else:
                text.caches['flashlast'] = False

    
    return (should_draw_text, no_cache)
    

