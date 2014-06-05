import re
from collections import ChainMap

from PyQt4 import Qt

from stem.core import AttributedString
from stem.util.coordmap import TextCoordMapper

from ..text_rendering import TextViewSettings
from ..qt_util import ending, to_q_color, restoring


class TextPainter:
    '''
    Paints text on a QPaintDevice.
    '''
    def __init__(self, *, settings=None, device=None):
        self.settings = settings or TextViewSettings()
        self._metrics = Qt.QFontMetricsF(self.settings.q_font)
        self.device = device
        self.reset()
        self._base_attrs = {
#             'bgcolor': self.settings.q_bgcolor,
#             'color': self.settings.q_fgcolor
        }

        self._cur_lc_attrs = {}
        self._cur_attrs = {}

        self._attrs = ChainMap(self._cur_attrs, self._cur_lc_attrs, self._base_attrs)


    def reset(self):
        self.q_bgcolor = self.settings.q_bgcolor
        self.q_fgcolor = self.settings.q_fgcolor


    def __enter__(self):
        self._painter = Qt.QPainter(self.device)
        self._painter.setFont(self.settings.q_font)
        self._painter.setPen(self.q_fgcolor)
        self._painter.setBrush(self.q_bgcolor)
        return self

    def __exit__(self, *args, **kw):
        self._painter.end()
        self._painter = None

    def update_attrs(self, attrs):
        sentinel = object()

        for k, v in attrs.items():
            if v is None:
                try:
                    del self._cur_attrs[k]
                except KeyError:
                    pass
            else:
                self._cur_attrs[k] = v

        font_changed = 'bold' in attrs or 'italic' in attrs

        lc = attrs.get('lexcat', sentinel)
        if lc is not sentinel:
            font_changed = font_changed or 'bold' in self._cur_lc_attrs or 'italic' in self._cur_lc_attrs
            self._cur_lc_attrs.clear()
            if lc is not None:
                lcattrs = self.settings.scheme.lexical_category_attrs(lc)
                font_changed = font_changed or 'bold' in lcattrs or 'italic' in lcattrs
                self._cur_lc_attrs.update(lcattrs)
                
        sel_color = self._attrs.get('sel_color')
        sel_bgcolor = self._attrs.get('sel_bgcolor')
        if sel_color == 'auto':
            sel_color = self.settings.scheme.selection_fg
        if sel_bgcolor == 'auto':
            sel_bgcolor = self.settings.scheme.selection_bg
        
        self._painter.setPen(to_q_color(sel_color or self._attrs.get('color', self.settings.q_fgcolor)))
        self._painter.setBrush(to_q_color(sel_bgcolor or self._attrs.get('bgcolor', self.settings.q_bgcolor)))

        if font_changed:
            font = Qt.QFont(self._painter.font())
            font.setBold(self._attrs.get('bold') or False)
            font.setItalic(self._attrs.get('italic') or False)
            self._painter.setFont(font)
            self._metrics = Qt.QFontMetricsF(font)


    def paint_bar_caret(self, pos, color=None):
        r = Qt.QRectF(pos, Qt.QSizeF(2, self._metrics.lineSpacing()))

        if color is not None:
            color = to_q_color(color)
        else:
            color = to_q_color(self._attrs.get('color', self.settings.q_fgcolor))

        self._painter.fillRect(r, color)



    def paint_background(self, pos, cells, bgcolor=None):
        r = Qt.QRectF(pos, Qt.QSizeF(cells * self.settings.char_width,
                                     self._metrics.lineSpacing()))

        if (bgcolor is not None 
            and self._attrs.get('sel_bgcolor') is None
            and self._attrs.get('bgcolor') is None):
            bgcolor = to_q_color(bgcolor)
        else:
            bgcolor = self._painter.brush()
        self._painter.fillRect(r, bgcolor)

        return r.topRight()

    def paint_span(self, pos, text, color=None, bgcolor=None):
        ep = self.paint_background(pos, len(text), bgcolor=bgcolor)
        p = Qt.QPointF(pos.x(), self._metrics.ascent() + pos.y())
        if color is not None:
            oldpen = self._painter.pen()
            self._painter.setPen(to_q_color(color))

        self._painter.drawText(p, text)

        if self._attrs.get('error'):
            with restoring(self._painter):
                pen = Qt.QPen(to_q_color('#F00'))
                pen.setWidth(2)

                pen.setStyle(Qt.Qt.DotLine)

                self._painter.setPen(pen)


                self._painter.drawLine(Qt.QLineF(p, Qt.QPointF(ep.x(), p.y())))


        if color is not None:
            self._painter.setPen(oldpen)

        return ep
