

from PyQt4.Qt import *
from .qt_util import *


class TextViewSettings(object):
    def __init__(self):
        from ..control import colors

        self.scheme    = colors.scheme

        self.q_font    = QFont('Menlo')
        self.q_font.setPixelSize(13)
            
        self.q_bgcolor = QColor(self.scheme.bg) #QColor.fromRgb(0, 43, 54)
        self.q_fgcolor = QColor(self.scheme.fg)
        #QColor.fromRgb(131, 148, 150) 
        self.tab_stop  = 8




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


def render_attr_text(text, cfg):
    '''
    Renders the `AttributedString` `text` to a pixmap.

    :type text: codeedit.attributed_string.AttributedString
    :type cfg: codeedit.view.TextViewSettings
    '''

    assert isinstance(cfg, TextViewSettings)

    
    # fonts can have fractional width (at least on OS X) => use -F variant of
    # QFontMetrics
    fm = QFontMetricsF(cfg.q_font)
    
    bounding_rect_size = QSizeF(
        fm.width(cfg.expand_tabs(text.text)) + 1,
        fm.lineSpacing() + 1
    )

    pixmap = QPixmap(bounding_rect_size.toSize())
    #pixmap.setAlphaChannel(QPixmap(bounding_rect_size.toSize()))
    #assert pixmap.hasAlpha()
    
    # current coordinates
    xc = 0.0
    yc = fm.ascent()
    raw_col = 0
    

    painter = QPainter(pixmap)
    with ending(painter):
        painter.setFont(cfg.q_font)
        
        # clear background (may have alpha component, so set appropriate
        # CompositionMode)
        with restoring(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(pixmap.rect(), cfg.q_bgcolor)

        color = None
        bgcolor = None
        italic = False
        underline = False
        sel_bgcolor = None
        sel_color = None

        for string, deltas in text.iterchunks():
            color = deltas.get('color', color) or cfg.q_fgcolor
            bgcolor = deltas.get('bgcolor', bgcolor)
            sel_bgcolor = deltas.get('sel_bgcolor', sel_bgcolor)
            sel_color = deltas.get('sel_color', sel_color)
        
            actual_color = sel_color or color
            actual_bgcolor = sel_bgcolor or bgcolor


            new_italic = deltas.get('italic', italic)
            new_underline = deltas.get('underline', underline)

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
                    QRectF(xc, 0, width, fm.lineSpacing()),
                    QColor(actual_bgcolor)
                )
            
            painter.setPen(QColor(actual_color))
            painter.drawText(QPointF(xc, yc), tab_expanded_string)# string)

            xc += width
            raw_col += len(tab_expanded_string)

    return pixmap
            

def draw_attr_text(painter, rect, text, settings, partial=False):
    cache_key = 'codeedit.view.draw_attr_text.pixmap'
    draw_pos_key = 'codeedit.view.draw_attr_text.pos'
    
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
    

