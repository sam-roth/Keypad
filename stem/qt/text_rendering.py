

from PyQt4.Qt import *
from .qt_util import *
from ..util.cascade_dict import CascadeDict
from .. import options
import math
from . import options as qt_options


class TextViewSettings(object):
    def __init__(self, scheme):

        self.scheme = scheme

        fontname, fontsize = options.TextViewFont
        

        self.q_font    = QFont(fontname)
        self.q_font.setPointSizeF(fontsize)

        self.double_strike = options.TextViewDoubleStrike

        if options.TextViewIntegerMetrics:
            self.q_font.setStyleStrategy(QFont.ForceIntegerMetrics | self.q_font.styleStrategy())
            
        self.q_completion_bgcolor = to_q_color(self.scheme.bg)
        self.q_completion_bgcolor.setAlphaF(qt_options.CompletionViewOpacity)

        self.q_bgcolor  = to_q_color(self.scheme.bg)
        self.q_fgcolor  = to_q_color(self.scheme.fg)
        #self.q_bgcolor = QColor(self.scheme.bg) #QColor.fromRgb(0, 43, 54)
        #self.q_fgcolor = QColor(self.scheme.fg)
        #QColor.fromRgb(131, 148, 150) 
        self.tab_stop  = 8

        self.word_wrap = False


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


def paint_attr_text(painter, text, bounding_rect, cfg):
    fm = QFontMetricsF(cfg.q_font)

    # current coordinates
    xc = 0.0 + bounding_rect.left()
    yc = fm.ascent() + bounding_rect.top()
    raw_col = 0
    

    painter.setFont(cfg.q_font)
    
    # clear background (may have alpha component, so set appropriate
    # CompositionMode)
    with restoring(painter):
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(bounding_rect, cfg.q_bgcolor)


    current_attributes = {}
    current_lexcat_attributes = {}
    
    attributes = CascadeDict()
    attributes.dicts = [current_attributes, current_lexcat_attributes]

    italic = False
    underline = False

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


        if sel_bgcolor == 'auto':
            sel_bgcolor = cfg.scheme.selection_bg

        if sel_color == 'auto':
            sel_color = cfg.scheme.selection_fg


            
        actual_color = sel_color or color
        actual_bgcolor = sel_bgcolor or bgcolor

        new_italic      = attributes.get('italic', italic)
        new_underline   = attributes.get('underline', underline)

        if new_italic != italic or new_underline != underline:
            italic = new_italic
            underline = new_underline

            font = painter.font()
            font.setItalic(new_italic)
            font.setUnderline(new_underline)
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
        lines * (fm.lineSpacing()) # + 1)
        #fm.width(cfg.expand_tabs(text.text)) + 1,
        #fm.lineSpacing() + 1
    )





def render_attr_text(text, cfg):
    '''
    Renders the `AttributedString` `text` to a pixmap.

    :type text: stem.attributed_string.AttributedString
    :type cfg: stem.view.TextViewSettings
    '''

    assert isinstance(cfg, TextViewSettings)

    
    # Trying to make a pixmap of zero-width produces many annoying warnings.
    bounding_rect_size = text_size(text, cfg).expandedTo(QSizeF(1,1))

    pixmap = QPixmap(bounding_rect_size.toSize())
    #pixmap.setAlphaChannel(QPixmap(bounding_rect_size.toSize()))
    #assert pixmap.hasAlpha()
    painter = QPainter(pixmap)
    with ending(painter):
        paint_attr_text(painter, text, QRectF(QPointF(0, 0), bounding_rect_size), cfg)

    return pixmap
            

def apply_overlay(text, overlay):
    text = text.clone()

    for start, end, key, value in overlay:
        if end >= len(text):
            text.append(' ' * (end - len(text)))
        text.set_attributes(start, end, **{key: value})

    return text



# Updates will be overlayed with a translucent red box if set to True.
FLASH_RERENDER = False

def draw_attr_text(painter, rect, text, settings, partial=False, overlay=frozenset()):
    '''
    Draw the AttributedString text, rerendering it if necessary. Use the
    overlay formatting specified if any.

    The overlay formatting should be specified as a frozenset of tuples of
        start_pos, end_pos, key, value.

    The overlay formatting will be applied to the string before displaying it.
    '''
    cache_key = 'stem.view.draw_attr_text.pixmap'
    draw_pos_key = 'stem.view.draw_attr_text.pos'
    overlay_key = 'stem.view.draw_attr_text.overlay_formatting'

    
    # Ensure that we don't get a mutable set here. That would be bad. (I'm
    # assuming that Python doesn't make a copy here if the set is already
    # frozen.)
    overlay = frozenset(overlay)

    pixmap = text.caches.get(cache_key)

    no_cache            = pixmap is None or \
                          text.caches.get(overlay_key, frozenset()) != overlay
    should_draw_text    = not partial or no_cache or \
                          text.caches.get(draw_pos_key, None) != rect.topLeft()
    

    if no_cache:
        if overlay:
            text_to_draw = apply_overlay(text, overlay)
            text.caches[overlay_key] = overlay
        else:
            text_to_draw = text
            try:
                del text.caches[overlay_key]
            except KeyError:
                pass

        pixmap = render_attr_text(text_to_draw, settings)
        text.caches[cache_key] = pixmap
    
    if should_draw_text or (FLASH_RERENDER and text.caches.get('flashlast')):
        text.caches[draw_pos_key] = rect.topLeft()
        with restoring(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(rect, settings.q_bgcolor)
        painter.drawPixmap(rect.topLeft(), pixmap)
        if FLASH_RERENDER:
            if no_cache:
                painter.fillRect(rect, QColor.fromRgb(255, 0, 0, 64))
                text.caches['flashlast'] = True
            else:
                text.caches['flashlast'] = False

    
    return (should_draw_text, no_cache)
    

