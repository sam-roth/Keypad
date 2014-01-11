

from PyQt4.QtCore import *
from PyQt4.QtGui import *



import sys
import contextlib
import math

from .. import signal, attributed_string
from ..key import SimpleKeySequence
from . import consts


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

def qcolor_marshaller(attrname):
    def fget(self):
        # QColor::name() actually returns an HTML-style hex string like
        # #AABBCC.
        return getattr(self, attrname).name()

    def fset(self, value):
        setattr(self, attrname, QColor(value))
    
    return property(fget, fset)



class TextViewSettings(object):
    def __init__(self):
        self.q_font    = QFont('Menlo', 14)
        self.q_bgcolor = QColor.fromRgb(0, 43, 54)
        self.q_fgcolor = QColor.fromRgb(131, 148, 150) 
        self.tab_stop  = 8




    bgcolor = qcolor_marshaller('q_bgcolor')
    fgcolor = qcolor_marshaller('q_fgcolor')

    @property
    def q_font(self):
        return self._q_font

    @q_font.setter
    def q_font(self, value):
        self._q_font = value
        # assume monospace
        fm = QFontMetricsF(value)
        self.char_width = fm.width('X')

    def expand_tabs(self, text):
        return text.expandtabs(self.tab_stop)

    
    

def render_attr_text(text, cfg):
    '''
    Renders the `AttributedString` `text` to a pixmap.

    :type text: codeedit.attributed_string.AttributedString
    :type cfg: codeedit.view.TextViewSettings
    '''

    assert isinstance(cfg, TextViewSettings)

    
    # fonts can have fractional width (at least on OS X) => use -F variant of
    # QFontMetrics
    fm = QFontMetricsF(cfg.q_font)
    
    bounding_rect_size = QSizeF(
        fm.width(cfg.expand_tabs(text.text)) + 1,
        fm.lineSpacing() + 1
    )

    pixmap = QPixmap(bounding_rect_size.toSize())
    #pixmap.setAlphaChannel(QPixmap(bounding_rect_size.toSize()))
    #assert pixmap.hasAlpha()
    
    # current coordinates
    xc = 0.0
    yc = fm.ascent()
    raw_col = 0
    

    painter = QPainter(pixmap)
    with ending(painter):
        painter.setFont(cfg.q_font)
        
        # clear background (may have alpha component, so set appropriate
        # CompositionMode)
        with restoring(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(pixmap.rect(), cfg.q_bgcolor)

        color = None
        bgcolor = None
    
        for string, deltas in text.iterchunks():
            color = deltas.get('color', color) or cfg.q_fgcolor
            bgcolor = deltas.get('bgcolor', bgcolor)
            
            # tab_expanded_string used for width calculations
            offset_from_tstop = raw_col % cfg.tab_stop
            tab_expanded_string = cfg.expand_tabs(' ' * (offset_from_tstop) + string)[offset_from_tstop:]
            width = fm.width(tab_expanded_string)


            # draw background
            if bgcolor is not None:
                painter.fillRect(
                    QRectF(xc, 0, width, fm.lineSpacing()),
                    QColor(bgcolor)
                )
            
            painter.setPen(QColor(color))
            painter.drawText(QPointF(xc, yc), tab_expanded_string)# string)

            xc += width
            raw_col += len(tab_expanded_string)

    return pixmap
            

def draw_attr_text(painter, rect, text, settings, partial=False):
    cache_key = 'codeedit.view.draw_attr_text.pixmap'
    draw_pos_key = 'codeedit.view.draw_attr_text.pos'
    
    pixmap = text.caches.get(cache_key)

    no_cache            = pixmap is None
    should_draw_text    = not partial or no_cache or \
                          text.caches.get(draw_pos_key, None) != rect.topLeft()
    

    if no_cache:
        pixmap = render_attr_text(text, settings)
        text.caches[cache_key] = pixmap
    
    if should_draw_text:
        text.caches[draw_pos_key] = rect.topLeft()
        with restoring(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(rect, settings.q_bgcolor)
        painter.drawPixmap(rect.topLeft(), pixmap)

    return (should_draw_text, no_cache)
    

def draw_attr_text_old(painter, point, text, tab_width=8):
    unchanged = object()
    
    with restoring(painter):
        orig_pen = painter.pen()
        orig_brush = painter.brush()

        
        dx = 0
        fm = QFontMetricsF(painter.font())
        cwidth = fm.width('M')


        pixmap_cache = text.caches.get('pixmap_cache')
        if pixmap_cache is None:
            boundingRectSize = QSizeF(fm.width(text.text.replace('\t', ' '*tab_width)), fm.lineSpacing()+1)
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
                    cursor_after = deltas.get('cursor_after', False)

                    string = string.replace('\t', ' '*tab_width)
                    width = fm.width(string)
                    pos = QPointF(dx, fm.ascent())
                    
                    with restoring(cache_painter):
                        if bgcolor is not unchanged:
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
                        else:
                            cache_painter.setBrush(orig_brush)
                    if color is None:
                        cache_painter.setPen(orig_pen)
                    elif color is not unchanged:
                        cache_painter.setPen(QColor(color))

                    cache_painter.drawText(pos, string)

                    if cursor_after:
                        cache_painter.drawLine(dx + width-1, 0, dx + width-1, pixmap_cache.height())
                    dx += width
            text.caches['pixmap_cache'] = pixmap_cache

        painter.drawPixmap(point, pixmap_cache)


class QtUi(object):

    @classmethod
    def parse_keystroke(cls, ks):
        return QKeySequence.fromString(ks)[0]

    
qtUi = QtUi()


from collections import namedtuple

KeyEvent = namedtuple('KeyEvent', 'key text')

class TextView(QAbstractScrollArea):

    class MouseButtons:
        Left = Qt.LeftButton
        Right = Qt.RightButton
        Middle = Qt.MiddleButton
    

    KeyModifiers = consts.KeyModifiers
    Keys = consts.Keys

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.viewport().setAttribute(Qt.WA_OpaquePaintEvent, True)

        #self.setAttribute(Qt.WA_NoSystemBackground)
        #self.viewport().setAttribute(Qt.WA_NoSystemBackground)
        self.ui = qtUi       
        
        self.settings = TextViewSettings()
        #self.setAttribute(Qt.WA_TranslucentBackground)
        #self.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFont(self.settings.q_font)

        self._lines = []
        self._margins = QMargins(4, 4, 4, 4)

        self._plane_size = None
        self.update_plane_size()

        self._img_cache = None

        self.cursor_pos = None

        self.start_line = 0
        self._partial_redraw_ok = False
        self._prevent_partial_redraw = False
        self._last_cursor_line = None


    @property
    def tab_width(self): return 8

    @signal.Signal
    def plane_size_changed(self, width, height): pass

    @signal.Signal
    def scrolled(self, start_line): pass


    def scroll_to_line(self, line):
        self.verticalScrollBar().setValue(line)

    @property
    def lines(self): return self._lines

    @property
    def plane_size(self): 
        w, h = self._plane_size
        return int(w), int(h)

    @lines.setter
    def lines(self, lines):
        self._lines = lines
        self.update_plane_size()

    def update_plane_size(self):
        metrics = QFontMetricsF(self.font())
        
        m = self._margins
        size = self.size()
        size.setWidth(size.width() - m.left() - m.right())
        size.setHeight(size.height() - m.top() - m.bottom())
        
        self.char_width = metrics.width('m')
        self.line_height = metrics.lineSpacing() + 1

        width_chars   = size.width() // metrics.width('m')
        height_chars  = size.height() // metrics.lineSpacing()
        
        new_plane_size = (width_chars, height_chars)
        if new_plane_size != self._plane_size:
            self._plane_size = new_plane_size
            self.plane_size_changed(width_chars, height_chars)

    def map_to_plane(self, x, y):
        line = int(math.floor((y - self._margins.top()) / self.line_height)) + self.start_line
        raw_col = int(math.floor((x-self._margins.left()) / self.char_width))

        cumulative_raw_cols = 0
        
        try:
            col = 0
            for col, ch in enumerate(self.lines[line].text):
                if cumulative_raw_cols >= raw_col:
                    break

                if ch == '\t':
                    cumulative_raw_cols = int(math.ceil((cumulative_raw_cols+1)/self.tab_width)) * self.tab_width
                else:
                    cumulative_raw_cols += 1
            else:
                col += 1
        except IndexError:
            return line, raw_col
        else:
            return line, col
        
    @signal.Signal
    def mouse_down_char(self, line, col): pass

    @signal.Signal
    def mouse_move_char(self, buttons, line, col): pass

    @signal.Signal
    def key_press(self, event): pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_plane_size()

    def _viewport_paint(self, event):
        #print('paint partial=', self._partial_redraw_ok)
        painter = QPainter(self.viewport())
        area_size = self.viewport().size()
        self.verticalScrollBar().setPageStep(area_size.height())
        self.verticalScrollBar().setRange(0, len(self.lines))

        with ending(painter):
            if not self._partial_redraw_ok:
                painter.setCompositionMode(QPainter.CompositionMode_Source)
                painter.fillRect(self.rect(), self.settings.q_bgcolor)
        self._paint_to(self.viewport())

    def viewportEvent(self, event):
        if event.type() == QEvent.Paint:
            assert isinstance(event, QPaintEvent)
            self._viewport_paint(event)
            return True
        elif event.type() == QEvent.MouseButtonPress:
            line, col = self.map_to_plane(event.x(), event.y())
            self.mouse_down_char(line, col)
            return True
        elif event.type() == QEvent.MouseMove:
            line, col = self.map_to_plane(event.x(), event.y())
            self.mouse_move_char(event.buttons(), line, col)
            return True
        else:
            return super().viewportEvent(event)

    def keyPressEvent(self, event):
        event.accept()
        self.key_press(KeyEvent(key=SimpleKeySequence(modifiers=event.modifiers() & ~Qt.KeypadModifier,
                                                      keycode=event.key()),
                                text=event.text().replace('\r', '\n')))

    
    def scrollContentsBy(self, dx, dy):
        #print('scrollContentsBy')
        self.scrolled(self.verticalScrollBar().value())
        self.viewport().update()
    

    def _paint_to(self, device):
        painter = QPainter(device)
        painter.setFont(self.font())

        if self._prevent_partial_redraw:
            self._partial_redraw_ok = False
            self._prevent_partial_redraw = False

        with ending(painter):
            painter.setPen(Qt.white)
            painter.setBrush(Qt.white)

            x = self._margins.left()

            fm = QFontMetricsF(self.font())
            y = self._margins.top()

            viewport_width = self.viewport().width()

            height = self.line_height #fm.lineSpacing()+1
            
            if self.cursor_pos is not None:
                cursor_line, cursor_col = self.cursor_pos
            else:
                cursor_line, cursor_col = None, None

            lines_drawn = 0
            lines_updated = 0
            
            for i, row in enumerate(self.lines[self.start_line:], self.start_line):
                drew_line, renewed_cache = draw_attr_text(
                    painter, 
                    QRect(QPoint(x, y), QSize(viewport_width, height)),
                    row, 
                    self.settings,
                    partial=(self._partial_redraw_ok and i != self._last_cursor_line))
                if drew_line: lines_drawn += 1
                if renewed_cache: lines_updated += 1

                if i == cursor_line:
                    cursor_x = fm.width(self.settings.expand_tabs(row.text[:cursor_col])) + x
                    #cursor_x = fm.width(row.text[:cursor_col].replace('\t', ' ' * self.tab_width)) + x
                    painter.drawLine(cursor_x, y + 1, cursor_x, y + height - 2)

                y += height
                if y >= self.height():
                    break

            if y < self.height():
                painter.setCompositionMode(QPainter.CompositionMode_Source)
                painter.fillRect(QRect(QPoint(x, y), QSize(self.width() - x, self.height() - y)), self.settings.q_bgcolor)
            #if self._partial_redraw_ok:
            #    print('redrew', lines_drawn, 'lines')
            #print('updated', lines_updated, 'lines')
            self._partial_redraw_ok = False
            self._last_cursor_line = cursor_line
            


    def partial_redraw(self):
        self._partial_redraw_ok = True
        self.viewport().update()
        #self.viewport().repaint()

    def full_redraw(self):
        self._prevent_partial_redraw = True
        #self.viewport().repaint()
        self.viewport().update()



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
        pass
        #print('New plane size: {}x{}'.format(width, height))

        #tv.put_text(0, 0, 'Hello, world!')

    win.show()
    win.resize(640, 480)
    win.raise_()

    
    app.exec_()


