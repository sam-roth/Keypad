
from PyQt4 import Qt as qt
from keypad.abstract.textview import AbstractCodeView, KeyEvent, MouseEvent, MouseEventKind, MouseButton
from keypad.buffers import Buffer
from keypad.qt.qt_util import ending, restoring, to_q_color, marshal_key_event
from keypad.control import lorem
from keypad.core import AttributedString, Color, Signal
from keypad.api import run_in_main_thread
from keypad.options import GeneralSettings



import collections.abc

from .paragraph import ParagraphDatum

class DefaultList(list):
    def __init__(self, factory):
        super().__init__()
        self.factory = factory

    def resize(self, size):
        while len(self) < size:
            self.append(self.factory())
        if len(self) > size:
            del self[len(self) - size:]

    def get(self, index):
        if len(self) <= index:
            self.resize(index + 1)
        return self[index]

class _Caret:
    def __init__(self, pos):
        self.pos = pos

class _CursorBlinker:
    def __init__(self):
        self._on2off = 500
        self._off2on = 500
        self._state = False
        self._running = False
        self._suppress_next = False
        self._timer_set = False

    @property
    def running(self):
        return self._running

    def stop(self, state=True):
        self._running = False
        self._state = state
        self.cursor_should_blink(self._state)

    def start(self):
        self._running = True
        self._suppress_next = False
        self._set_timer()

    def show_and_suppress_next(self):
        self._state = True
        self._suppress_next = True
        self.cursor_should_blink(True)

    def _on_timeout(self):
        self._timer_set = False
        if self._running:
            self._state = not self._state
            if self._suppress_next:
                self._suppress_next = False
            else:
                self.cursor_should_blink(self._state)
            self._set_timer()
        else:
            self.cursor_should_blink(self._state)

    def _set_timer(self):
        if self._running and not self._timer_set:
            if self._state:
                qt.QTimer.singleShot(self._on2off, self._on_timeout)
            else:
                qt.QTimer.singleShot(self._off2on, self._on_timeout)
            self._timer_set = True


    def set_parameters(self, period, duty_cycle):
        assert 0 <= duty_cycle <= 1
        self._on2off = int(1000 * period * duty_cycle)
        self._off2on = int(1000 * period * (1 - duty_cycle))

    @Signal
    def cursor_should_blink(self, on):
        pass





