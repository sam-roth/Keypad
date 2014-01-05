

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import sys
import contextlib

from .. import signal, attributed_string


@contextlib.contextmanager
def ending(painter):
    try:
        yield painter
    finally:
        painter.end()


@contextlib.contextmanager
def restoring(painter):
    try:
        painter.save()
        yield painter
    finally:
        painter.restore()


#def dummyfunc(*args, **kw): return Dummy()
#
#class Dummy(object):
#    def __getattr__(self, attr):
#        return dummyfunc
#
#
import math

def draw_attr_text(painter, point, text):
    #assert isinstance(text, attributed_string.AttributedString)
    #assert isinstance(painter, QPainter)
    unchanged = object()
    
    with restoring(painter):
        orig_pen = painter.pen()
        orig_brush = painter.brush()

        
        dx = 0
        fm = QFontMetricsF(painter.font()) #painter.fontMetrics()        
        cwidth = fm.width('M')

        print('cwidth={}'.format(cwidth))

        #static_cache = text.caches.get('static_cache')
        #build_static_cache = static_cache is None
        #if build_static_cache:
        #    static_cache = []
        #iter_static_cache = iter(static_cache)


        pixmap_cache = text.caches.get('pixmap_cache')
        if pixmap_cache is None:

            #boundingRectSize = fm.boundingRect(text.text).size()
            #boundingRectSize.setHeight(fm.lineSpacing()+1)

            boundingRectSize = QSizeF(fm.width(text.text), fm.lineSpacing()+1)

            pixmap_cache = QPixmap(boundingRectSize.toSize())
            
            cache_painter = QPainter(pixmap_cache)
            
            with ending(cache_painter):
                cache_painter.setFont(painter.font())
                cache_painter.setPen(painter.pen())
                cache_painter.setBrush(painter.brush())
                with restoring(cache_painter):
                    cache_painter.setCompositionMode(QPainter.CompositionMode_Source)
                    cache_painter.fillRect(pixmap_cache.rect(), QColor(0, 0, 0, int(255*0.9)))

                last_bgcolor = None
                for string, deltas in text.iterchunks():
                    
                    color = deltas.get('color', unchanged)
                    bgcolor = deltas.get('bgcolor', unchanged)

                    width = fm.width(string)
                    #len(string) * cwidth 
                    pos = QPointF(dx, fm.ascent()) #pixmap_cache.height() - fm.descent())
                    
                    with restoring(cache_painter):
                        if bgcolor is None:
                            cache_painter.setBrush(orig_brush)
                        elif bgcolor is not unchanged:
                            last_bgcolor = bgcolor
                        else:
                            bgcolor = last_bgcolor

                        if bgcolor is not None:
                            cache_painter.setBrush(QColor(bgcolor))
                            cache_painter.setPen(Qt.transparent)
                            cache_painter.drawRect(QRectF(
                                QPointF(dx, 0),
                                QSizeF(cwidth * len(string), fm.lineSpacing()+1)
                            ))

                            
                            #cache_painter.drawRect(fm.boundingRect('M'*len(string)).translated(pos))

                    if color is None:
                        cache_painter.setPen(orig_pen)
                    elif color is not unchanged:
                        cache_painter.setPen(QColor(color))

                    #if build_static_cache:
                    #    static_text = QStaticText(string)
                    #    static_text.setTextFormat(Qt.PlainText)
                    #    static_cache.append(static_text)
                    #else:
                    #    static_text = next(iter_static_cache)

                    cache_painter.drawText(pos, string)
                    # CoreText trick for rendering on dark backgrounds
                    #painter.drawText(QPoint(point.x() + dx, point.y() + 1), string) 
                    dx += width
            text.caches['pixmap_cache'] = pixmap_cache

        #painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(point, pixmap_cache)

        #if build_static_cache:
        #    text.caches['static_cache'] = static_cache

    

class TextView(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        font = QFont('Menlo', 14)
        self.setFont(font)

        self.lines = []
        self._margins = QMargins(4, 4, 4, 4)

        self._plane_size = None
        self.update_plane_size()

        self._img_cache = None


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
        
        new_plane_size = (width_chars, height_chars)
        if new_plane_size != self._plane_size:
            self._plane_size = new_plane_size
            self.plane_size_changed(width_chars, height_chars)
            #self._img_cache = QPixmap(self.width(), self.height()) #, QImage.Format_ARGB32)
            #
            #painter = QPainter(self._img_cache)
            #with ending(painter):
            #    painter.setCompositionMode(QPainter.CompositionMode_Source)
            #    painter.fillRect(self._img_cache.rect(), QColor(0, 0, 0, int(255 * 0.90)))
            ##self._img_cache.fill(QColor(0, 0, 0, int(255 * 0.90)))
            #self._paint_to(self._img_cache)

    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_plane_size()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        with ending(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(self.rect(), QColor(0, 0, 0, int(255*0.9)))
        self._paint_to(self)
        #if self._img_cache is not None:
        #    painter.drawPixmap(0, 0, self._img_cache)


    def _paint_to(self, device):
        painter = QPainter(device)
        painter.setFont(self.font())
        with ending(painter):
            #painter.setBrush(QColor(0, 0, 0, int(255 * 0.90)))
            #painter.setPen(Qt.transparent)

            #painter.drawRect(self.rect())

            painter.setPen(Qt.white)
            painter.setBrush(Qt.white)

            x = self._margins.left()

            fm = QFontMetrics(self.font())
            y = self._margins.top()
            height = fm.lineSpacing()+1# + fm.height()
            for i, row in enumerate(self.lines):
                draw_attr_text(painter, QPoint(x, y), row)
                #painter.drawText(QPoint(x, y), row)
                y += height
                if y >= self.height():
                    break



def make_test_attr_str():
    astr = attributed_string.AttributedString('Hello, world!$')
    
    astr.set_attribute(0, 4, 'color', '#FAA')
    astr.set_attribute(7, 12, 'color', '#AAF')
    astr.set_attribute(12, 13, 'color', '#FFA')

    astr.set_attribute(13, 14, 'bgcolor', '#FFF')
    astr.set_attribute(13, 14, 'color', '#000')


    astr.insert(13, '!!')
    
    return astr
    
#if __name__ == '__main__':

def main():

    app = QApplication(sys.argv)

    win = QWidget()
    win.setAttribute(Qt.WA_TranslucentBackground)
    layout = QVBoxLayout(win)
    layout.setContentsMargins(0, 0, 0, 0)
    win.setLayout(layout)

    tv = TextView(win)
    for _ in range(100):
        tv.lines.append(make_test_attr_str())
    layout.addWidget(tv)

    
    @tv.plane_size_changed.connect
    def on_plane_size_change(width, height):
        print('New plane size: {}x{}'.format(width, height))

        #tv.put_text(0, 0, 'Hello, world!')

    win.show()
    win.resize(640, 480)
    win.raise_()

    
    app.exec_()


