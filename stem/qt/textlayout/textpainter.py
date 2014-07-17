import re
from collections import ChainMap

from PyQt4 import Qt

from stem.core import AttributedString
from stem.util.coordmap import TextCoordMapper

from ..options import TextViewSettings
from ..qt_util import ending, to_q_color, restoring

from functools import lru_cache



class TextPainter:
    '''
    Paints text on a QPaintDevice.
    '''
    def __init__(self, *, settings=None, device=None):
        self.settings = settings or TextViewSettings()
        self._metrics = Qt.QFontMetricsF(self.settings.q_font)
        self.device = device
        self.reset()
        self._base_attrs = {}
        self._cur_lc_attrs = {}
        self._cur_attrs = {}

        self._attrs = ChainMap(self._cur_attrs, self._cur_lc_attrs, self._base_attrs)


    def reset(self):
        self.q_bgcolor = self.settings.q_bgcolor
        self.q_fgcolor = self.settings.q_fgcolor


    def __enter__(self):
        '''
        Create the QPainter on the device.
        '''
        self._painter = Qt.QPainter(self.device)
        self._painter.setFont(self.settings.q_font)
        self._painter.setPen(self.q_fgcolor)
        self._painter.setBrush(self.q_bgcolor)
        return self

    def __exit__(self, *args, **kw):
        '''
        End the painter.
        '''
        self._painter.end()
        self._painter = None


    def _make_font(self):
        '''
        Return the current font.
        '''
        font = Qt.QFont(self.settings.q_font)
        font.setBold(self._attrs.get('bold') or False)
        font.setItalic(self._attrs.get('italic') or False)
        font.setUnderline(self._attrs.get('underline') or False)
        return font

    def _make_pen(self):
        '''
        Return the current pen.
        '''
        sel_color = self._attrs.get('sel_color')
        if sel_color == 'auto':
            sel_color = self.settings.scheme.selection_fg

        return Qt.QPen(to_q_color(sel_color 
                                  or self._attrs.get('color',
                                                     self.settings.q_fgcolor)))

    def _make_brush(self):
        '''
        Return the current brush.
        '''
        sel_bgcolor = self._attrs.get('sel_bgcolor')
        if sel_bgcolor == 'auto':
            sel_bgcolor = self.settings.scheme.selection_bg

        return Qt.QBrush(to_q_color(sel_bgcolor 
                                    or self._attrs.get('bgcolor',
                                                       self.settings.q_bgcolor)))

    def update_attrs(self, attrs):
        '''
        Update internal state to reflect the string attributes given.
        '''
        sentinel = object()

        for k, v in attrs.items():
            if v is None:
                try:
                    del self._cur_attrs[k]
                except KeyError:
                    pass
            else:
                self._cur_attrs[k] = v

        lc = attrs.get('lexcat', sentinel)
        if lc is not sentinel:
            self._cur_lc_attrs.clear()
            if lc is not None:
                lcattrs = self.settings.scheme.lexcat_attrs(lc)
                self._cur_lc_attrs.update(lcattrs)

        self._painter.setPen(self._make_pen())
        self._painter.setBrush(self._make_brush())
        self._painter.setFont(self._make_font())


    def paint_bar_caret(self, pos, color=None):
        '''
        Paint a bar-shaped caret in the given position.
        '''
        # Round the values so that the cursor doesn't change width.
        r = Qt.QRect(pos.toPoint(), Qt.QSize(2, self._metrics.lineSpacing()))

        if color is not None:
            color = to_q_color(color)
        else:
            color = to_q_color(self._attrs.get('color', self.settings.q_fgcolor))

        self._painter.fillRect(r, color)



    def paint_background(self, pos, cells, bgcolor=None):
        '''
        Paint the background of the string. This is done automatically when
        using paint_span().
        '''
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
        '''
        Paint a contiguous span of a string with no format changes.
        '''

        ep = self.paint_background(pos, len(text), bgcolor=bgcolor)
        p = Qt.QPointF(pos.x(), self._metrics.ascent() + pos.y() - 1)
        if color is not None:
            oldpen = self._painter.pen()
            self._painter.setPen(to_q_color(color))

        self._painter.drawText(p, text)

        if self.settings.double_strike:
            self._painter.drawText(p, text)
            
        # FIXME: this should merge across spans
        c = self._attrs.get('cartouche')
        if c:
            with restoring(self._painter):
                if c not in (True, 'auto'):
                    self._painter.setPen(to_q_color(c))
                self._painter.setBrush(Qt.Qt.transparent)
                self._painter.drawRect(Qt.QRectF(pos, 
                                                 Qt.QSizeF(ep.x() - p.x() - 2,
                                                           self._metrics.lineSpacing()-2)))


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
