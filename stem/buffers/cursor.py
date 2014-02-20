
from .buffer import TextModification, Buffer

class Cursor(object):

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
        :type change: stem.buffer.TextModification
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
            import pprint
            logging.exception('t=%r pos=%r self_y=%r, self_x=%r, locals=%s', t, self.pos, self_y, self_x, pprint.pprint(locals()))
            raise

    def walk(self, stride):
        '''
        Yield successive characters, moving the cursor in the direction implied
        by the sign of the stride given.

        The stride is the number of characters to advance by.

        If either end of the document is reached, the generator will raise StopIteration.
        '''
        while True:
            pos = self.pos
            yield self.rchar
            if stride == 0 or stride > 0 and self.at_end or stride < 0 and self.at_start:
                break
            self.advance(stride)
        

    @property
    def rchar(self):
        '''
        The character to the right of the cursor.
        '''
        return self.buffer.span_text(self.pos, offset=1)

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
        True iff the cursor is before the last character in the document.
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
    def pos(self):
        '''
        A tuple of ``(y, x)``. See the `y` and `x` properties for details.
        '''
        return self._pos

    @pos.setter
    def pos(self, value):
        self._set_pos(value)


    def _set_pos(self, value):
        self._col_affinity = None
        y, x = value

        try:
            line = self.buffer.lines[y]
        except IndexError:
            raise IndexError('Line {}/{}'.format(y, len(self.buffer.lines)))
        else:
            if x > len(line) or x < 0:
                raise IndexError('Column {}/{}'.format(x, len(line)))
            else:
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
            
            line.set_attribute(start_x, end_x, key, value)
        
        return self

    def advance(self, n=1):
        self.pos = self.buffer.calculate_pos(self.pos, n)
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

        y, x = self.pos

        if isinstance(line, tuple): # check if line is actually a pair y, x
            if col is not None:
                raise TypeError('too many arguments')
            
            y, x = line
        else:
            if line is not None:
                y = line

            if col is not None:
                x = col

        self.pos = y, x

        return self
    
    @property
    def line(self):
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
    
