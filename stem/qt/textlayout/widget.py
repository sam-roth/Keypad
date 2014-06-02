

from ..qt_util import *
from .viewport import TextViewport
from stem.api import interactive, BufferController
from stem.buffers import Span
from .engine import Caret
from stem.options import GeneralSettings

class TextWidget(QAbstractScrollArea):
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

    def mousePressEvent(self, event):
        m = self._viewport.map_from_point(event.pos())
        if m is not None:
            (sec, line), col = m

            self._viewport.set_carets('cursor',
                                      [Caret(Caret.Type.bar, (line, col))])
            self._viewport.update()
    
        print(self._viewport.map_from_point(event.pos()))
        return super().mousePressEvent(event)

    @property
    def buffer(self):
        return self._viewport.buffer

    @buffer.setter
    def buffer(self, value):
        self._viewport.buffer = value
        self._update_size()

    def viewportEvent(self, event):
        if event.type() == QEvent.Paint:
            return False # keep Qt from painting over the text
        else:
            return super().viewportEvent(event)


    def scrollContentsBy(self, dx, dy):
        self._viewport.first_line = self.verticalScrollBar().value()


def main():
    import sys
    from stem.control import lorem
    from stem.buffers import Buffer, Cursor
    app = QApplication(sys.argv)

    tw = TextWidget()
    tw.show()
    tw.raise_()

    buf = Buffer()

    buf.insert((0, 0), lorem.text)

    curs = Cursor(buf)
    curs.down()
    curs.line.set_attributes(color='#F00')

    tw.buffer = buf

    tw.viewport().update()
    app.exec()


@interactive('tle')
def tle(bctl: BufferController):
    global tw
    tw = TextWidget()
    tw.show()
    tw.raise_()
    tw.buffer = bctl.buffer
    

if __name__ == '__main__':
    main()
    



