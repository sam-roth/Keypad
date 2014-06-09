
import functools
import collections
import itertools

from ..qt_util import (QApplication,
                       QColor,
                       QEvent,
                       QPainter,
                       QPointF,
                       QRect,
                       QRectF,
                       QSizeF,
                       QTimer,
                       QWidget,
                       ending,
                       to_q_key_sequence,
                       to_q_color,
                       KeyEvent,
                       Qt,
                       marshal_key_event)

from ..options import TextViewSettings

import enum
import collections

from .engine import TextLayoutEngine
from stem.buffers import Buffer
from stem.abstract.textview import MouseButton
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
                line_end_x = max(length, 1) if i != end_y else end_x
    
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
        self._y_for_line_number = {}
        self._line_offsets = {}
        self._right_margin = 5
        self._overlays = {}
        self._carets = {}
        self._last_line = len(self.buffer.lines)
        self._extra_lines = ()
        self._prev_paint_range = (0, 0)

        self.setAttribute(Qt.WA_OpaquePaintEvent)
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

        qc = self.cursor()
        qc.setShape(Qt.IBeamCursor)
        self.setCursor(qc)

        self._simulate_focus = False

        self._extra_lines_visible = True

    @property
    def plane_size(self):
        height = (self.height() - self.origin.y()) / self.settings.line_spacing
        width = (self.width() - self.origin.x()) / self.settings.char_width

        return int(height), int(width)

    @property
    def last_line(self):
        return self._last_line

    @property
    def settings(self):
        return self._settings

    def event(self, event):
        import logging
        if event.type() == QEvent.KeyPress:
            self.key_press(marshal_key_event(event))
            self._cursor_blink_off_timer.stop()
            self._on_cursor_blink_on()
            event.accept()
            return True
        elif event.type() == QEvent.ShortcutOverride:
            ce_evt = marshal_key_event(event)
            self.should_override_app_shortcut(ce_evt)
            if ce_evt.is_intercepted:
                event.accept()
                return True
            else:
                return super().event(event)
        elif event.type() == QEvent.MouseButtonPress:
            m = self.map_from_point(event.pos())
            if m is not None:
                (section, line), col = m
                self.mouse_down_char(line, col)
            return True
        elif event.type() == QEvent.MouseMove:
            m = self.map_from_point(event.pos())
            if m is not None:
                (section, line), col = m
                self.mouse_move_char(event.buttons(), line, col)
            return True

        else:
            if event.type() == QEvent.Resize:
                first, last = self._prev_paint_range
                for line in self.buffer.lines[first:last]:
                    line.invalidate()
                self.update()
            elif event.type() in (QEvent.FocusIn, QEvent.Show):
                self._prev_paint_range = -1, -1
                self.update()

            return super().event(event)




    def _reload_settings(self, *args):
        self._cursor_blink_on_timer.setInterval(self._general_settings.cursor_blink_rate *
                                                (1 - self._general_settings.cursor_duty_cycle) *
                                                1000)
        self._cursor_blink_off_timer.setInterval(self._general_settings.cursor_blink_rate *
                                                 self._general_settings.cursor_duty_cycle *
                                                 1000)


        for line in itertools.chain(self.buffer.lines,
                                    self.extra_lines):
            line.invalidate()

        self.update()

    def _on_cursor_blink_on(self):
        self._cursor_visible = self.hasFocus() or self._simulate_focus
        if self._cursor_visible:
            self._cursor_blink_off_timer.start()
            self.update()

    def _on_cursor_blink_off(self):
        self._cursor_visible = False
        self._cursor_blink_on_timer.start()
        self.update()

    @property
    def simulate_focus(self):
        return self._simulate_focus

    @simulate_focus.setter
    def simulate_focus(self, value):
        self._simulate_focus = value
        self._on_cursor_blink_on()

    def focusInEvent(self, event):
        event.accept()
        self._on_cursor_blink_on()

    def focusOutEvent(self, event):
        event.accept()
        self._on_cursor_blink_on()


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

    @property
    def extra_lines_visible(self):
        return self._extra_lines_visible

    @extra_lines_visible.setter
    def extra_lines_visible(self, value):
        self._extra_lines_visible = value
        self.update()

    @property
    def extra_lines(self):
        return self._extra_lines

    @extra_lines.setter
    def extra_lines(self, value):
        self._extra_lines = tuple(x.clone() for x in value)
        self.update()

    def map_from_point(self, point):
        point = point - self.origin
        if point.y() < 0:
            return LineID(None, max(0, self.first_line-1)), 0
        line_id = self._line_number_for_y[point.y()]

        try:
            y, line_offsets = self._line_offsets[line_id]
        except KeyError:
            y, x = self.buffer.end_pos
            return LineID(None, y), x
            
        for dy, offsets in line_offsets:
            if y + dy >= point.y():
                col = LinearInterpolator(offsets)(point.x(), saturate=True)
                return line_id, int(col)
        else:
            y, x = self.buffer.end_pos
            return LineID(None, min(y, self.last_line + 1)), x


    def map_to_point(self, line, col):
        line_id = LineID(None, line)
        y0, line_offsets = self._line_offsets.get(line_id, (0, ()))
        for dy, offsets in line_offsets:
            if offsets and col >= offsets[0][1] and col <= offsets[-1][1]:
                inv = [(y,x) for (x,y) in offsets]
                x = LinearInterpolator(inv)(col, saturate=True)

                return (QPointF(x, y0 + dy) + self.origin).toPoint()
        else:
            return None



    def paintEvent(self, event):
        FLASH_RERENDER = False

        painter = QPainter(self)

        omgr = _OverlayManager(self._overlays,
                               self._carets)

        cursor_visible = self._cursor_visible

        with ending(painter):
            prev_first_line, prev_last_line = self._prev_paint_range

            normal_bgcolor = self._settings.q_bgcolor

            if self._origin != QPointF(0, 0):
                painter.fillRect(QRectF(QPointF(0, 0),
                                        QSizeF(self.width(),
                                               self._origin.y())),
                                 normal_bgcolor)
