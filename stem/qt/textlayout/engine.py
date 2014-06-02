import re
from collections import ChainMap

from PyQt4 import Qt

from stem.core import AttributedString
from stem.core.attributed_string import RangeDict
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


        self._mapper.clear(plane_pos.y(), plane_pos.y() + line_spacing)

        subchunk_offsets = [(device_pos.x(), offset)]

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

                    offset += len(subchunk)
                    phys_col += len(subchunk_tx)
                    p.setX(p.x() + w)
                    d0 = d1

                    subchunk_offsets.append((d0.x(), offset))

        return tuple(subchunk_offsets)

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
                fm = Qt.QFontMetricsF(self._settings.q_font)
                # calculate where the string has to be wrapped in order to prevent it from exceeding
                # the window width
                chars_per_line = int(width / fm.width('x'))
                phys_col = 0
                tstop = self._settings.tab_stop
                prev_split = 0
                split = []
                for i, ch in enumerate(overlaid.text):
                    if phys_col >= chars_per_line:
                        split.append(overlaid[prev_split:i])
                        prev_split = i
                        phys_col = 0

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
        '''
        Return a QPixmap containing the rendered line.
        '''

        params_key = 'get_line_pixmap_params'
        pixmap_key = 'get_line_pixmap_pixmap'
        offset_key = 'offsets'

        fm = Qt.QFontMetricsF(self._settings.q_font)

        overlays = frozenset(overlays)

        params = width, overlays, wrap, bgcolor, line_id

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
            line_offsets = []

            for i, phys_line in enumerate(lines):
                line_plane_pos = Qt.QPointF(plane_pos.x(), plane_pos.y() + i * fm.lineSpacing())

                offsets = self.render_line_to_device(plane_pos=line_plane_pos,
                                                     device_pos=Qt.QPointF(0, i * fm.lineSpacing()),
                                                     device=pm,
                                                     text=phys_line,
                                                     line_id=line_id,
                                                     offset=offset,
                                                     bgcolor=bgcolor)

                line_offsets.append(((i+1) * fm.lineSpacing(), offsets))
                
                offset += len(phys_line)

            cache[pixmap_key] = pm, tuple(line_offsets)


        return cache[pixmap_key]

    def map_from_point(self, point):
        return self._mapper.map_from_point(point.x(), point.y())



