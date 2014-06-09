
import abc
import contextlib
import re

from ..core import Signal
from ..options import GeneralSettings
from ..core.nconfig import Settings, Field

_AdvanceWordRegex = re.compile(
    r'''
      \b 
    | $ 
    | ^ 
    | _                     # for snake_case idents
    | (?<= _ ) \w           #  -> match after "_" too
    | (?<= [a-z] ) [A-Z]    # for camelCase and PascalCase idents
    | ['"]                  # match strings
    | (?<= ['"] ) .         # match after strings
    ''',
    re.VERBOSE
)


class Flag(object):
    def __init__(self):
        self.value = False
    def __bool__(self):
        return self.value
    @contextlib.contextmanager
    def __call__(self):
        oldval = self.value
        try:
            self.value = True
            yield
        finally:
            self.value = oldval

class SelectionSettings(Settings):
    _ns_ = 'selection'

    max_history_entries = Field(int, 10,
                                docs='The maximum number of previous cursor positions to retain')

    history_fuzz_lines = Field(int, 10,
                               docs='The number of lines the cursor needs to move in order to '
                                    'add a new history entry.')

class Selection(object):
    def __init__(self, manip, config):
        '''
        Create a new selection on the given buffer.
        '''

        from .cursor import Cursor
        from .buffer_manipulator import BufferManipulator
        from .buffer import Buffer
        
        self.manip = manip
        if isinstance(manip, BufferManipulator):
            self.buffer = manip.buffer
        elif isinstance(manip, Buffer):
            self.buffer = manip
        else:
            raise TypeError('Must use Buffer or Manipulator for this constructor')
        
        self._insert_cursor = Cursor(manip)
        self._anchor_cursor = None
        self._history = []
        self._future = []

        self.select = Flag()
        self.sel_settings = SelectionSettings.from_config(config)
        self.config = config


    def add_history(self):
        if len(self._history) >= self.sel_settings.max_history_entries:
            del self._history[0]

        add_entry = False
        if not self._history:
            add_entry = True
        else:
            y0, x0 = self._history[-1].pos
            y, x = self.pos

            if abs(y0 - y) >= self.sel_settings.history_fuzz_lines:
                add_entry = True
        
        if add_entry:
            self._future.clear()
            self._history.append(self.insert_cursor.clone())

    def to_previous_position(self):
        if self._history:
            first = True
            while (self._history 
                   and (first
                        or abs(top.pos[0] - self.pos[0])
                           < self.sel_settings.history_fuzz_lines)):
                top = self._history.pop()
                self._future.append(self.insert_cursor.clone())
                first = False
            self.move(top.pos)

    def to_next_position(self):
        if self._future:
            top = self._future.pop()
            self._history.append(self.insert_cursor.clone())
            self.move(top.pos)

    @property
    def history(self):
        return tuple(self._history)

    @property
    def indent(self):
        return GeneralSettings.from_config(self.config).indent_text
    
    @property
    def pos(self):
        return self.insert_cursor.pos

    @pos.setter
    def pos(self, value):
        y, x = value
        self.move(y, x)
        
    @property
    def insert_cursor(self): 
        return self._insert_cursor

    @property
    def anchor_cursor(self): 
        return self._anchor_cursor
        
    @Signal
    def moved(self):
        pass

    def _pre_move(self):
        if self.select and not self._anchor_cursor:
            self._anchor_cursor = self._insert_cursor.clone()
            self._anchor_cursor.chirality = self._anchor_cursor.Chirality.Left
        elif not self.select:
            self._anchor_cursor = None

    def _post_move(self):
        self.moved()

    @contextlib.contextmanager
    def moving(self):
        try:
            self._pre_move()
            yield
        finally:
            self._post_move()

    def advance_word(self, n):
        from ..core.attributed_string import lower_bound

        curs = self._insert_cursor
        line, col = curs.pos
        posns = [match.start() for match in 
                 _AdvanceWordRegex.finditer(curs.line.text)]
        idx = lower_bound(posns, col)
        idx += n
        
        with self.moving():
            if 0 <= idx < len(posns):
                new_col = posns[idx]
                curs.right(new_col - col)
            elif idx < 0 and not curs.on_first_line:
                curs.up().end()
            elif idx > 0 and not curs.on_last_line:
                curs.down().home()
        return self

    def right(self, n=1):
        with self.moving():
            self._insert_cursor.right(n)
        return self

    def down(self, n=1):
        with self.moving():
            self._insert_cursor.down(n)

        return self
    def move(self, line=None, col=None):
        with self.moving():
            self._insert_cursor.move(line, col)
        return self
    
    def advance(self, n=1):
        with self.moving():
            self._insert_cursor.advance(n)
        return self


    def home(self):
        with self.moving():
            self._insert_cursor.home()
        return self

    def end(self):
        with self.moving():
            self._insert_cursor.end()
        return self


    def last_line(self):
        with self.moving():
            self._insert_cursor.last_line()
        return self

    def get_text(self):
        if not self._anchor_cursor:
            return ''
        else:
            return self._anchor_cursor.text_to(self._insert_cursor)

    def set_text(self, value):
        if self._anchor_cursor:
            self._anchor_cursor.remove_to(self._insert_cursor)

        with self.moving():
            self._insert_cursor.insert(value)

        if not value:
            self._anchor_cursor = None

        self.add_history()

    @property
    def text(self): return self.get_text()
    
    @text.setter
    def text(self, value): self.set_text(value)

    def replace(self, text):
        self.text = text
        return self
    
    def delete(self, n=1):
        if not self._anchor_cursor:
            with self.select():
                self.advance(n)

        self.text = ''
        return self

    def clear_selection(self):
        self._anchor_cursor = None

    def advance_para(self, n=1):
        with self.moving():
            skip = True
            c = self._insert_cursor
            for _ in c.walklines(n):
                if c.searchline(r'^\s*$'):
                    if not skip:
                        break       
                else:
                    skip = False
        return self
    

    def tab(self, n=1):
        if self._anchor_cursor:
            first, second = sorted([
                self._insert_cursor,
                self._anchor_cursor
            ], key=lambda c: c.pos)

            c = first.clone()

            for _ in c.walklines(1):
                if c.pos >= second.pos:
                    break

                c.home()

                span = c.line_span_matching(r'^\s*$')
                if span:
                    # if the line is just whitespace, remove its contents
                    span.remove()
                else:
                    # otherwise perform the indentation
                    if n > 0:
                        c.insert(self.indent * n)
                    else:
                        m = c.searchline(r'^\s+')
                        if m:
                            remove_count = min(m.end(), -len(self.indent) * n)
                            c.delete(remove_count)

        else:
            c = self._insert_cursor
            c.insert(self.indent * n)
        
        return self

    def backspace(self):
        return self.delete(-1)

class BacktabMixin(object):
    
    def backspace(self):
        ts = len(self.indent)
        if self.anchor_cursor or \
                not re.match(r'^\s*$', self.insert_cursor.line.text[:self.insert_cursor.x]) or\
                (self.insert_cursor.x % ts) != 0 or\
                self.insert_cursor.x == 0:
            super().backspace()
        else:
            self.delete(-ts)


class BacktabSelection(BacktabMixin, Selection):
    pass