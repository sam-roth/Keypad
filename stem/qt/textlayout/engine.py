import re
from collections import ChainMap

from PyQt4 import Qt

from stem.core import AttributedString
from stem.util.coordmap import TextCoordMapper

from ..text_rendering import TextViewSettings
from ..qt_util import ending, to_q_color

from .textpainter import TextPainter

class TextLayoutEngine:
    def __init__(self, settings=None):
        self._mapper = TextCoordMapper()
        self._settings = settings or TextViewSettings()
        self._tab = re.compile('(\t)')


    def render_line_to_device(self, *, plane_pos, device_pos, 
                              device, text, bgcolor=None, start_col=0,
                              line_id=0):
        tstop = self._settings.tab_stop
        line_spacing = Qt.QFontMetricsF(self._settings.q_font).lineSpacing()

        with TextPainter(device=device, settings=self._settings) as tp:
            if bgcolor is not None:
                tp.q_bgcolor = to_q_color(bgcolor)

            p = plane_pos
            d0 = device_pos
            offset = 0

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
                    w = d1.x() - d0.x()

                    # store the region in the mapper, so that mouse positions can be mapped back to text
                    # positions
                    self._mapper.put_region(x=p.x(),
                                            y=p.y(),
                                            char_width=w/len(subchunk),
                                            char_count=len(subchunk),
                                            line_spacing=line_spacing,
                                            line_id=line_id,
                                            offset=offset)

                    offset += len(subchunk)
                    phys_col += len(subchunk_tx)
                    p.setX(p.x() + w)
                    d0 = d1







class TestWidget(Qt.QWidget):

    def __init__(self):
        super().__init__()
    
        layout = Qt.QVBoxLayout(self)

        tle = TextLayoutEngine()
        self.tle = tle
        pixmap = Qt.QPixmap(Qt.QSize(1000, 300))    

        hw = AttributedString.join([AttributedString('Hello\tab\t, ll', color='#FFF'),
                                    AttributedString('ll!', color='#FF0')])
        tle.render_line_to_device(plane_pos=Qt.QPointF(0, 0),
                                  device_pos=Qt.QPointF(0, 0),
                                  device=pixmap,
                                  text=hw)
    
        self.lbl = lbl = Qt.QLabel(self)
        lbl.setPixmap(pixmap)
        layout.addWidget(lbl)
        self.resize(pixmap.size() + Qt.QSize(10, 10))

        self.tle._mapper.dump()

    def mousePressEvent(self, ev):

        p = self.lbl.mapFromParent(ev.pos())
        print(p)
        print(self.tle._mapper.map_from_point(p.x(), p.y()))
        return super().mousePressEvent(ev)


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












