

from ..qt_util import *
from .viewport import TextViewport
from stem.api import interactive, BufferController
from stem.buffers import Span
from .engine import Caret
from stem.options import GeneralSettings
from stem.abstract.textview import AbstractTextView, MouseButton

class TextView(QAbstractScrollArea):
    def __init__(self, parent=None, *, config=None):
        super().__init__(parent)

        self._viewport = TextViewport(self, config=config)
        self._viewport.origin = QPointF(10, 10)
        self.setViewport(self._viewport)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._viewport.buffer_text_modified.connect(self._update_size)
        self._cursor = None


    def _update_size(self, *args):
        self.verticalScrollBar().setRange(0, len(self.buffer.lines))

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
#         if event.type() == QEvent.Paint:
#             return False # keep Qt from painting over the text
#         else:
#             return super().viewportEvent(event)
# 

    def scrollContentsBy(self, dx, dy):
        self._viewport.first_line = self.verticalScrollBar().value()


class TextViewProxy(AbstractTextView):
    def __init__(self, view):

        self.__view = view
        self.__cursor_pos = None

        view._viewport.mouse_move_char.connect(self.mouse_move_char)
        view._viewport.mouse_down_char.connect(self.mouse_down_char)
        view._viewport.key_press.connect(self.key_press)
        view._viewport.should_override_app_shortcut.connect(self.should_override_app_shortcut)

    @property
    def buffer(self):
        return self.__view.buffer

    @buffer.setter
    def buffer(self, value):
        self.__view.buffer = value

    @property
    def cursor_pos(self):
        return self.__cursor_pos

    @cursor_pos.setter
    def cursor_pos(self, value):
        self.__cursor_pos = value
        self.__view._viewport.set_carets('TextViewProxy.cursor',
                                         [Caret(Caret.Type.bar, value)] if value is not None else [])

    @property
    def first_line(self):
        return self.__view._viewport.first_line

    @first_line.setter
    def first_line(self, value):
        self.__view.verticalScrollBar().setValue(value)

    def set_overlays(self, token, overlays):
        self.__view._viewport.set_overlays(token, overlays)

    def update(self):
        self.__view._viewport.update()


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
        self.view.update()



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
    



