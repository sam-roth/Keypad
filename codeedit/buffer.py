
from . import util


#class Block(object):
#    def __init__(self, text='', attrs={}):
#        self._text = text
#        self.attrs = attrs
#
#    @property
#    def text(self):
#        return self._text
    
class Line(object):
    def __init__(self, text=''):
        #self._blocks = []
        self._text = text

    def _did_change_text(self, index, delta):
        pass


    @property
    def text(self):
        return self._text

#    @property
#    def blocks(self):
#        return util.ImmutableListView(self._blocks)
#
#    def block(self, index):
#        accum = 0
#        for i, block in enumerate(self._blocks):
#            start = accum
#            accum += len(block.text)
#            if accum >= index:
#                return i, block, start, accum
    
    def __len__(self):
        return len(self._text)
        #return sum(len(region.text) for region in self._regions)

class Buffer(object):
    def __init__(self):
        self._lines = []
        self._cursor_serial = 0

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
        for i, line in enumerate(self._lines):
            print('\x1b[36m{: 4}\x1b[0m {}'.format(i + 1, line.text.replace(' ', '\x1b[36m.\x1b[0m')))


class Cursor(object):
    def __init__(self, buf):
        '''
        :type buf: codeedit.buffer.Buffer
        '''
        self.buffer = buf
        self._line = 0
        self._col  = 0
        self._mark_valid()
    
    def _mark_valid(self):
        self._serial = self.buffer._cursor_serial

    def _mark_all_invalid(self):
        self.buffer._cursor_serial += 1

    def _check_valid(self):
        assert self._serial == self.buffer._cursor_serial, "cursor is invalid"
    
    @property
    def line(self):
        self._check_valid()
        return self._line

    @property
    def col(self):
        self._check_valid()
        return self._col

    def move_to(self, line=0, col=0):
        if line != self._line and (line < 0 or line >= len(self.buffer._lines)):
            raise IndexError('line %d' % line)
        
        if col != self._col and (col < 0 or col > len(self.buffer._lines[line])):
            raise IndexError('col %d' % col)
        
        self._line = line
        self._col = col

        self._mark_valid()

    def move_by(self, down=0, right=0):
        self.move_to(self.line + down, self.col + right)

    def insert(self, text):
        # TODO: handle line breaks
        line = self.buffer._lines[self._line]
           
        left  = line._text[:self._col]
        right = line._text[self._col:]
    
        line._text = left + text + right
        line._did_change_text(self._col, len(text))

        self._mark_all_invalid()
        self._mark_valid()

        self.move_by(right=len(text))
        

    def remove_until(self, other):
        '''
        Remove the text between this cursor and the other. The character under
        the other cursor will not be removed. The other cursor's position will
        be updated.

        :type other: codeedit.buffer.Cursor
        '''

        other_line, other_col = other.line, other.col
        
        if other_line < self.line:
            raise ValueError('Other cursor must be after this cursor.')

        if self.line != other_line:
            del self.buffer._lines[self.line + 1:other_line]
            other_line = self.line + 1
            
            first_line = self.buffer._lines[self.line]
            first_line_last_index = len(first_line._text) - 1
            first_line._text = first_line._text[:self.col]
            first_line._did_change_text(first_line_last_index, self.col - first_line_last_index - 1)

            last_line_text = self.buffer._lines[other_line]._text[other_col:]
            del self.buffer._lines[other_line]
            self.insert(last_line_text)
        else:
            line = self.buffer._lines[self.line]
            left  = line._text[:self.col]
            right = line._text[other_col+1:]
            line._text = left + right
            line._did_change_text(other_col, self.col - other_col - 1)
       
        self._mark_all_invalid()
        self._mark_valid()

        other.move_to(self.line, self.col)

    def clone(self):
        result = Cursor(self.buffer)
        result.move_to(self.line, self.col)
        return result
