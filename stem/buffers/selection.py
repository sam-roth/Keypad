
import abc
import contextlib
import re


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


class Selection(object):
    def __init__(self, manip):
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
        
        self.select = Flag()
        self.indent = '    '

    @property
    def insert_cursor(self): 
        return self._insert_cursor

    @property
    def anchor_cursor(self): 
        return self._anchor_cursor

    def _pre_move(self):
        if self.select and not self._anchor_cursor:
            self._anchor_cursor = self._insert_cursor.clone()
            self._anchor_cursor.chirality = self._anchor_cursor.Chirality.Left
        elif not self.select:
            self._anchor_cursor = None

    def _post_move(self):
        pass

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

    @property
    def text(self):
        if not self._anchor_cursor:
            return ''
        else:
            return self._anchor_cursor.text_to(self._insert_cursor)

    @text.setter
    def text(self, value):
        if self._anchor_cursor:
            self._anchor_cursor.remove_to(self._insert_cursor)

        with self.moving():
            self._insert_cursor.insert(value)

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
    

    def tab(self):
        if self._anchor_cursor:
            c = self._anchor_cursor
        else:
            c = self._insert_cursor

        c.insert(self.indent)
        
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


