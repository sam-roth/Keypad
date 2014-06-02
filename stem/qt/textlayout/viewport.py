
import functools
import collections
import itertools

from ..qt_util import *
from ..text_rendering import TextViewSettings

import enum
import collections

from .engine import TextLayoutEngine
from stem.buffers import Buffer
from stem.core import Signal
from stem.core.attributed_string import RangeDict
from stem.util.coordmap import LinearInterpolator
from stem.options import GeneralSettings

LineID = collections.namedtuple('LineID', 'section number')

class _OverlayManager:
    def __init__(self, overlays, carets):
        self.overlays = list(itertools.chain.from_iterable(overlays.values()))
        self._carets = collections.defaultdict(list)

        for caret_list in carets.values():
            for caret in caret_list:
                y, x = caret.pos
                self._carets[y].append(caret)


    def line(self, i, length):
        for overlay_span, attr_key, attr_val in self.overlays:
            start_pos, end_pos = overlay_span.start_curs.pos, overlay_span.end_curs.pos
    
            start_y, start_x = start_pos
            end_y, end_x = end_pos
            
            if start_y <= i <= end_y:
                line_start_x = 0 if i != start_y else start_x
                line_end_x = length if i != end_y else end_x
    
                yield line_start_x, line_end_x, attr_key, attr_val

    def carets(self, i):
        return self._carets.get(i, [])


class TextViewport(QWidget):

    def __init__(self, parent=None, *, config=None):
        super().__init__(parent)

        self._settings = TextViewSettings(settings=config)
        self._layout_engine = TextLayoutEngine(self._settings)
        self.buffer = Buffer()
        self._origin = QPointF(0, 0)
        self._first_line = 0
        self._line_number_for_y = RangeDict()
        self._line_offsets = {}
        self._right_margin = 5
        self._overlays = {}
        self._carets = {}

        self._general_settings = GeneralSettings.from_config(config)
        self._general_settings.value_changed.connect(self._reload_settings)


        self.setFocusPolicy(Qt.StrongFocus)
        t = self._cursor_blink_on_timer = QTimer(self)
        t.timeout.connect(self._on_cursor_blink_on)

        t = self._cursor_blink_off_timer = QTimer(self)
        t.timeout.connect(self._on_cursor_blink_off)

        for timer in [self._cursor_blink_on_timer,
                      self._cursor_blink_off_timer]:
            timer.setSingleShot(True)

        self._cursor_visible = False
        self._reload_settings()
        self._cursor_blink_on_timer.start()
        

    def _reload_settings(self, *args):
        self._cursor_blink_on_timer.setInterval(self._general_settings.cursor_blink_rate *
                                                (1 - self._general_settings.cursor_duty_cycle) *
                                                1000)
        self._cursor_blink_off_timer.setInterval(self._general_settings.cursor_blink_rate *
                                                 self._general_settings.cursor_duty_cycle *
                                                 1000)

    def _on_cursor_blink_on(self):
        self._cursor_visible = True
        self._cursor_blink_off_timer.start()
        self.update()

    def _on_cursor_blink_off(self):
        self._cursor_visible = False
        self._cursor_blink_on_timer.start()
        self.update()

    def focusInEvent(self, event):
        event.accept()
        self._cursor_blink_off_timer.start()
        self._cursor_visible = True

    def focusOutEvent(self, event):
        event.accept()
        self._cursor_blink_on_timer.stop()
        self._cursor_blink_off_timer.stop()
        self._cursor_visible = False


    def set_overlays(self, token, overlays):
        self._overlays[token] = overlays
        self.update()

    def set_carets(self, token, carets):
        self._carets[token] = tuple(carets)
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

        omgr = _OverlayManager(self._overlays,
                               self._carets)

        cursor_visible = self._cursor_visible

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


                carets = omgr.carets(i) if self._cursor_visible else None

                pm, o = self._layout_engine.get_line_pixmap(plane_pos=plane_pos,
                                                            line=line,
                                                            width=self.width() 
                                                                 - self._origin.x()
                                                                 - self.right_margin,
                                                            overlays=omgr.line(i, len(line)),
                                                            wrap=True,
                                                            line_id=LineID(None, i),
                                                            bgcolor=None,
                                                            carets=carets)
                
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
    
