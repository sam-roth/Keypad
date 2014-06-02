

from ..qt_util import *
from .viewport import TextViewport
from stem.api import interactive, BufferController

class TextWidget(QAbstractScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._viewport = TextViewport(self)
        self._viewport.origin = QPointF(10, 10)
        self.setViewport(self._viewport)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._viewport.buffer_text_modified.connect(self._update_size)

    def _update_size(self, *args):
        self.verticalScrollBar().setRange(0, len(self.buffer.lines))

    def mousePressEvent(self, event):
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
    from stem.buffers import Buffer
    app = QApplication(sys.argv)

    tw = TextWidget()
    tw.show()
    tw.raise_()

    buf = Buffer()

    buf.insert((0, 0), lorem.text)

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
    



