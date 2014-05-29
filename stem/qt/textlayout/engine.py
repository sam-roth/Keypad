import re
from collections import ChainMap

from PyQt4 import Qt

from stem.core import AttributedString
from stem.util.coordmap import TextCoordMapper
from stem.control import lorem

from ..text_rendering import TextViewSettings, apply_overlay
from ..qt_util import ending, to_q_color

from .textpainter import TextPainter

class TextLayoutEngine:
    def __init__(self, settings=None):
        self._mapper = TextCoordMapper()
        self._settings = settings or TextViewSettings()
        self._tab = re.compile('(\t)')


    def render_line_to_device(self, *, plane_pos, device_pos, 
                              device, text, bgcolor=None, start_col=0,
                              line_id=0, offset=0):
        '''
        :param device_pos: The position on the device to which the line will be rendered.
        :param plane_pos:  The position on the screen, relative to the plane, where the line
                           will eventually be painted.
        :param line_id:    A unique identifier (such as a line number) for this line.
        :param start_col:  The first physical column of the string.
        :param offset:     The first logical column of the string.

        '''
        tstop = self._settings.tab_stop
        line_spacing = Qt.QFontMetricsF(self._settings.q_font).lineSpacing()

        with TextPainter(device=device, settings=self._settings) as tp:
            if bgcolor is not None:
                tp.q_bgcolor = to_q_color(bgcolor)

            p = plane_pos
            d0 = device_pos

            phys_col = start_col

            for chunk, deltas in text.iterchunks():
                for subchunk in self._tab.split(chunk):
                    if not subchunk:
                        continue

                    if subchunk == '\t':
                        # insert the number of spaces required to get to the next tab stop
                        n_tabs = phys_col // tstop
                        next_tabstop = (n_tabs + 1) * tstop
                        rem = next_tabstop - phys_col

                        subchunk_tx = ' ' * rem
                        if subchunk_tx:
                            subchunk_tx = subchunk_tx[:-1] + self._settings.tab_glyph

                        # show tabs using an average of the fg and bg colors
                        color = to_q_color(self._settings.fgcolor.mean(self._settings.bgcolor))
                    else:
                        subchunk_tx = subchunk
                        color = None

                    tp.update_attrs(deltas)
                    d1 = tp.paint_span(d0, subchunk_tx, color=color)
                    w = Qt.QFontMetricsF(self._settings.q_font).width(subchunk_tx)
                    d1 = Qt.QPointF(d0.x() + w, d0.y())

                    # store the region in the mapper, so that mouse positions can be mapped back to text
                    # positions
                    self._mapper.put_region(x=p.x(),
                                            y=p.y(),
                                            char_width=w/len(subchunk),
                                            char_count=len(subchunk),
                                            line_spacing=line_spacing,
                                            line_id=line_id,
                                            offset=int(offset))

                    offset += len(subchunk)
                    phys_col += len(subchunk_tx)
                    p.setX(p.x() + w)
                    d0 = d1


    def transform_line_for_display(self, *, line, width,
                                   overlays=frozenset(),
                                   wrap=False):
        '''
        Return a tuple of AttributedString objects containing the physical lines
        to which the logical line given should be mapped.
        '''

        overlays = frozenset(overlays)
        params = width, overlays, wrap

        cache = line.caches.setdefault(id(self), {})

        if cache.get('transform_params') != params:
            cache['transform_params'] = params
            if overlays:
                overlaid = apply_overlay(line, overlays)
            else:
                overlaid = line

            if wrap:
                # calculate where the string has to be wrapped in order to prevent it from exceeding
                # the window width
                chars_per_line = width // self._settings.char_width
                phys_col = 0
                tstop = self._settings.tab_stop
                prev_split = 0
                split = []
                for i, ch in enumerate(overlaid.text):
                    if phys_col >= chars_per_line:
                        split.append(overlaid[prev_split:i])
                        prev_split = i
                        phys_col -= chars_per_line

                    if ch == '\t':
                        n_tabs = phys_col // tstop
                        next_tabstop = (n_tabs + 1) * tstop
                        rem = next_tabstop - phys_col
                        phys_col += rem
                    else:
                        phys_col += 1

    
                split.append(overlaid[prev_split:])
                phys_lines = tuple(split)
            else:
                phys_lines = (overlaid, )

            cache['transform_result'] = phys_lines

            return phys_lines
        else:
            return cache['transform_result']

    def get_line_pixmap(self, *, plane_pos, line, width, 
                        overlays=frozenset(), wrap=False, 
                        line_id=0, bgcolor=None):

        params_key = 'get_line_pixmap_params'
        pixmap_key = 'get_line_pixmap_pixmap'

        fm = Qt.QFontMetricsF(self._settings.q_font)

        overlays = frozenset(overlays)

        params = (plane_pos.x(), plane_pos.y()), width, overlays, wrap, bgcolor, line_id

        cache = line.caches.setdefault(id(self), {})

        if cache.get(params_key) != params:
            cache[params_key] = params
            lines = self.transform_line_for_display(line=line,
                                                    width=width,
                                                    overlays=overlays,
                                                    wrap=wrap)
            pm = Qt.QPixmap(Qt.QSize(width,
                                     len(lines) * fm.lineSpacing()))


            painter = Qt.QPainter(pm)
            with ending(painter):
                if bgcolor is None:
                    bgcolor = self._settings.q_bgcolor
                else:
                    bgcolor = to_q_color(bgcolor)

                painter.fillRect(pm.rect(), bgcolor)


            offset = 0
            for i, phys_line in enumerate(lines):
                line_plane_pos = Qt.QPointF(plane_pos.x(), plane_pos.y() + i * fm.lineSpacing())

                self.render_line_to_device(plane_pos=line_plane_pos,
                                           device_pos=Qt.QPointF(0, i * fm.lineSpacing()),
                                           device=pm,
                                           text=phys_line,
                                           line_id=line_id,
                                           offset=offset,
                                           bgcolor=bgcolor)


                offset += len(phys_line)

            cache[pixmap_key] = pm

        return cache[pixmap_key]








class TestWidget(Qt.QWidget):

    def __init__(self):
        super().__init__()
    
        layout = Qt.QVBoxLayout(self)

        tle = TextLayoutEngine()
        self.tle = tle

        self.resize(Qt.QSize(1000, 300))
        self.curs = 0,0 
        self.update_pixmap()


    def update_pixmap(self):
        tle = self.tle
        hw = AttributedString(lorem.text.strip())

        tle._mapper.clear()
        y, x = self.curs
        pixmap = tle.get_line_pixmap(plane_pos=Qt.QPointF(0,0),
                                     line=hw,
                                     width=self.width(),
                                     overlays=frozenset([(x, x+1, 'bgcolor', '#FFF')]),
                                     wrap=True)

        self.pixmap = pixmap

    def paintEvent(self, ev):
        self.update_pixmap()
        p = Qt.QPainter(self)
        with ending(p):
            p.drawPixmap(Qt.QPoint(0,0), self.pixmap)


    def event(self, ev):

        if ev.type() in (Qt.QEvent.MouseButtonPress, Qt.QEvent.MouseMove):
            p = ev.pos()
    
            r = self.tle._mapper.map_from_point(p.x(), p.y())
            if r is not None:
                self.curs = r
    
            self.repaint()
        return super().event(ev)

    
refs = []
def test1():
    global refs


    lbl = TestWidget()
    lbl.show()
    lbl.raise_()

    refs += [lbl]

if __name__ == '__main__':
    import sys
    app = Qt.QApplication(sys.argv)
    test1()
    app.exec()












