from PyQt4 import Qt as qt

from keypad.abstract.textview import AbstractCodeView, CaretType
from keypad.qt.completion_view import CompletionView
from keypad.qt.options import TextViewSettings

from keypad.core import Config
from keypad.options import GeneralSettings
from keypad.buffers import Cursor
from .view_impl import ViewImpl


class NoTabWidget(qt.QWidget):
    def event(self, event):
        if event.type() == qt.QEvent.KeyPress:
            if event.key() == qt.Qt.Key_Tab:
                return True
        return super().event(event)

class _ScrollArea(qt.QAbstractScrollArea):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.settings = TextViewSettings(settings=config)
        self.settings.reloaded.connect(self._settings_change)

        self._create_widgets()
        self._init_layout()

        self.setFocusProxy(self.primary_view)
        self._settings_change()

    def event(self, event):
        if event.type() == qt.QEvent.KeyPress:
            event.ignore()
            return False
        else:
            return super().event(event)

    def _create_widgets(self):
        self.primary_view = ViewImpl(self.settings)
        self.modeline_view = ViewImpl(self.settings, text_section=False)


    def _init_layout(self):
        l = qt.QVBoxLayout(self.viewport())
        l.setContentsMargins(6, 6, 6, 0)
        l.setSpacing(2)

        for w in [self.primary_view, self.modeline_view]:
            l.addWidget(w)

    def _settings_change(self, *args):
        stylesheet = 'background: {};'.format(self.settings.scheme.nontext_bg.css_rgba)
        self.viewport().setStyleSheet(stylesheet)


    def scrollContentsBy(self, dx, dy):
        self.primary_view.first_line = self.verticalScrollBar().value()
        super().scrollContentsBy(dx, dy)

    def update_scroll_range(self, *args):
        self.verticalScrollBar().setRange(0, len(self.primary_view.buffer.lines))


