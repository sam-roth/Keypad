
import re
import enum

from collections import ChainMap

from PyQt4 import Qt

from stem.core import AttributedString
from stem.core.attributed_string import RangeDict
from stem.util.coordmap import TextCoordMapper, LinearInterpolator
from stem.control import lorem

from ..options import TextViewSettings
from ..qt_util import ending, to_q_color

from .textpainter import TextPainter


def apply_overlay(text, overlay):
    text = text.clone()

    for start, end, key, value in overlay:
        if end >= len(text):
            text.append(' ' * (end - len(text)))
        text.set_attributes(start, end, **{key: value})

    return text


class CaretType(enum.Enum):
    off = 0
    bar = 1

class Caret:
    Type = CaretType

    __slots__ = 'type', 'pos'

    def __init__(self, type, pos):
        self.type = CaretType(type)
        self.pos = pos

    def __repr__(self):
        return 'Caret({!r}, {!r})'.format(self.type, self.pos)

class TextLayoutEngine:
    def __init__(self, settings=None):
        self._settings = settings or TextViewSettings()
        self._tab = re.compile('(\t)')


    def render_line_to_device(self, *, plane_pos, device_pos, 
                              device, text, bgcolor=None, start_col=0,
                              line_id=0, offset=0, carets=(), pad_width=None):
        '''

        Render an AttributedString to the device. 

        Normally, you should use the get_line_pixmap() method.

        The string must consist of at most one physical line. It will not be wrapped.
        Rendering is always performed: a cache will not be used. If you want to use caching,
        use the get_line_pixmap() method instead.


        :param device_pos: The position on the device to which the line will be rendered.
        :param plane_pos:  The position on the screen, relative to the plane, where the line
                           will eventually be painted.
        :param line_id:    A unique identifier (such as a line number) for this line.
        :param start_col:  The first physical column of the string.
        :param offset:     The first logical column of the string.
        :param pad:        If set, fill the rest of the line with the same bgcolor as the end of
                           the line.

        '''
        tstop = self._settings.tab_stop
        line_spacing = Qt.QFontMetricsF(self._settings.q_font).lineSpacing()
        fm = Qt.QFontMetricsF(self._settings.q_font)


        subchunk_offsets = [(device_pos.x(), offset)]

        bar_carets = sorted([c.pos[1] for c in carets 
                             if c.type == CaretType.bar
                             and offset <= c.pos[1] <= offset + len(text)], reverse=True)

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
                    d1 = tp.paint_span(d0, subchunk_tx, color=color, bgcolor=bgcolor)

                    w = fm.width(subchunk_tx)
                    d1 = Qt.QPointF(d0.x() + w, d0.y())

                    while bar_carets and offset <= bar_carets[-1] < offset + len(subchunk):
                        tp.paint_bar_caret(Qt.QPointF(d0.x() + fm.width(subchunk[:bar_carets[-1] - offset]),
                                                      d0.y()))

                        bar_carets.pop()
                        


                    offset += len(subchunk)
                    phys_col += len(subchunk_tx)
                    p.setX(p.x() + w)
                    d0 = d1

                    subchunk_offsets.append((d0.x(), offset))
                if pad_width is not None:
                    width = (pad_width - d0.x()) // fm.width('x')
                    tp.paint_background(d0, width, bgcolor=bgcolor)


            while bar_carets and bar_carets[-1] == offset:
                tp.paint_bar_caret(d0)
                bar_carets.pop()
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

    def check_pixmap_clean(self, *, plane_pos, line, width,
                        overlays=frozenset(), wrap=False, 
                        line_id=0, bgcolor=None, carets=None):
        '''
        Return true if the line has not changed since the last time it was drawn.

        This is useful if you don't want to redraw unchanged lines.
        '''
        carets = tuple(carets or ())

        params_key = 'get_line_pixmap_params'

        fm = Qt.QFontMetricsF(self._settings.q_font)

        overlays = frozenset(overlays)

        params = width, overlays, wrap, bgcolor, line_id, carets

        cache = line.caches.setdefault(id(self), {})

        return cache.get(params_key) == params
            
    def get_line_pixmap(self, *, plane_pos, line, width, 
                        overlays=frozenset(), wrap=False, 
                        line_id=0, bgcolor=None, carets=None):
        '''
        Return a tuple of ``(QPixmap, [(y, [(x, col)])])`` containing the rendered line
        and the offsets of each line and of each evenly spaced region of characters
        in the line.

        If the line hasn't changed since the last time this method was called, a
        cached pixmap will be returned.

        Use a :py:class:`stem.util.coordmap.LinearInterpolator` to find the
        column for a given (x, y) position on the screen.
        '''

        carets = tuple(carets or ())

        params_key = 'get_line_pixmap_params'
        pixmap_key = 'get_line_pixmap_pixmap'
        offset_key = 'offsets'

        fm = Qt.QFontMetricsF(self._settings.q_font)

        overlays = frozenset(overlays)

        params = width, overlays, wrap, bgcolor, line_id, carets

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
                                                     bgcolor=bgcolor,
                                                     carets=carets)

                line_offsets.append(((i+1) * fm.lineSpacing(), offsets))
                
                offset += len(phys_line)

            cache[pixmap_key] = pm, tuple(line_offsets)


        return cache[pixmap_key]