class ViewImpl(qt.QWidget):
    def __init__(self, settings, *, text_section=True):
        '''
        :type settings: keypad.qt.options.TextViewSettings
        '''
        super().__init__()
        self._genset = GeneralSettings.from_config(settings.config)
        self._genset.value_changed.connect(self._on_settings_reloaded)

        self._buffer = None
        self.buffer = Buffer()
        option = qt.QTextOption(qt.Qt.AlignLeft)
        option.setWrapMode(qt.QTextOption.WrapAtWordBoundaryOrAnywhere)
        option.setUseDesignMetrics(True)

        self.option = option

        def factory():
            layout = qt.QTextLayout()
            font = self.settings.q_font
            layout.setFont(font)
            layout.setTextOption(self.option)
            layout.setCacheEnabled(True)
            return ParagraphDatum(layout, settings)

        self._paragraph_data = DefaultList(factory)
        self._first_line = 0
        self._carets = {}
        self._partial_update_pending = False
        self._force_full_update = False
        self._needs_refresh = True
        self._valid_line_count = 0
        self._overlays = {}
        self._cursor_blinker = _CursorBlinker()
        self._cursor_blinker.cursor_should_blink.connect(self._on_cursor_should_blink)
        self._cursor_blinker.start()
        self._cursors_visible = True
        self._simulate_focus = False

        self.setAttribute(qt.Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(qt.Qt.WA_InputMethodEnabled, True)
        self.setFocusPolicy(qt.Qt.StrongFocus)
        c = self.cursor()
        c.setShape(qt.Qt.IBeamCursor)
        self.setCursor(c)
        self.settings = settings
        self.settings.reloaded.connect(self._on_settings_reloaded)
        self._text_section = text_section

        self._on_settings_reloaded()

    @property
    def simulate_focus(self):
        return self._simulate_focus

    @simulate_focus.setter
    def simulate_focus(self, value):
        self._simulate_focus = value
        self._update_cursor_visibility()

    def focusInEvent(self, event):
        self._update_cursor_visibility()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._update_cursor_visibility()
        super().focusOutEvent(event)

    def _update_cursor_visibility(self):
        if self.hasFocus() or self.simulate_focus:
            self._cursor_blinker.start()
        else:
            self._cursor_blinker.stop(state=True)


    def _on_cursor_should_blink(self, on):
        if on != self._cursors_visible:
            self._cursors_visible = on
            self.refresh()


    @property
    def plane_size(self):
        height = self.last_line - self.first_line
        width = self.width() / self.settings.font_metrics.width('m')

        return height, width

    def set_overlays(self, token, overlays):
        if overlays:
            self._overlays[token] = tuple(overlays)
        else:
            try:
                del self._overlays[token]
            except KeyError:
                pass

        self.refresh()


    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        if self._buffer is not None:
            self._buffer.text_modified.disconnect(self._on_text_modified)

        self._buffer = value

        if self._buffer is not None:
            self._buffer.text_modified.connect(self._on_text_modified)

    def _on_text_modified(self, *args):
        self.refresh()


    def _on_settings_reloaded(self, *args):
        self._cursor_blinker.set_parameters(self._genset.cursor_blink_rate,
                                            self._genset.cursor_duty_cycle)
        font = self.settings.q_font
        for para in self._paragraph_data:
            para.layout.setFont(font)

        self.refresh()
        self.full_update()


    def set_caret(self, token, pos):
        self._cursor_blinker.show_and_suppress_next()
        self._carets[token] = _Caret(pos)
        self.refresh()

    def unset_caret(self, token):
        self._carets.pop(token, None)
        self.refresh()

    @property
    def first_line(self):
        return self._first_line

    @first_line.setter
    def first_line(self, value):
        self._first_line = value
        self.refresh(partial=False)

    @property
    def last_line(self):
        return self._first_line + self._valid_line_count

    def partial_update(self):
        self._partial_update_pending = True
        self.update()

    def full_update(self):
        self._force_full_update = True
        self.update()

    @property
    def _bgcolor(self):
        return (self.settings.q_bgcolor if self._text_section
                else to_q_color(self.settings.scheme.nontext_bg))


    def paintEvent(self, event):
        if self._needs_refresh:
            self._needs_refresh = False
            self._position_layouts()
        painter = qt.QPainter(self)
        partial = self._partial_update_pending and not self._force_full_update
        background = self._bgcolor

        try:
            with ending(painter):
                painter.setRenderHint(qt.QPainter.Antialiasing)
                painter.setPen(self.settings.q_fgcolor)
                if not partial:
                    painter.fillRect(self.rect(), background)

                for i, datum in enumerate(self._paragraph_data[:self._valid_line_count]):
#                     line_bg = background if not datum.carets else to_q_color(self.settings.scheme.cur_line_bg)
                    datum.draw(painter, 
                               only_if_modified=partial)
#                                bgcolor=line_bg)

                r = self.rect()
                if self._paragraph_data and self._valid_line_count != 0:
                    last = self._paragraph_data[self._valid_line_count - 1]
                    ymax = last.layout.boundingRect().bottom()
                    r.setTop(ymax)

                painter.fillRect(r, to_q_color(self.settings.scheme.nontext_bg))
        finally:
            self._partial_update_pending = False
            self._force_full_update = False


    def refresh(self, partial=True):
        self._needs_refresh = True
        if partial:
            self.partial_update()
        else:
            self.update()

    def resizeEvent(self, event):
        self._position_layouts()
        self.full_update()


    def _get_overlays(self):
        for overlay_list in self._overlays.values():
            for span, key, value in overlay_list:
                yield span.start_curs.pos, span.end_curs.pos, key, value

    def _position_layouts(self):
        font = self.font()
        fm = qt.QFontMetricsF(font)

        line_height = fm.height()
        y = 0
        ymax = self.height()
        x = 0
        first_line = self.first_line
        text_section = self._text_section
        cursors_visible = self._cursors_visible
        background = self._bgcolor

        carets = sorted((c for c in self._carets.values()
                         if c.pos[0] >= first_line), 
                        key=lambda c: c.pos,
                        reverse=True)


        # Maintain a set of the currently active overlays. Use the sort-
        # merge join algorithm to make this efficient.

        overlay_start = sorted(((s, e, k, v) for (s, e, k, v) in self._get_overlays()
                                if e[0] >= first_line),
                               key=lambda o: o[0][0],
                               reverse=True)


        overlay_end = sorted(((s, e, k, v) for (s, e, k, v) in self._get_overlays()
                              if e[0] >= first_line),
                             key=lambda o: o[1][0],
                             reverse=True)


        current_overlays = set()

        while overlay_start and overlay_start[-1][0][0] < first_line:
            current_overlays.add(overlay_start.pop())


        i = -1 # for self._valid_line_count
        for i, para in enumerate(self.buffer.lines[self.first_line:]):

            while overlay_start and overlay_start[-1][0][0] == self.first_line + i:
                current_overlays.add(overlay_start.pop())

            datum = self._paragraph_data.get(i)

            datum_overlays = []
            for (sy, sx), (ey, ex), key, val in current_overlays:
                if sy != first_line + i:
                    sx = 0
                if ey != first_line + i:
                    ex = len(para)
                datum_overlays.append((sx, ex, key, val))

            datum.overlays = datum_overlays

            datum.update_layout(para, qt.QPointF(x, y))
            datum.layout.beginLayout()

            line = datum.layout.createLine()

            while line.isValid():
                line.setPosition(qt.QPointF(x, y))
                line.setLineWidth(self.width())

                y += line.height()

                line = datum.layout.createLine()

            datum.layout.endLayout()
            datum_carets = []
            while carets and carets[-1].pos[0] == self.first_line + i:
                datum_carets.append(carets.pop())

            while overlay_end and overlay_end[-1][1][0] == self.first_line + i:
                current_overlays.remove(overlay_end.pop())

            datum.bgcolor = background if not datum_carets else to_q_color(self.settings.scheme.cur_line_bg)
            datum.carets = datum_carets if cursors_visible else []


            if text_section and y >= ymax: # Only text section has an elastic size.
                i -= 1 # this line isn't valid
                break

        if not text_section:
            self.setFixedHeight(y)

        self._valid_line_count = i + 1

#         self.partial_update()


    def _paragraph_at_y(self, y):
        # use binary search to find paragraph
        lo = 0
        hi = self._valid_line_count - 1
        while True:
            mid = (hi + lo) // 2
            r = self._paragraph_data[mid].layout.boundingRect()
            if r.top() <= y < r.bottom():
                # found
                return mid
            elif hi - lo <= 1:
                # map positions after the end to the last line to take advantage of Fitt's law
                return self._valid_line_count - 1
            elif y < r.top():
                hi = mid
            else:
                lo = mid

    def map_to_point(self, y, x):
        if y < self.first_line or y >= self.last_line:
            return None
        else:
            index = y - self.first_line
            datum = self._paragraph_data[index]
            line = datum.layout.lineForTextPosition(x)
            if not line.isValid():
                return None
            else:
                point_y = line.position().y()
                point_x, _ = line.cursorToX(x, qt.QTextLine.Trailing)

                return qt.QPointF(point_x, point_y)

    def map_from_point(self, point):
        index = self._paragraph_at_y(point.y())
        if index is not None:
            line_num = index + self.first_line
            layout = self._paragraph_data[index].layout

            for i in range(layout.lineCount()):
                line = layout.lineAt(i)
                r = line.rect()
                if r.top() <= point.y() < r.bottom():
                    col = line.xToCursor(point.x())
                    return line_num, col
                    
            if layout.lineCount() > 0:
                col = layout.lineAt(layout.lineCount() - 1).xToCursor(point.x())
                return line_num, col

        return None

    def mousePressEvent(self, event):
        event.accept()
        pos = self.map_from_point(event.pos())
        if pos is not None:
            line_num, col = pos
            self.mouse_down_char(line_num, col)
            self.mouse_event(MouseEvent(MouseEventKind.mouse_down,
                                        event.buttons(),
                                        (line_num, col)))

    def mouseMoveEvent(self, event):
        event.accept()
        pos = self.map_from_point(event.pos())
        if pos is not None:
            line_num, col = pos
            self.mouse_move_char(event.buttons(), line_num, col)
            self.mouse_event(MouseEvent(MouseEventKind.mouse_move,
                                        event.buttons(),
                                        (line_num, col)))

    def event(self, event):
        if event.type() == qt.QEvent.InputMethod:
            if event.commitString():
                self.input_method_commit(event.preeditString(),
                                         event.replacementStart(),
                                         event.replacementLength() + event.replacementStart(),
                                         event.commitString())
            else:
                self.input_method_preedit(event.preeditString())
        elif event.type() == qt.QEvent.ShortcutOverride:
            evt = marshal_key_event(event)
            self.should_override_app_shortcut(evt)
            if evt.is_intercepted:
                return True
        elif event.type() == qt.QEvent.KeyPress:
            self.keyPressEvent(event)
            self.key_press(marshal_key_event(event))
            return True


        return super().event(event)

    @Signal
    def mouse_down_char(self, line, col): 
        '''
        Emitted when the left mouse button is pressed.

        :param line: the line number under the mouse cursor
        :param col: the column number under the mouse cursor
        '''

    @Signal
    def mouse_event(self, event):
        '''
        Emitted when any mouse action is performed.

        :type event: MouseEvent
        '''

    @Signal
    def mouse_move_char(self, buttons, line, col):
        '''
        Emitted when the mouse moves.

        .. note::
            This signal may be emitted only while a button is pressed, depending
            on implementation.

        :param buttons: The bitwise OR of the mouse buttons pressed.
        :param line: The line number.
        :param col: The column number.

        :type buttons: bitwise OR of `~MouseButton`
        '''

    @Signal
    def key_press(self, event: KeyEvent):
        '''
        The user pressed a key while the view was focused.
        '''

    @Signal
    def should_override_app_shortcut(self, event: KeyEvent):
        '''
        Emitted before an event is interpreted as an application shortcut.
        To intercept, use the :py:meth:`~KeyEvent.intercept` method.
        '''

    @Signal
    def input_method_preedit(self, text):
        '''
        Optionally emitted by a TextView on receiving a preedit event from
        the OS's input method.

        This is used for implementing compose/dead-key support.
        '''

    @Signal
    def input_method_commit(self, 
                            preedit_text,
                            replace_start, replace_stop,
                            replace_text):
        '''
        Optionally emitted by a TextView on receiving a commit event from
        the OS's input method.

        This is used for implementing compose/dead-key support.
        '''

def styletest(buf):
    from keypad.core import AttributedString, colorscheme
    from keypad.buffers import Cursor

    curs = Cursor(buf)

    def put_sample(attr, val, disp_val=None):
        disp_val = disp_val if disp_val else val
        curs.insert('{:<15} {:<10} '.format(attr, disp_val))
        y,x = curs.pos
        curs.insert('The five boxing wizards jump quickly.')
        curs.line.set_attributes(x, None, **{attr: val})
        curs.insert('\n')

    for attr in 'color bgcolor sel_bgcolor sel_color cartouche'.split():
        put_sample(attr, colorscheme.SolarizedDark._violet, colorscheme.SolarizedDark._violet.hex)

    put_sample('error',         True, 'True')
    put_sample('italic',        True, 'True')
    put_sample('underline',     True, 'True')

if __name__ == "__main__":
    app = qt.QApplication([])

    vi = ViewImpl()
    styletest(vi.buffer)
    vi.set_caret('primary', (0, 2))
    vi.show()
    vi.raise_()

    app.exec()



