
import functools
import collections

from ..qt_util import *

from .engine import TextLayoutEngine
from stem.buffers import Buffer
from stem.core import Signal
from stem.core.attributed_string import RangeDict
from stem.util.coordmap import LinearInterpolator

LineID = collections.namedtuple('LineID', 'section number')


class TextViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout_engine = TextLayoutEngine()
        self.buffer = Buffer()
        self._first_line = 0
        self._line_number_for_y = RangeDict(1)
        self._line_offsets = {}

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

    def map_from_point(self, point):
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
        self._line_number_for_y = RangeDict(self.height())
        self._line_offsets.clear()

        with ending(painter):
            plane_pos = QPointF(0, 0)

            for i, line in enumerate(self._buffer.lines[self.first_line:],
                                     self.first_line):
                pm, o = self._layout_engine.get_line_pixmap(plane_pos=plane_pos,
                                                            line=line,
                                                            width=self.width(),
                                                            overlays=frozenset(),
                                                            wrap=True,
                                                            line_id=LineID(None, i),
                                                            bgcolor=None)
                
                painter.drawPixmap(plane_pos, pm)

                line_id = LineID(None, i)
                self._line_number_for_y[int(plane_pos.y()):int(plane_pos.y()+pm.height())] = line_id
                self._line_offsets[line_id] = plane_pos.y(), o

                plane_pos.setY(plane_pos.y() + pm.height())
    
                if plane_pos.y() >= self.height():
                    break
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
    
