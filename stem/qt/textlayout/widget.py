

from ..qt_util import (Qt, 
                       QAbstractScrollArea,
                       QApplication,
                       QEvent,
                       QFontMetricsF,
                       QFrame,
                       QPoint,
                       QPointF,
                       QMenu,
                       QRect, 
                       QCursor)

from .viewport import TextViewport
from stem.api import interactive, BufferController
from stem.buffers import Span
from .engine import Caret
from stem.options import GeneralSettings
from stem.abstract.textview import (AbstractTextView, 
                                    MouseButton,
                                    AbstractCodeView)

import logging

class TextView(QAbstractScrollArea):
    def __init__(self, parent=None, *, config=None):
        super().__init__(parent)
        self._viewport = TextViewport(self, config=config)
        self._viewport.origin = QPointF(10, 10)
        self.setViewport(self._viewport)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._viewport.buffer_text_modified.connect(self._update_size)
        self._cursor = None

        self._viewport.setFocusProxy(None)
        self.setFocusProxy(self._viewport)
        self.setFrameShape(QFrame.NoFrame)

        self.setAttribute(Qt.WA_StaticContents)
    def _update_size(self, *args):
        self.verticalScrollBar().setRange(0, len(self.buffer.lines))


    @property
    def text_viewport(self):
        return self._viewport

    @property
    def buffer(self):
        return self._viewport.buffer

    @buffer.setter
    def buffer(self, value):
        self._viewport.buffer = value
        self._update_size()

    def viewportEvent(self, event):
        if event.type() == QEvent.Wheel:
            return super().viewportEvent(event)
        else:
            return False

    def scrollContentsBy(self, dx, dy):
        self._viewport.first_line = self.verticalScrollBar().value()


class CodeView(TextView):
    def __init__(self, parent=None, *, config=None):
        super().__init__(parent=parent, config=config)

        from ..call_tip_view import CallTipView
        from ..completion_view import CompletionView

        self._call_tip_view = CallTipView(self._viewport.settings, self)
        self._completion_view = CompletionView(self._viewport.settings, self)

        self._completion_view.installEventFilter(self)


    def viewportEvent(self, event):
        if event.type() == QEvent.FocusOut:
            self._call_tip_view.hide()
        return super().viewportEvent(event)

    def closeEvent(self, ev):
        # HACK: if this isn't done explicitly, the interpreter tends to segfault
        self._call_tip_view.deleteLater()
        self._completion_view.deleteLater()

    def eventFilter(self, obj, ev):
        if obj is self._completion_view:
            if ev.type() == QEvent.Show:
                self._viewport.simulate_focus = True
            elif ev.type() == QEvent.Hide:
                self._viewport.simulate_focus = False

        return super().eventFilter(obj, ev)

    @property
    def completion_view(self): 
        return self._completion_view

    @property
    def call_tip_model(self):
        return self._call_tip_view.model

    def set_call_tip_model(self, value, cursor_pos):

        
        self._call_tip_view.model = value

        line_height = QFontMetricsF(self._viewport.settings.q_font).height()

        p = self._viewport.map_to_point(*cursor_pos)

        if p is None:
            return
            
        x = p.x()
        y = p.y()
        
        line_height = QFontMetricsF(self._viewport.settings.q_font).height()

        rect = QRect()
        rect.setSize(self._call_tip_view.size())
        rect.moveBottomLeft(self.mapToGlobal(QPoint(x, y - line_height)))


        self._call_tip_view.move(rect.topLeft())

        

    def show_completion_view(self, cursor_pos):
        p = self._viewport.map_to_point(*cursor_pos)
        x = p.x()
        y = p.y()

        line_height = QFontMetricsF(self._viewport.settings.q_font).height()

        normal_compl_rect = QRect(self.mapToGlobal(QPoint(x, y + line_height)),
                                  self.completion_view.size())
        intersect = QApplication.desktop().screenGeometry().intersected(normal_compl_rect)
        if intersect != normal_compl_rect:
            normal_compl_rect.moveBottomLeft(
                self.mapToGlobal(
                    QPoint(x, y - line_height)))
        
            
        self.completion_view.move_(normal_compl_rect.topLeft())
        self.completion_view.show()


