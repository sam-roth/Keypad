
import functools
import collections
import itertools

from ..qt_util import *
from ..text_rendering import TextViewSettings

from .engine import TextLayoutEngine
from stem.buffers import Buffer
from stem.core import Signal
from stem.core.attributed_string import RangeDict
from stem.util.coordmap import LinearInterpolator

LineID = collections.namedtuple('LineID', 'section number')

class _OverlayManager:
    def __init__(self, overlays):
        self.overlays = list(itertools.chain.from_iterable(overlays.values()))

    def line(self, i, length):
        for overlay_span, attr_key, attr_val in self.overlays:
            start_pos, end_pos = overlay_span.start_curs.pos, overlay_span.end_curs.pos
    
            start_y, start_x = start_pos
            end_y, end_x = end_pos
            
            if start_y <= i <= end_y:
                line_start_x = 0 if i != start_y else start_x
                line_end_x = length if i != end_y else end_x
    
                yield line_start_x, line_end_x, attr_key, attr_val




class TextViewport(QWidget):
    def __init__(self, parent=None, *, settings=None):
        super().__init__(parent)

        self._settings = settings or TextViewSettings()
        self._layout_engine = TextLayoutEngine(settings)
        self.buffer = Buffer()
        self._origin = QPointF(0, 0)
        self._first_line = 0
        self._line_number_for_y = RangeDict()
        self._line_offsets = {}
        self._right_margin = 5
        self._overlays = {}

    def set_overlays(self, token, overlays):
        self._overlays[token] = overlays
        self.update()

    @property
    def right_margin(self):
        return self._right_margin

    @right_margin.setter
    def right_margin(self, value):
        self._right_margin = value
        self.update()

    def _on_text_modified(self, chg):
        self.update()
        self.buffer_text_modified()

    @Signal
    def buffer_text_modified(self):
        pass

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        if hasattr(self, '_buffer'):
            self._buffer.text_modified.disconnect(self._on_text_modified)
        self._buffer = value
        self._buffer.text_modified.connect(self._on_text_modified)
        self.update()

    @property
    def first_line(self):
        return self._first_line

    @first_line.setter
    def first_line(self, value):
        self._first_line = value
        self.update()

    @property
    def origin(self):
        return QPointF(self._origin)

    @origin.setter
    def origin(self, value):
        self._origin = value
        self.update()

    def map_from_point(self, point):
        point = point - self.origin

        line_id = self._line_number_for_y[point.y()]

        y, line_offsets = self._line_offsets[line_id]
        for dy, offsets in line_offsets:
            if y + dy >= point.y():
                col = LinearInterpolator(offsets)(point.x(), saturate=True)
                return line_id, int(col)
        else:
            assert False, 'wrong line was selected by self._line_number_for_y[point.y()]'


    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        self._line_number_for_y = RangeDict()
        self._line_offsets.clear()

        omgr = _OverlayManager(self._overlays)

        with ending(painter):
            if self._origin != QPointF(0, 0):
                painter.fillRect(QRectF(QPointF(0, 0),
                                        QSizeF(self.width(),
                                               self._origin.y())),
                                 self._settings.q_bgcolor)
                painter.fillRect(QRectF(QPointF(0, 0),
                                        QSizeF(self._origin.x(),
                                               self.height())),
                                 self._settings.q_bgcolor)
                painter.fillRect(QRectF(QPointF(self.width() - self.right_margin,
                                                0),
                                        QSizeF(self.right_margin,
                                               self.height())),
                                 self._settings.q_bgcolor)
            plane_pos = QPointF(0, 0)

            for i, line in enumerate(self._buffer.lines[self.first_line:],
                                     self.first_line):

                pm, o = self._layout_engine.get_line_pixmap(plane_pos=plane_pos,
                                                            line=line,
                                                            width=self.width() 
                                                                 - self._origin.x()
                                                                 - self.right_margin,
                                                            overlays=omgr.line(i, len(line)),
                                                            wrap=True,
                                                            line_id=LineID(None, i),
                                                            bgcolor=None)
                
                painter.drawPixmap(plane_pos + self._origin, pm)

                line_id = LineID(None, i)
                self._line_number_for_y[int(plane_pos.y()):int(plane_pos.y()+pm.height())] = line_id
                self._line_offsets[line_id] = plane_pos.y(), o

                plane_pos.setY(plane_pos.y() + pm.height())

                if plane_pos.y() + self._origin.y() >= self.height():
                    break

            if plane_pos.y() + self._origin.y() < self.height():
                topleft = plane_pos + QPointF(0, self._origin.y())
                painter.fillRect(QRectF(topleft,
                                        QSizeF(self.width(),
                                               self.height() - topleft.y())),
                                 to_q_color(self._settings.scheme.nontext_bg))



def main():
    import sys
    from stem.control import lorem

    app = QApplication(sys.argv)

    tw = TextViewport()
    tw.show()
    tw.raise_()

    buf = Buffer()

    buf.insert((0, 0), lorem.text_wrapped)

    tw.buffer = buf


    app.exec()

if __name__ == '__main__':
    main()
    
