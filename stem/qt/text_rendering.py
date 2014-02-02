

from PyQt4.Qt import *
from .qt_util import *
from ..util.cascade_dict import CascadeDict
from .. import options

import math

class TextViewSettings(object):
    def __init__(self, scheme):

        self.scheme = scheme

        fontname, fontsize = options.TextViewFont
        

        self.q_font    = QFont(fontname)
        self.q_font.setPointSizeF(fontsize)

        if options.TextViewIntegerMetrics:
            self.q_font.setStyleStrategy(QFont.ForceIntegerMetrics | self.q_font.styleStrategy())
            
        self.q_completion_bgcolor = to_q_color(self.scheme.bg)
        self.q_completion_bgcolor.setAlphaF(0.7)

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
                QRectF(xc, 0, width, fm.lineSpacing()+1),
                to_q_color(actual_bgcolor)
            )
        
        painter.setPen(to_q_color(actual_color))
        painter.drawText(QPointF(xc, yc), tab_expanded_string)# string)

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
        lines * (fm.lineSpacing() + 1)
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
            

def draw_attr_text(painter, rect, text, settings, partial=False):
    cache_key = 'stem.view.draw_attr_text.pixmap'
    draw_pos_key = 'stem.view.draw_attr_text.pos'
    
    pixmap = text.caches.get(cache_key)

    no_cache            = pixmap is None
    should_draw_text    = not partial or no_cache or \
                          text.caches.get(draw_pos_key, None) != rect.topLeft()
    

    if no_cache:
        pixmap = render_attr_text(text, settings)
        text.caches[cache_key] = pixmap
    
    if should_draw_text:
        text.caches[draw_pos_key] = rect.topLeft()
        with restoring(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(rect, settings.q_bgcolor)
        painter.drawPixmap(rect.topLeft(), pixmap)

    return (should_draw_text, no_cache)
    

