
import abc
import contextlib

class Selection(object):
    def __init__(self, buff):
        '''
        Create a new selection on the given buffer.

        :type buff: stem.buffers.Buffer
        '''

        from .cursor import Cursor

        self.buffer = buff
        
        self._insert_cursor = Cursor(buff)
        self._anchor_cursor = None
        
        self._select = False

    @property
    def insert_cursor(self): 
        return self._insert_cursor

    @property
    def anchor_cursor(self): 
        return self._anchor_cursor

    
    @contextlib.contextmanager
    def select(self):
        '''
        Context manager that corresponds to shift key use.
        '''
        last_select = self._select
        try:
            self._select = True
            yield
        finally:
            self._select = last_select

    def _pre_move(self):
        if self._select and not self._anchor_cursor:
            self._anchor_cursor = self._insert_cursor.clone()
            self._anchor_cursor.chirality = self._anchor_cursor.Chirality.Left
        elif not self._select:
            self._anchor_cursor = None

    def _post_move(self):
        pass

    @contextlib.contextmanager
    def _moving(self):
        try:
            self._pre_move()
            yield
        finally:
            self._post_move()

    def right(self, n=1):
        with self._moving():
            self._insert_cursor.right(n)

    def down(self, n=1):
        with self._moving():
            self._insert_cursor.down(n)

    def move(self, line=None, col=None):
        with self._moving():
            self._insert_cursor.move(line, col)
    
    def advance(self, n=1):
        with self._moving():
            self._insert_cursor.advance(n)

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

        with self._moving():
            self._insert_cursor.insert(value)

