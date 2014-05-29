import re
from collections import ChainMap

from PyQt4 import Qt

from stem.core import AttributedString
from stem.util.coordmap import TextCoordMapper

from ..text_rendering import TextViewSettings
from ..qt_util import ending, to_q_color


class TextPainter:
    '''
    Paints text on a QPaintDevice.
    '''
    def __init__(self, *, settings=None, device=None):
        self.settings = settings or TextViewSettings()
        self._metrics = Qt.QFontMetricsF(self.settings.q_font)
        self.device = device
        self.reset()

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

        c = attrs.get('color', sentinel)

        if c is None:
            self._painter.setPen(self.q_fgcolor)
        elif c is not sentinel:
            self._painter.setPen(to_q_color(c))

        c = attrs.get('bgcolor', sentinel)

        if c is None:
            self._painter.setBrush(self.q_bgcolor)
        elif c is not sentinel:
            self._painter.setBrush(to_q_color(c))



    def paint_background(self, pos, cells, bgcolor=None):
        r = Qt.QRectF(pos, Qt.QSizeF(cells * self.settings.char_width,
                                  self._metrics.lineSpacing()))

        if bgcolor is not None:
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
        if color is not None:
            self._painter.setPen(oldpen)

        return ep
