import weakref

from PyQt4 import Qt as qt

from keypad.core import AttributedString, Color
from keypad.qt.qt_util import ending, restoring, to_q_color
from keypad.qt.options import TextViewSettings

class ParagraphDatum:
    __slots__ = ('layout', 
                 'line',
                 'cartouche',
                 '_carets',
                 '_dirty',
                 '_modified',
                 '_valid_pos',
                 '_overlays',
                 '_overlay_formats',
                 '_bgcolor',
                 'settings',
                 '__weakref__')

    _cache_key = 'qt_tle.ParagraphDatum'

    def __init__(self, layout, settings):
        self.settings = settings
        self.layout = layout
        self.line = None
        self.cartouche = ()
        self._carets = ()
        self._dirty = False
        self._modified = False
        self._valid_pos = None
        self._bgcolor = qt.Qt.white
        self._overlays = ()
        self._overlay_formats = []

    @property
    def carets(self): return self._carets

    @carets.setter
    def carets(self, value):
        tuple_value = tuple(value)
        if tuple_value != self._carets:
            self._carets = tuple_value
            self._dirty = True


    @property
    def overlays(self): return self._overlays
    @overlays.setter
    def overlays(self, value):
        value_tuple = tuple(value)
        if value_tuple != self._overlays:
            self._modified = True
            self._overlays = value_tuple
            self._overlay_formats = list(_overlays_to_formats(value_tuple, self.settings, len(self.line)))

    @property
    def bgcolor(self): return self._bgcolor
    @bgcolor.setter
    def bgcolor(self, value):
        if self._bgcolor != value:
            self._bgcolor = value
            self._modified = True

    def needs_update(self, line, pos):
        if self.line is None or self.line is not line or self._dirty:
            return True
        if self._valid_pos != pos:
            return True

        cache = line.caches.get(ParagraphDatum._cache_key)
        return not cache or cache() is not self

    def update_layout(self, line, pos):
        if self.needs_update(line, pos):
            self.line = line
            line.caches[self._cache_key] = weakref.ref(self)
            self.layout.setText(line.text)

            formats, cartouche = _attrs_to_formats(line, self.settings)
            self.cartouche = cartouche

            self.layout.setAdditionalFormats(formats)
            self._dirty = False
            self._modified = True
            self._valid_pos = pos

    def draw(self, painter, *, only_if_modified=False, bgcolor=None):
        if bgcolor is not None:
            self.bgcolor = bgcolor

        bgcolor = self.bgcolor
        
        if not only_if_modified or self._modified or self._dirty:
            painter.fillRect(self.layout.boundingRect(), bgcolor)

            with restoring(painter):
                self.layout.draw(painter, qt.QPointF(0, 0), self._overlay_formats)
                self._draw_carets(painter)
                self._draw_cartouche(painter)
            self._modified = False

    def _draw_carets(self, painter):
        for caret in self.carets:
            self.layout.drawCursor(painter, qt.QPointF(0,0), caret.pos[1], 2)

    def _draw_cartouche(self, painter):
        with restoring(painter):
            for start, end, value in self.cartouche:
                if value is None:
                    continue

                painter.setPen(to_q_color(value))
                for line in (self.layout.lineAt(i) for i in range(self.layout.lineCount())):
                    if end < line.textStart():
                        break
                    if start > line.textStart() + line.textLength():
                        continue

                    line_end = min(line.textStart() + line.textLength(), end)

                    x1, _ = line.cursorToX(start)
                    x2, _ = line.cursorToX(line_end)
                    y1 = line.y()

                    width = x2 - x1
                    height = line.height()
                    painter.drawRect(x1, y1, width, height)

_format_handlers = {}

def _format_handler(name):
    def acceptor(func):
        _format_handlers[name] = func
        return func
    return acceptor