#                 painter.fillRect(QRectF(QPointF(0, 0),
#                                         QSizeF(self._origin.x(),
#                                                self.height())),
#                                  self._settings.q_bgcolor)
#                 painter.fillRect(QRectF(QPointF(self.width() - self.right_margin,
#                                                 0),
#                                         QSizeF(self.right_margin,
#                                                self.height())),
#                                  self._settings.q_bgcolor)
            plane_pos = QPointF(0, 0)




            # prerender extra lines
            extra_line_pixmaps = []
            total_extra_line_height = 5

            extra_lines = self.extra_lines if self.extra_lines_visible else []

            for i, extra_line in enumerate(extra_lines):
                pm, _ = self._layout_engine.get_line_pixmap(plane_pos=QPointF(0, 0),
                                                            line=extra_line,
                                                            width=(self.width()
                                                                   - self.origin.x()
                                                                   - self.right_margin),
                                                            overlays=(),
                                                            wrap=True,
                                                            line_id=LineID('extra', i),
                                                            bgcolor=self.settings.scheme.extra_line_bg,
                                                            carets=None)

                extra_line_pixmaps.append(pm)
                total_extra_line_height += pm.height()



            def gen_lines():
                for i, line in enumerate(self._buffer.lines[self.first_line:],
                                         self.first_line):
                    yield LineID(None, i), i, line


            clean_cache_key = str(id(self)) + '.clean'

            for line_id, doc_line_num, line in gen_lines():
                

                clean_rect = line.caches.get(clean_cache_key, None)
                if FLASH_RERENDER:
                    flashlast = line.caches.get('flashlast', False)
                else:
                    flashlast = False

                if doc_line_num is not None:
                    all_carets = omgr.carets(doc_line_num)
                    carets = all_carets if self._cursor_visible else None
                    bgcolor = self._settings.scheme.cur_line_bg if all_carets else None
                    overlays = tuple(omgr.line(doc_line_num, len(line)))
                else:
                    all_carets = ()
                    carets = None
                    bgcolor = None
                    overlays = ()

                params = dict(plane_pos=plane_pos,
                              line=line,
                              width=(self.width()
                                     - self.origin.x()
                                     - self._right_margin),
                              overlays=overlays,
                              wrap=True,
                              line_id=line_id,
                              bgcolor=bgcolor,
                              carets=carets)

                line_clean = ((prev_first_line <= doc_line_num < prev_last_line)
                              and not flashlast
                              and clean_rect is not None
                              and clean_rect.top() == int(plane_pos.y())
                              and self._layout_engine.check_pixmap_clean(**params))

