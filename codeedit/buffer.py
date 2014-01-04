
from . import util

class Line(object):
    def __init__(self, text=''):
        #self._blocks = []
        self._text = text

    def _did_change_text(self, index, delta):
        pass

    @property
    def text(self):
        return self._text
    
    def __len__(self):
        return len(self._text)

class Buffer(object):
    def __init__(self):
        self._lines = []
        self._cursor_serial = 0
        self.persistent_cursors = []
        self._canonical_cursor = None

    @property
    def canonical_cursor(self):
        return self._canonical_cursor

    @canonical_cursor.setter
    def canonical_cursor(self, value):
        if value not in self.persistent_cursors:
            self.persistent_cursors.append(value)
        self._canonical_cursor = value

    @property
    def lines(self):
        return util.ImmutableListView(self._lines)

    @classmethod
    def from_text(cls, text):
        self = cls()
        self._lines = list(map(Line, text.splitlines()))
        return self
        
    def dump(self):
        print(70*'=')
        cc = self.canonical_cursor
        for i, line in enumerate(self._lines):
            text = line.text
            if cc is not None and cc.line == i:
                if cc.col < len(text):
                    left = text[:cc.col]
                    center = text[cc.col:cc.col+1]
                    right = text[cc.col+2:]
                    text = left + '\x1b[7m' + center + '\x1b[0m' + right
                else:
                    text += '\x1b[36m\x1b[7m$\x1b[0m'

            print('\x1b[36m{: 4}\x1b[0m {}'.format(i, text.replace(' ',  '\x1b[36m.\x1b[0m')))

    def _did_change_lines(self, curs, index, delta):
        for cursor in self.persistent_cursors:
            if cursor._line >= index and cursor is not curs:
                cursor._line += delta
            cursor._mark_valid()
        
    def _did_change_text(self, curs, line, index, delta):
        self._lines[line]._did_change_text(index, delta)
        for cursor in self.persistent_cursors:
            if cursor._line == line and cursor._col >= index and cursor is not curs:
                cursor._col += delta
            cursor._mark_valid()


    def cursor(self, line=0, col=0):
        result = Cursor(self)
        result.move_to(line, col)
        return result


class Cursor(object):
    def __init__(self, buf):
        '''
        :type buf: codeedit.buffer.Buffer
        '''
        self.buffer = buf
        self._line = 0
        self._col  = 0
        self._mark_valid()
        self.col_affinity = None
    
    def _mark_valid(self):
        self._serial = self.buffer._cursor_serial

    def _mark_all_invalid(self):
        self.buffer._cursor_serial += 1

    def _check_valid(self):
        assert self._serial == self.buffer._cursor_serial, "cursor is invalid"
    
    @property
    def line(self):
        #self._check_valid()
        return self._line

    @property
    def col(self):
        #self._check_valid()
        return self._col


    def _move_to_pos(self, line, col, exact=True):
        if line is not None and line < 0:
            if exact:
                raise IndexError('line %d' % line)
            else:
                line = 0
        if col is not None and col < 0:
            if exact:
                raise IndexError('col %d' % col)
            else:
                col = 0

        self.move_to(line, col, exact)

    def move_to(self, line=None, col=None, exact=True):
        if line is None:
            line = self.line
        
        if col is None:
            if self.col_affinity is not None:
                col = self.col_affinity
                self.col_affinity = None
            else:
                col = self.col
        else:
            self.col_affinity = None


        if line < 0:
            line += len(self.buffer._lines)

        if col < 0:
            col += len(self.buffer._lines[line]) + 1

        
        if line >= len(self.buffer._lines):
            if exact:
                raise IndexError('line %d' % line)
            else:
                line = len(self.buffer._lines) - 1
        
        if col > len(self.buffer._lines[line]):
            if exact:
                raise IndexError('col %d' % col)
            else:
                self.col_affinity = col
                col = len(self.buffer._lines[line])
        
        self._line = line
        self._col = col

        self._mark_valid()

    def move_by(self, down=0, right=0, exact=True):
        self._move_to_pos(self.line + down if down != 0 else None, self.col + right if right != 0 else None, exact)

    def go(self, down=0, right=0):
        self.move_by(down, right, exact=False)

    def go_to(self, line=None, col=None):
        self._move_to_pos(line, col, exact=False)

    def go_to_end(self):
        self.move_to(col=-1, exact=False)

    def go_to_home(self):
        self.move_to(col=0, exact=False)

    def backspace(self):
        try:
            self.move_by(right=-1)
        except IndexError:
            other = self.clone()
            self.go(down=-1)
            self.go_to_end()
            self.remove_until(other)
        else:
            self.remove_until(self)
        

    def insert(self, text):
        lines = text.split('\n')
        if len(lines) == 0:
            return
        elif len(lines) == 1:
            self._insert_in_line(lines[0])
        else:
            first, *rest = lines
            rest_of_first = self.buffer._lines[self.line]._text[self.col:]
            
            end_of_first = self.clone()
            end_of_first.move_to(col=len(self.buffer._lines[self.line]._text))
            self.remove_until(end_of_first)

            self._insert_in_line(first)

            
            for line in rest:
                self.buffer._lines.insert(self.line + 1, Line(line))
                self.buffer._did_change_lines(self, self.line + 1, 1)

                self.move_to(col=0)
                self.move_by(down=1)

            orig_col = self.col
            self.move_to(col=-1)
            self._insert_in_line(rest_of_first)
            self.move_to(col=orig_col)

            self._mark_all_invalid()
            self._mark_valid()

            

    def _insert_in_line(self, text):
        # TODO: handle line breaks
        line = self.buffer._lines[self.line]
           
        left  = line._text[:self.col]
        right = line._text[self.col:]
    
        line._text = left + text + right
        self._mark_all_invalid()
        self.buffer._did_change_text(self, self.line, self.col, len(text))

        self._mark_valid()

        self.move_by(right=len(text))
        

    def remove_until(self, other):
        '''
        Remove the text between this cursor and the other. The character under
        the other cursor will be removed. The other cursor's position will
        be updated.

        :type other: codeedit.buffer.Cursor
        '''

        other_line, other_col = other.line, other.col
        
        if other_line < self.line:
            raise ValueError('Other cursor must be after this cursor.')

        if self.line != other_line:
            del self.buffer._lines[self.line + 1:other_line]
            self.buffer._did_change_lines(self, self.line + 1, -(other_line - self.line - 1))

            other_line = self.line + 1
            
            first_line = self.buffer._lines[self.line]
            first_line_last_index = len(first_line._text) - 1
            first_line._text = first_line._text[:self.col]
            self.buffer._did_change_text(self, self.line, self.col, self.col - first_line_last_index - 1)

            last_line_text = self.buffer._lines[other_line]._text[other_col:]

            del self.buffer._lines[other_line]
            self.buffer._did_change_lines(self, other_line, -1)

            self.insert(last_line_text)
            self.move_by(right=-len(last_line_text))
        else:
            line = self.buffer._lines[self.line]
            left  = line._text[:self.col]
            right = line._text[other_col+1:]
            line._text = left + right
            self.buffer._did_change_text(self, self.line, self.col, self.col - other_col - 1)
       
        self._mark_all_invalid()
        self._mark_valid()

        other.move_to(self.line, self.col)

    def clone(self):
        result = Cursor(self.buffer)
        result.move_to(self.line, self.col)
        return result