def _register_format_handlers():
    handler = _format_handler
    @handler('color')
    def set_color(fmt, key, value, state):
        if not state.get('sel_color'): # sel_color takes precedence
            if value:
                if value == 'auto':
                    fmt.setForeground(to_q_color(state['settings'].scheme.selection_fg))
                else:
                    fmt.setForeground(to_q_color(value))
            else:
                fmt.clearForeground()

    @handler('bgcolor')
    def set_bgcolor(fmt, key, value, state):
        if not state.get('sel_bgcolor'):
            if value:
                if value == 'auto':
                    fmt.setBackground(to_q_color(state['settings'].scheme.selection_bg))
                else:
                    fmt.setBackground(to_q_color(value))
            else:
                fmt.clearBackground()

    @handler('sel_bgcolor')
    def set_sel_bgcolor(fmt, key, value, state):
        set_bgcolor(fmt, key, value, state)
        state['sel_bgcolor'] = value

    @handler('sel_color')
    def set_sel_bgcolor(fmt, key, value, state):
        set_color(fmt, key, value, state)
        state['sel_color'] = value

    @handler('italic')
    def set_italic(fmt, key, value, state):
        fmt.setFontItalic(value)

    @handler('underline')
    def set_underline(fmt, key, value, state):
        fmt.setFontUnderline(value)

    @handler('error')
    def set_error(fmt, key, value, state):
        fmt.setUnderlineStyle(qt.QTextCharFormat.SpellCheckUnderline if value
                              else qt.QTextCharFormat.NoUnderline)
        if isinstance(value, (str, Color)):
            fmt.setUnderlineColor(to_q_color(value))
        elif value:
            fmt.setUnderlineColor(qt.QColor(qt.Qt.red))

    @handler('lexcat')
    def set_lexcat(fmt, key, value, state):
        if value is None:
            if 'pre_lexcat' in state:
                old_fmt = state['pre_lexcat']

                for prop in list(fmt.properties().keys()):
                    fmt.clearProperty(prop)

                for prop, value in old_fmt.properties().items():
                    fmt.setProperty(prop, value)

                fmt.merge(state['pre_lexcat'])
                state['lexcat_set'] = False
            return

        if not state.get('lexcat_set'):
            state['pre_lexcat'] = qt.QTextCharFormat(fmt)
            state['lexcat_set'] = True

        settings = state['settings']
        assert isinstance(settings, TextViewSettings)
        for k, v in settings.scheme.lexcat_attrs(value).items():
            try:
                fh = _format_handlers[k]
            except KeyError:
                pass
            else:
                fh(fmt, k, v, state)


_register_format_handlers()

def _attrs_to_formats(text, settings):
    assert isinstance(text, AttributedString)

    result = text.caches.get(id(_attrs_to_formats))
    if result is not None:
        return result
    else:
        formats = []
        cartouche = []
        start = 0
        fmt = qt.QTextCharFormat()
        state = {'settings': settings}
        c_start = 0
        c_value = None
        for chunk, deltas in text.iterchunks():
            for k, v in deltas.items():
                if k == 'cartouche':
                    cartouche.append((c_start, start, c_value))
                    c_start = start
                    c_value = v
                try:
                    handler = _format_handlers[k]
                except KeyError:
                    pass
                else:
                    handler(fmt, k, v, state)

            frange = qt.QTextLayout.FormatRange()
            frange.start = start
            frange.length = len(chunk)
            frange.format = qt.QTextCharFormat(fmt)

            formats.append(frange)

            start += len(chunk)
            
        cartouche.append((c_start, start, c_value))

        cartouche_tuple = tuple(cartouche)
        format_tuple = tuple(formats)
        text.caches[id(_attrs_to_formats)] = format_tuple, cartouche_tuple
        return format_tuple, cartouche_tuple

def _overlays_to_formats(overlays, settings, text_length):
    overlays = sorted(overlays, key=lambda o: o[:2], reverse=True)
    while overlays:
        s, e, _, _ = overlays[-1]
        frange = qt.QTextLayout.FormatRange()
        frange.start = s
        frange.length = e - s
        state = {'settings': settings}
        while overlays and overlays[-1][:2] == (s, e):
            _, _, k, v = overlays.pop()
            try:
                handler = _format_handlers[k]
            except KeyError:
                pass
            else:
                handler(frange.format, k, v, state)
#         print(text_length, e-s)
        if text_length == e - s:
#             frange.format.setProperty(qt.QTextFormat.FullWidthSelection, True)
            frange.length += 1
        yield frange

#
#     for s, e, k, v in sorted(overlays):
#         try:
#             handler = _format_handlers[k]
#         except KeyError:
#             pass
#         else:
#             frange = qt.QTextLayout.FormatRange()
#             frange.start = s
#             frange.length = e - s
#             handler(frange.format, k, v, {'settings':settings})
#             yield frange
# 