class TextViewProxy(AbstractCodeView):

    def __init__(self, config=Config.root):
        super().__init__()
        self.peer = _ScrollArea(config)

        self.primary = self.peer.primary_view
        self._cursor_pos = (0, 0)
        self._cursor_visible = True
        self._cursor_caret_key = (id(self), 'primary')
        self._completion_view = CompletionView(self.peer.settings)
        self._completion_view.key_press.connect(self.key_press)

        self.primary.mouse_down_char.connect(self.mouse_down_char)
        self.primary.mouse_event.connect(self.mouse_event)
        self.primary.key_press.connect(self.key_press)
        self.primary.mouse_move_char.connect(self.mouse_move_char)
        self.primary.input_method_preedit.connect(self.input_method_preedit)
        self.primary.input_method_commit.connect(self.input_method_commit)

        self.modeline_view = self.peer.modeline_view

        self._update_cursor()
        self._buffer_change(self.buffer)
        self.peer.update_scroll_range()

    def _buffer_change(self, buffer):
        b = self.primary.buffer
        if b is not None:
            b.lines_added_or_removed.disconnect(self.peer.update_scroll_range)
        if buffer is not None:
            buffer.lines_added_or_removed.connect(self.peer.update_scroll_range)


    @property
    def buffer(self):
        '''
        The buffer shown.

        :rtype: `~keypad.buffers.buffer.Buffer`
        '''

        return self.primary.buffer

    @buffer.setter
    def buffer(self, value):
        self._buffer_change(value)
        self.primary.buffer = value
        self.primary.refresh()
        self.primary.full_update()



    @property
    def modelines(self):
        return self.modeline_view.buffer.lines

    @modelines.setter
    def modelines(self, value):
        (Cursor(self.modeline_view.buffer)
         .remove_to(Cursor(self.modeline_view.buffer)
                    .last_line().end()))
        c = Cursor(self.modeline_view.buffer)
        for line in value:
            c.insert(line)
            c.insert('\n')


    @property
    def modelines_visible(self):
        '''
        A boolean value indicating whether the modelines (e.g., ``... [StandardInteractionMode]``)
        should be visible.
        '''

        return False # TODO: implement

    @modelines_visible.setter
    def modelines_visible(self, value):
        pass # TODO: implement

    @property
    def cursor_type(self):
        '''
        The caret type of the text cursor.

        :rtype: CaretType
        '''

        return CaretType.bar # TODO: implement

    @cursor_type.setter
    def cursor_type(self, value):
        pass # TODO: implement

    def _update_cursor(self):
        if self._cursor_pos is None or not self._cursor_visible:
            self.primary.unset_caret(self._cursor_caret_key)
        else:
            self.primary.set_caret(self._cursor_caret_key, self.cursor_pos)

    @property
    def cursor_pos(self):
        '''
        The **text** cursor position.

        :returns: A tuple of (y, x).
        '''

        return self._cursor_pos

    @cursor_pos.setter
    def cursor_pos(self, value):
        '''
        The **text** cursor position.

        :param value: A tuple of (y, x) indicating the new cursor position.
        '''

        self._cursor_pos = value
        self._update_cursor()

    @property
    def cursor_visible(self):
        return self._cursor_visible

    @cursor_visible.setter
    def cursor_visible(self, value):
        self._cursor_visible = value
        self._update_cursor()


    @property
    def first_line(self):
        '''
        The first visible line.
        '''

        return self.primary.first_line

    @first_line.setter
    def first_line(self, value):
        self.peer.verticalScrollBar().setValue(value)


    @property
    def last_line(self):
        '''
        The last visible line (read-only).
        '''

        return self.primary.last_line


    @property
    def plane_size(self):
        return self.primary.plane_size
        


    def set_overlays(self, token, overlays):
        '''
        Give the text specified the requested attributes without modifying the buffer.

        :param token: 
            A unique identifier (of your choosing) that may be used to later
            erase or modify the attributes.

        :param overlays:
            A list of tuples of ``(span, key, value)`` indicating the attributes
            to apply.

        :type token: `object`
        :type overlays: [(`~keypad.buffers.span.Span`, `object`, `object`)]

        '''

        self.primary.set_overlays(token, overlays)

    def update(self):
        '''
        Force redrawing of the entire view.
        '''
        self.primary.refresh()
        self.primary.full_update()

    @property
    def completion_view(self): # FIXME: model should be the property, not view
        '''
        :rtype: keypad.abstract.completion.AbstractCompletionView
        '''

        return self._completion_view


    @property
    def call_tip_model(self):
        pass

    @call_tip_model.setter
    def call_tip_model(self, value):
        pass


    def show_completions(self):
        self._show_completion_view(self.cursor_pos)

    def _show_completion_view(self, cursor_pos):
        p = self.primary.map_to_point(*cursor_pos)
        x = p.x()
        y = p.y()

        line_height = qt.QFontMetricsF(self.primary.settings.q_font).height()

        normal_compl_rect = qt.QRect(self.primary.mapToGlobal(qt.QPoint(x, y + line_height)),
                                     self.completion_view.size())

        screen_geom = qt.QApplication.desktop().screenGeometry()
        
        if normal_compl_rect.bottom() > screen_geom.height():
            normal_compl_rect.moveBottomLeft(
                self.primary.mapToGlobal(
                    qt.QPoint(x, y - line_height)))
        if normal_compl_rect.right() > screen_geom.width():
            normal_compl_rect.moveRight(screen_geom.width())



        self.completion_view.move_(normal_compl_rect.topLeft())
        self.completion_view.show()



from keypad.api import interactive

@interactive('testview')
def testview(_: object):
    view = TextViewProxy()

    from PyQt4 import Qt as qt
    from keypad.plugins.pymodel import make_python_code_model
    from keypad.control import BufferController
    from keypad.control.buffer_controller import lorem
    from keypad.api import app, run_in_main_thread


    view = TextViewProxy()
    bc = BufferController(None, view, view.buffer, config=Config.root)
    with bc.history.transaction():
        bc.replace_from_path('/System/Library/Frameworks/Kernel.framework/Versions/A/Headers/stdint.h')

    view.peer.show()
    view.peer.raise_()
    view.peer.setMinimumSize(300, 300)

    def later():
        for win in app().windows:
            win.close()

    run_in_main_thread(later)

def main():
    from PyQt4 import Qt as qt
    from keypad.plugins.pymodel import PythonCodeModelPlugin
    from keypad.control import BufferController
    from keypad.control.buffer_controller import lorem

    app = qt.QApplication([])

    view = TextViewProxy()
    bc = BufferController(None, view, view.buffer, config=Config.root)
    bc.replace_from_path('/System/Library/Frameworks/Kernel.framework/Versions/A/Headers/stdint.h')
    view.update()


    view.primary.show()
    view.primary.raise_()

    app.exec()

if __name__ == '__main__':
    main()