class TextViewProxyMixin:
    def __init__(self, view):

        self._view = view
        self.__cursor_pos = None

        view._viewport.mouse_move_char.connect(self.mouse_move_char)
        view._viewport.mouse_down_char.connect(self.mouse_down_char)
        view._viewport.key_press.connect(self.key_press)
        view._viewport.should_override_app_shortcut.connect(self.should_override_app_shortcut)
        view._viewport.input_method_preedit.connect(self.input_method_preedit)
        view._viewport.input_method_commit.connect(self.input_method_commit)
        view._viewport.mouse_event.connect(self.mouse_event)

        self.__cursor_visible = True


    def show_context_menu(self, pos, items, *, auto=True):
        '''
        (Optional) Show a context menu with the given items.

        Each item is a pair of its label and a callback.

        The position should be the plane coordinates of a character to
        which to anchor the menu.
        '''

        m = QMenu(self._view)
        for item, action in items:
            m.addAction(item, action)
        if auto:
            m.exec(QCursor.pos())
        else:
            line, col = pos
            global_pos = self._view.text_viewport.mapToGlobal(
                self._view.text_viewport.map_to_point(line, col))
            m.exec(global_pos)


    @property
    def modelines(self):
        return self._view.text_viewport.extra_lines

    @modelines.setter
    def modelines(self, value):
        self._view.text_viewport.extra_lines = value


    @property
    def modelines_visible(self):
        return self._view.text_viewport.extra_lines_visible

    @modelines_visible.setter
    def modelines_visible(self, value):
        self._view.text_viewport.extra_lines_visible = value


    @property
    def buffer(self):
        return self._view.buffer

    @buffer.setter
    def buffer(self, value):
        self._view.buffer = value

    @property
    def cursor_pos(self):
        return self.__cursor_pos

    @cursor_pos.setter
    def cursor_pos(self, value):
        self._set_cursor_pos(value)

    def _set_cursor_pos(self, value):
        self.__cursor_pos = value
        ty = Caret.Type.bar if self.cursor_visible else Caret.Type.off

        self._view._viewport.set_carets('TextViewProxy.cursor',
                                        [Caret(ty, value)] 
                                        if value is not None else [])

    @property
    def first_line(self):
        return self._view._viewport.first_line

    @first_line.setter
    def first_line(self, value):
        self._view.verticalScrollBar().setValue(value)

    @property
    def last_line(self):
        return self._view.text_viewport.last_line

    def set_overlays(self, token, overlays):
        self._view._viewport.set_overlays(token, overlays)

    def update(self):
        self._view._viewport.update()

    @property
    def cursor_visible(self):
        return self.__cursor_visible

    @cursor_visible.setter
    def cursor_visible(self, value):
        self.__cursor_visible = value
        self._set_cursor_pos(self.cursor_pos)

class TextViewProxy(TextViewProxyMixin, AbstractTextView):
    pass


class CodeViewProxyMixin(TextViewProxyMixin):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)


        self.completion_view.key_press.connect(self.key_press)

    @property
    def completion_view(self): 
        return self._view.completion_view
                
    @property
    def call_tip_model(self):
        return self._view.call_tip_model

    @call_tip_model.setter
    def call_tip_model(self, value):
        self._view.set_call_tip_model(value, self.cursor_pos)


    def show_completions(self):
        self._view.show_completion_view(self.cursor_pos)
#         l, c = self.cursor_pos
#         p = self._view._viewport.map_to_point(l, c)
#         p = self._view._viewport.mapToGlobal(p)
# 
#         self.completion_view.visible=True
#         self.completion_view.move_(p)
# 


    def _set_cursor_pos(self, value):
        if value and self.cursor_pos and value[0] != self.cursor_pos[0]:
            self.call_tip_model = None
        super()._set_cursor_pos(value)

    @property
    def plane_size(self):
        return self._view.text_viewport.plane_size

class CodeViewProxy(CodeViewProxyMixin, AbstractCodeView):
    pass


class DummyBufferController:
    def __init__(self):
        from stem.control import lorem
        from stem.buffers import Buffer, Cursor
        self.tv = TextView()
        self.view = TextViewProxy(self.tv)
        self.tv.show()
        self.tv.raise_()    
        buf = Buffer()
    
        buf.insert((0, 0), lorem.text_wrapped)
    
        curs = Cursor(buf)
        curs.down()
        curs.line.set_attributes(color='#F00')

        self.view.buffer = buf

        self.view.mouse_down_char.connect(self.mouse_down_char)
        self.view.mouse_move_char.connect(self.mouse_move_char)
        self.view.key_press.connect(self.key_press)
        self.view.update()



    def key_press(self, event):
        print('got key event', event)

    def mouse_down_char(self, line, col):
        print('mdc', line, col)
        self.view.cursor_pos = line, col

    def mouse_move_char(self, buttons, line, col):
        if buttons & MouseButton.left_button:
            self.view.cursor_pos = line, col

def main():
    import sys

    app = QApplication(sys.argv)

    dbc = DummyBufferController()


    app.exec()
# 
#     tw = TextView()
#     tvp = TextViewProxy(tw)
#     tw.show()
#     tw.raise_()
# 
#     buf = Buffer()
# 
#     buf.insert((0, 0), lorem.text)
# 
#     curs = Cursor(buf)
#     curs.down()
#     curs.line.set_attributes(color='#F00')
# 
#     tw.buffer = buf
# 
#     tw.viewport().update()
#     app.exec()
# 
# 
@interactive('tle')
def tle(bctl: BufferController):
    global dbc
    dbc = DummyBufferController()

    dbc.view.buffer = bctl.buffer
#     tw = TextWidget()
#     tw.show()
#     tw.raise_()
#     tw.buffer = bctl.buffer
    

if __name__ == '__main__':
    main()