#                 if ((prev_first_line <= doc_line_num <= prev_last_line) 
#                     and clean_rect is not None 
#                     and clean_rect.top() == int(plane_pos.y())): # and not event.rect().contains(clean_rect.toRect()):
                if line_clean:
#                     print('CLEAN', line_id)
                    plane_pos.setY(plane_pos.y() + clean_rect.height())
                else:    
#                     print('DIRTY', line_id)
                    pm, o = self._layout_engine.get_line_pixmap(**params)
#                     pm, o = self._layout_engine.get_line_pixmap(plane_pos=plane_pos,
#                                                                 line=line,
#                                                                 width=self.width() 
#                                                                      - self._origin.x()
#                                                                      - self.right_margin,
#                                                                 overlays=overlays,
#                                                                 wrap=True,
#                                                                 line_id=line_id,
#                                                                 bgcolor=bgcolor,
#                                                                 carets=carets)
#     
    
    

                    if self._origin.x() != 0:
                        if bgcolor is None:
                            bgcolor = normal_bgcolor
                        painter.fillRect(QRectF(QPointF(0, plane_pos.y() + self._origin.y()),
                                                QSizeF(self.width(), pm.height())),
                                         to_q_color(bgcolor))


                    painter.drawPixmap(plane_pos + self._origin, pm)

                    line.caches[clean_cache_key] = QRect((plane_pos).toPoint(),
                                                         pm.size())
                    if FLASH_RERENDER:
                        if not flashlast:
                            painter.fillRect(QRectF(plane_pos + self._origin,
                                                    QSizeF(pm.size())),
                                             QColor.fromRgb(255, 0, 0, 128))
                            line.caches['flashlast'] = True
                        else:
                            line.caches['flashlast'] = False

                    self._line_number_for_y[int(plane_pos.y()):int(plane_pos.y()+pm.height())] = line_id
                    self._y_for_line_number[line_id] = int(plane_pos.y()), int(plane_pos.y() + pm.height())
                    self._line_offsets[line_id] = plane_pos.y(), o
    
                    plane_pos.setY(plane_pos.y() + pm.height())
    
                if (plane_pos.y() + self._origin.y()
                    >= self.height() - total_extra_line_height):
                    self._last_line = doc_line_num
                    break

            else:
                self._last_line = len(self.buffer.lines)


            del self._line_number_for_y[int(plane_pos.y() + self._origin.y()):]

            self._prev_paint_range = self.first_line, self.last_line

            if plane_pos.y() + self._origin.y() < self.height():
                topleft = plane_pos + QPointF(0, self._origin.y())
                topleft.setX(0)

                painter.fillRect(QRectF(topleft,
                                        QSizeF(self.width(),
                                               self.height() - topleft.y())),
                                 to_q_color(self._settings.scheme.nontext_bg))

            elp_pos = QPointF(self._origin.x(),
                              self.height()
                              - total_extra_line_height)
            for elp in extra_line_pixmaps:
                painter.drawPixmap(elp_pos, elp)
                elp_pos.setY(elp_pos.y() + elp.height())

#                 if self._origin.x() != 0:
#                     painter.fillRect(QRectF(QPointF(0, elp_pos.y() + self._origin.y()),
#                                             QSizeF(self._origin.x(), elp.height())),
#                                      to_q_color(self._settings.scheme.extra_line_bg))
        
    @Signal
    def mouse_down_char(self, line, col): pass

    @Signal
    def mouse_move_char(self, buttons, line, col): pass

    @Signal
    def key_press(self, event: KeyEvent): pass

    @Signal
    def should_override_app_shortcut(self, event: KeyEvent): pass

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
    
