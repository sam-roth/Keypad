import re
import contextlib


from .buffer import TextModification, Buffer


class Cursor(object):

    __slots__ = 'manip', 'buffer', '_pos', '_col_affinity', 'chirality', '__weakref__'

    class Chirality:
        Left = 0  # Inserting text at cursor doesn't move it.
        Right = 1 # Inserting text at cursor moves it.

    def __init__(self, manip, pos=(0,0)):    
        self.manip = manip

        # allow either a buffer or a buffer manipulator through duck typing
        self.buffer = getattr(manip, 'buffer', manip)

        self.buffer.text_modified.connect(self._on_buffer_text_modified)

        self.pos = pos
        self._col_affinity = None
        self.chirality = Cursor.Chirality.Right

        
    def _on_buffer_text_modified(self, change):
        '''
        :type change: keypad.buffer.TextModification
        '''
        
        self_y, self_x = self.pos
        chg_y, chg_x = change.pos
        end_y, end_x = change.insert_end_pos

        t=None

        if change.insert:
            if self.chirality != Cursor.Chirality.Left \
                    or self_y != chg_y or self_x != chg_x:

                if self_y == chg_y and self_x >= chg_x:
                    self_y = end_y
                    self_x = (self_x - chg_x) + end_x
                elif self_y > chg_y:
                    self_y += end_y - chg_y

        if change.remove:
            end_y, end_x = change.inverse.insert_end_pos

            # cursor was in the removed region
            if (chg_y, chg_x) < (self_y, self_x) < (end_y, end_x):
                self_y, self_x = chg_y, chg_x

            # cursor was outside of the removed region
            else:
                
                # cursor was on the last line of the removed region, but outside
                # of the removed region
                if self_y == end_y and self_x >= end_x:
                    self_x = chg_x + (self_x - end_x)
                    self_y = chg_y
                    t = 'last line outside'    
                # cursor was after the last line of the removed region
                elif self_y > end_y:
                    self_y -= end_y - chg_y 
                    t = 'after last line'
        
        try:
            self._set_pos((self_y, self_x))
        except:
            import logging
            logging.exception('Exception while updating cursor position after text modification.')
            raise


    def searchline(self, regex, flags=0):
        return re.search(regex, self.line.text, flags)

    def line_span_matching(self, regex, flags=0, group=0):
        match = self.searchline(regex, flags)
        if match:
            from . import span
            return span.Span(self.clone().move(col=match.start(group)),
                             self.clone().move(col=match.end(group)))

    def line_region_matching(self, regex, flags=0, group=0):
        spans = []
        from . import span
        for match in re.finditer(regex, self.line.text, flags):
            spans.append(span.Span(self.clone().move(col=match.start(group)),
                                   self.clone().move(col=match.end(group))))
        return span.Region(*spans)
        
    def symmetric_walk(self, stride):
        if stride >= 0:
            yield from self.walk(stride)
        else:
            for _ in self.walk(stride):
                yield self.lchar


    def walk(self, stride):
        '''
        Yield successive characters, moving the cursor in the direction implied
        by the sign of the stride given.

        The stride is the number of characters to advance by.

        If either end of the document is reached, the generator will raise StopIteration.
        '''

        # Optimization: hoisted loop invariants, manually, of course
        # Let's hope PyQt gets ported to PyPy soon.

        if stride == 0:
            yield self.rchar
        elif stride > 0:
            while True:
                if self.at_end:
                    break
                else:
                    yield self.rchar
                # inlined from self.advance(stride)
                y, x = value = self.buffer.calculate_pos(self._pos, stride)
                self._col_affinity = None
                lines = self.buffer._lines

                if y >= 0 and x >= 0 and y < len(lines):
                    line = lines[y]
                    if x <= len(line._text):
                        self._pos = value

        else:
            if self.at_end:
                self.advance(stride)
            while True:
                yield self.rchar
                if self.at_start:
                    break
                # inlined from self.advance(stride)
                y, x = value = self.buffer.calculate_pos(self._pos, stride)
                self._col_affinity = None
                lines = self.buffer._lines

                if y >= 0 and x >= 0 and y < len(lines):
                    line = lines[y]
                    if x <= len(line._text):
                        self._pos = value

    def walklines(self, stride):
        '''
        Yield successive lines, moving the cursor in the direction implied by the sign of 
        the stride given.

        The stride is the number of lines to move down by.

        If either end of the document is reached, the generator will raise StopIteration.
        '''
        
        while True:
            yield self.line
            if stride == 0 or stride < 0 and self.y == 0 or \
                    stride > 0 and self.y == len(self.buffer.lines) - 1:
                break
            self.down(stride)

    def opening_brace(self, *, timeout_ms=50):
        if self.buffer.code_model is None:
            raise RuntimeError("Can't find opening brace without code model.")

        new_pos = self.buffer.code_model.open_brace_pos(self.pos, time_limit_ms=timeout_ms)
        if new_pos == self.pos:
            self.advance(-1)
            new_pos = self.buffer.code_model.open_brace_pos(self.pos, time_limit_ms=timeout_ms)
            if new_pos is None:
                self.advance(1)
            elif new_pos == self.pos:
                new_pos = None
        if new_pos is None:
            raise RuntimeError("Already at outermost brace.")

        self.move(new_pos)

        return self
        
    def closing_brace(self, *, timeout_ms=50):
        if self.buffer.code_model is None:
            raise RuntimeError("Can't find closing brace without code model.")
        
        new_pos = self.buffer.code_model.close_brace_pos(self.pos, time_limit_ms=timeout_ms)
        
        if new_pos is None:
            raise RuntimeError("Already at outermost brace.")
        
        self.move(new_pos)
            
        return self
        

    @property
    def lchar(self):
        '''
        The character to the left of the cursor.
        '''
        
        return self.clone().advance(-1).rchar

    @property
    def rchar(self):
        '''
        The character to the right of the cursor.
        '''
        lt = self.line.text
        x = self.x
        if x < len(lt):
            return lt[x] # fast path
        else:
            return self.buffer.span_text(self.pos, offset=1)

    @property
    def rchar_attrs(self):
        return self.line.attributes(self.x)

    @property
    def at_start(self):
        '''
        True iff the cursor cannot advance by any negative number of characters.
        '''
        return self.pos == (0, 0)

    @property
    def past_end(self):
        '''
        True iff the cursor is at the end of the last line in the document.
        '''
        return self.pos > self.buffer.end_pos

    @property
    def at_end(self):
        '''
        True iff the cursor is before the last character in the document or past the end.
        '''
        return self.pos >= self.buffer.end_pos

    @property
    def y(self):
        '''
        The 0-based line number of the cursor.
        '''
        return self.pos[0]

    @property
    def x(self):
        '''
        The 0-based column number of the cursor. (Tabs not expanded.)
        '''
        return self.pos[1]


    @property
    def on_last_line(self):
        return self.y == len(self.buffer.lines) - 1

    @property
    def on_first_line(self):
        return self.y == 0

    @property
    def pos(self):
        '''
        A tuple of ``(y, x)``. See the `y` and `x` properties for details.
        '''
        return self._pos

    @pos.setter
    def pos(self, value):
        self._set_pos(value)


    @contextlib.contextmanager
    def transaction(self):
        '''
        Return a context manager for a history transaction if a BufferHistory has
        been attached to the buffer.
        '''
        h = self.buffer.history
        if h is not None:
            with h.rec_transaction():
                yield
        else:
            yield

    def _set_pos(self, value):
        self._col_affinity = None
        y, x = value
        if y < 0:
            raise IndexError('Line number must be positive')

        try:
            line = self.buffer.lines[y]
        except IndexError:
            raise IndexError('Line {}/{}'.format(y, len(self.buffer.lines)))
        else:
            if x > len(line) or x < 0:
                raise IndexError('Column {}/{}'.format(x, len(line)))
            else:
                self._pos = value

    def _set_pos_fast(self, value):
        self._col_affinity = None
        y, x = value
        if y < 0 or x < 0:
            return

        lines = self.buffer._lines
        if y < len(lines):
            line = lines[y]
            if x <= len(line.text):
                self._pos = value


    def insert(self, text):        
        self.manip.execute(TextModification(pos=self.pos, insert=text))
        return self

    def text_to(self, other):
        start_pos, end_pos = sorted([self.pos, other.pos])
        return self.buffer.span_text(start_pos, end_pos=end_pos)

    def remove_to(self, other):
        start_pos = min(self.pos, other.pos)
        self.manip.execute(TextModification(pos=start_pos, remove=self.text_to(other)))
        return self

    def set_attribute_to(self, other, key, value):
        if other.pos < self.pos:
            self, other = other, self

        self_y, self_x = self.pos
        other_y, other_x = other.pos

        for y, line in enumerate(self.buffer.lines[self_y:other_y+1], self_y):
            start_x = self_x   if y == self_y   else 0
            end_x   = other_x  if y == other_y  else None

            line.set_attributes(start_x, end_x, **{key: value})

        return self

    def advance(self, n=1):
        # inlined from
        # self._set_pos_fast(self.buffer.calculate_pos(self._pos, n))
        y, x = value = self.buffer.calculate_pos(self._pos, n)
        self._col_affinity = None
        lines = self.buffer._lines

        if y < 0 or x < 0:
            return self


        if y < len(lines):
            line = lines[y]
            if x <= len(line._text):
                self._pos = value

        return self

    def delete(self, n=1):
        start_pos = self.buffer.calculate_pos(self.pos, n)
        end_pos = self.pos

        start_pos, end_pos = sorted([start_pos, end_pos])
        
        remove = self.buffer.span_text(start_pos, end_pos=end_pos)
        
        mod = TextModification(pos=start_pos, remove=remove)
        self.manip.execute(mod)

        return self

    def backspace(self, n=1):
        self.delete(-n)
        return self

    def _clone(self, ty):
        result = ty(self.manip).move(*self.pos)
        result.chirality = self.chirality
        return result

    def clone(self):
        return self._clone(Cursor)
        
    def move(self, line=None, col=None):
        if isinstance(line, tuple): # check if line is actually a pair y, x
            if col is not None:
                raise TypeError('too many arguments')
            
            self.pos = line
        else:
            if line is not None and col is not None:
                self.pos = line, col
            elif line is not None:
                self.down(line - self.y)
            elif col is not None:
                self.right(col - self.x)

        return self
    
    @property
    def line(self):
        '''
        The current line of the buffer

        :rtype: keypad.core.AttributedString
        '''
        y, x = self.pos
        return self.buffer.lines[y]

    
    def right(self, n=1):
        y, x = self.pos
        x = max(0, min(len(self.line), x + n))
        self.pos = y, x
    
        return self

    def left(self, n=1):
        return self.right(-n)

    def down(self, n=1):
        y, x = self.pos
        y = max(0, min(len(self.buffer.lines)-1, y + n))
        
        line_length = len(self.buffer.lines[y])

        col_affinity = self._col_affinity

        if col_affinity is not None and col_affinity < line_length:
            x = col_affinity
            col_affinity = None
        elif x > line_length:
            if col_affinity is None:
                col_affinity = x
            x = line_length

        self.pos = y, x
        self._col_affinity = col_affinity

        return self

    def last_line(self):
        y, _ = self.pos
        self.down(len(self.buffer.lines)-(y + 1))
        return self

    def up(self, n=1):
        return self.down(-n)

    def end(self):
        return self.move(col=len(self.line))

    def home(self):
        return self.move(col=0)


    def __repr__(self):
        return 'Cursor{!r}'.format(self.pos)


