

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import sys
import contextlib

from .. import signal


@contextlib.contextmanager
def ending(painter):
    try:
        yield painter
    finally:
        painter.end()


class TextView(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        font = QFont('Menlo', 12)
        self.setFont(font)

        self.lines = []
        self._margins = QMargins(4, 4, 4, 4)
        self.update_plane_size()


    @signal.Signal
    def plane_size_changed(self, width, height): pass

    def update_plane_size(self):
        metrics = QFontMetrics(self.font())
        
        m = self._margins
        size = self.size()
        size.setWidth(size.width() - m.left() - m.right())
        size.setHeight(size.height() - m.top() - m.bottom())
        
        width_chars   = size.width() // metrics.width('m')
        height_chars  = size.height() // metrics.height()

#
#        plane_len = len(self.plane)
#        if plane_len < height_chars:
#            self.plane += [[' ' for _ in range(width_chars)] 
#                    for _ in range(height_chars-plane_len)]
#        elif plane_len > height_chars:
#            del self.plane[height_chars:]
#
#        for row in self.plane:
#            row_len = len(row)
#            if row_len < width_chars:
#                row += [' ' for _ in range(width_chars-plane_len)]
#            elif row_len > width_chars:
#                del row[width_chars:]
#
        self.plane_size_changed(width_chars, height_chars)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_plane_size()

    def paintEvent(self, event):
        painter = QPainter(self)
        with ending(painter):
            painter.setBrush(QColor(0, 0, 0, int(255 * 0.90)))
            painter.setPen(Qt.transparent)

            painter.drawRect(self.rect())
            #painter.setBrush(origBrush)

            painter.setPen(Qt.white)
            painter.setBrush(Qt.white)

            x = self._margins.left()

            fm = QFontMetrics(self.font())
            y = fm.height() + self._margins.top()
            height = fm.height()
            for i, row in enumerate(self.lines):
                painter.drawText(QPoint(x, y), row)
                y += height


#    def put_text(self, line, col, text):
#        if line >= len(self.lines):
#            self.lines += ['' for _ in range(line - len(self.lines) + 1)]
#
#        remain = len(self.lines[line]) - col
#        if remain < len(text):
#            raise IndexError('Line too long: %d / %d characters remain.' % (len(text), remain))
#
#        self.plane[line][col:col+len(text)] = text

    



if __name__ == '__main__':

    app = QApplication(sys.argv)

    win = QWidget()
    win.setAttribute(Qt.WA_TranslucentBackground)
    layout = QVBoxLayout(win)
    layout.setContentsMargins(0, 0, 0, 0)
    win.setLayout(layout)

    tv = TextView(win)
    tv.lines.append('Hello, world')
    layout.addWidget(tv)

    
    @tv.plane_size_changed.connect
    def on_plane_size_change(width, height):
        print('New plane size: {}x{}'.format(width, height))

        #tv.put_text(0, 0, 'Hello, world!')

    

    win.show()
    win.resize(640, 480)
    win.raise_()

    
    app.exec_()