class ModifiedCursor(Cursor):
    def __init__(self, *args, **kw):
        self.modifiers = []
        super().__init__(*args, **kw)

    def delete(self, n):
        start = self.clone().advance(n)
        start.remove_to(self)
        return self

    @property
    def pos(self):
        return self._pos
    
    @pos.setter
    def pos(self, value):
        for modifier in self.modifiers:
            value = modifier(self, value)
            
        super()._set_pos(value)

    def _clone(self, ty):
        result = super()._clone(ty)
        result.modifiers = self.modifiers.copy()
        return result

    def clone(self):
        return self._clone(ModifiedCursor)
        



def main():
    from .buffer_manipulator import BufferManipulator

    buff = Buffer()
    manip = BufferManipulator(buff)

    curs = Cursor(manip)
        
    with manip.history.transaction():
        curs.insert("Hello,\n")

    print(curs.pos)
    print(buff.dump())
    with manip.history.transaction():
        curs.insert('world!fj')


    print(curs.pos)
    print(buff.dump())

    
    with manip.history.transaction():
        curs.backspace()
        curs.backspace()

    print(curs.pos)
    print(buff.dump())

    curs.pos = 0,0
    with manip.history.transaction():
        curs.insert('abcd')

    print(curs.pos)
    print(buff.dump())


    curs2 = Cursor(manip)
    with manip.history.transaction():
        curs2.remove_to(curs)

    print(curs.pos)
    print(curs2.pos)
    print(buff.dump())

    with manip.history.transaction():
        curs.pos = 0, 6
        curs.delete(1)

    print(curs.pos)
    print(buff.dump())

    manip.history.undo()


    #with manip.history.transaction():
    if True:
        curs.pos = 0, 6
        curs.backspace(1)

    print(curs.pos)
    print(buff.dump())



if __name__ == '__main__':
    main()
    
