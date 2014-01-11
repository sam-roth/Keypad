
from . import util, undo

from .attributed_string import AttributedString

#class Line(object):
#    def __init__(self, text=''):
#        #self._blocks = []
#        self._text = text
#
#
#    @property
#    def text(self):
#        return self._text
#    
#    def __len__(self):
#        return len(self._text)

class Buffer(object):
    def __init__(self):
        self._lines = []
        self._cursor_serial = 0
        self.persistent_cursors = []
        self._canonical_cursor = None
        self._anchor_cursor = None
        self._history = undo.History()

    @property
    def history(self):
        return self._history

    @property
    def canonical_cursor(self):
        return self._canonical_cursor

    @canonical_cursor.setter
    def canonical_cursor(self, value):
        if value not in self.persistent_cursors and value is not None:
            self.persistent_cursors.append(value)
        self._canonical_cursor = value


    @property
    def anchor_cursor(self):
        return self._anchor_cursor

    @anchor_cursor.setter
    def anchor_cursor(self, value):
        if value not in self.persistent_cursors and value is not None:
            self.persistent_cursors.append(value)
        self._anchor_cursor = value

    @property
    def lines(self):
        return util.ImmutableListView(self._lines)

    @classmethod
    def from_text(cls, text):
        self = cls()
        self._lines = list(map(AttributedString, text.splitlines()))
        return self

    def to_plain_text(self):
        return '\n'.join(line.text for line in self.lines)
        
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
        for cursor in self.persistent_cursors:
            if cursor._line == line and cursor._col >= index and cursor is not curs:
                cursor._col += delta
            cursor._mark_valid()


    def cursor(self, line=0, col=0):
        result = UndoCursor(self)
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

    @property
    def pos(self):
        return self.line, self.col

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
                raise IndexError('col %d/%d' % (col, len(self.buffer._lines[line])))
            else:
                self.col_affinity = col
                col = len(self.buffer._lines[line])
        
        self._line = line
        self._col = col

        self._mark_valid()

    def move_by(self, down=0, right=0, exact=True, *, up=0, left=0):
        down -= up
        left -= right
        self._move_to_pos(self.line + down if down != 0 else None, 
                          self.col + right if right != 0 else None, 
                          exact)

    def go(self, down=0, right=0, *, up=0, left=0):
        self.move_by(down-up, right-left, exact=False)

    def go_to(self, line=None, col=None):
        self._move_to_pos(line, col, exact=False)

    def go_to_end(self):
        self.move_to(col=-1, exact=False)

    def go_to_home(self):
        self.move_to(col=0, exact=False)

    @property
    def line_length(self):
        return len(self.buffer.lines[self.line])

    @property
    def at_end_of_buffer(self):
        self.line == len(self.buffer.lines) - 1 and self.col == self.line_length

    @property
    def at_start_of_buffer(self):
        return self.line == 0 and self.col == 0

    @property
    def can_go_down(self):
        return self.line != len(self.buffer.lines) - 1

    @property
    def can_go_up(self):
        return self.line != 0


    def _find_offset(self, offset):
        line_start_offset = offset + self.col
        line = self.line
        while line_start_offset > len(self.buffer.lines[line]):
            line_start_offset -= len(self.buffer.lines[line]) + 1
            line += 1
        
        while line_start_offset < 0 and line > 0:
            line_start_offset += len(self.buffer.lines[line-1]) + 1
            line -= 1

        return (line, line_start_offset)

        
            

            
            


    def advance(self, chars):
        new_pos = self._find_offset(chars)
        logging.debug('Find offset returned %r for %r', new_pos, chars)
        self.move_to(*new_pos)
#        if chars < 0:
#            remaining_dist = -chars
#            while True:
#                col = self.col
#                if remaining_dist <= col:
#                    self.move_by(left=remaining_dist)
#                    break
#                else:
#                    self.move_by(up=1)
#                    self.go_to_end()
#                    self.move_by(left=1) # the cursor is one position past the end of the line
#                    remaining_dist -= col + 1 # extra column is newline
#        else:
#            while True:
#                col_remain = self.line_length - self.col
#                if remaining_dist <= col_remain:
#                    self.move_by(right=remaining_dist)
#                    break
#                else:
#                    self.move_by(down=1)
#                    self.go_to_home()


            

                    




#
#
#    def advance(self, chars):
#        if chars < 0:
#            while True:
#                if -chars > self.col:
#                    if not self.can_go_up:
#                        self.go_to_home()
#                        break
#                    self.go(up=1)
#                    self.go_to_end()
#                    chars += self.col if self.line_length > 0 else 1
#                else:
#                    self.go(left=-chars)
#                    break
#        else:
#            while True:
#                if chars > self.line_length - self.col:
#                    if not self.can_go_down:
#                        self.go_to_end()
#                        break
#                    self.go(down=1)
#                    self.go_to_home()
#                    chars -= self.line_length - self.col
#                else:
#                    self.go(right=chars)
#                    break
#

    def backspace(self):
        orig = self.clone()
        orig.advance(-1)
        self.remove_until(orig)
        

    def _raw_insert(self, text):
        if not text:
            return
        lines = text.split('\n')
        if len(lines) == 0:
            return
        elif len(lines) == 1:
            self._insert_in_line(lines[0])
        else:
            first, *rest = lines
            rest_of_first = self.buffer._lines[self.line].text[self.col:]
            
            end_of_first = self.clone()
            end_of_first.move_to(col=len(self.buffer._lines[self.line].text))
            self._raw_remove_until(end_of_first)

            self._insert_in_line(first)

            
            for line in rest:
                self.buffer._lines.insert(self.line + 1, AttributedString(line))
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
        if not text:
            return

        line = self.buffer._lines[self.line]

        line.insert(self.col, text)
           
        self._mark_all_invalid()
        self.buffer._did_change_text(self, self.line, self.col, len(text))

        self._mark_valid()

        self.move_by(right=len(text))
        

    def _raw_remove_until(self, other):
        '''
        Remove the text between this cursor and the other. The character under
        the other cursor will not be removed. The other cursor's position will
        be updated.

        :type other: codeedit.buffer.Cursor
        '''

        
        orig_self = None
        orig_other = None


        if other.line < self.line or (other.line == self.line and other.col < self.col):
            orig_self, orig_other = self, other
            self, other = other.clone(), self.clone()


        other_line, other_col = other.line, other.col

        if self.line != other_line:
            del self.buffer._lines[self.line + 1:other_line]
            self.buffer._did_change_lines(self, self.line + 1, -(other_line - self.line - 1))

            other_line = self.line + 1
            
            first_line = self.buffer._lines[self.line]
            first_line_last_index = len(first_line.text) - 1
            first_line.remove(self.col, None)
            self.buffer._did_change_text(self, self.line, self.col, self.col - first_line_last_index - 1)

            last_line_text = self.buffer._lines[other_line].text[other_col:]

            del self.buffer._lines[other_line]
            self.buffer._did_change_lines(self, other_line, -1)

            orig_col = self.col
            self._raw_insert(last_line_text)
            self.move_to(col=orig_col)
        else:
            line = self.buffer._lines[self.line]
            line.remove(self.col, other.col)
            self.buffer._did_change_text(self, self.line, self.col, self.col - other_col - 1)
       
        self._mark_all_invalid()
        self._mark_valid()

        if orig_self is not None:
            orig_self.move_to(self.line, self.col)
            orig_other.move_to(self.line, self.col)

        other.move_to(self.line, self.col)

    def clone(self):
        result = Cursor(self.buffer)
        result.move_to(self.line, self.col)
        return result

    def selection_until(self, other):
        return Selection(self, other)

    def select(self, left=0, down=0, right=0, up=0, forwards=0, backwards=0):
        copy = self.clone()
        copy.advance(forwards-backwards)
        copy.go(left=left, right=right, down=down, up=up)
        return self.selection_until(copy)

class Selection(object):
    '''
    Represents a selected range of text from `start_cursor` to
    `end_cursor`, including `start_cursor`, but excluding `end_cursor`.
    '''
    def __init__(self, start_cursor, end_cursor):
        '''
        :type start_cursor: codeedit.buffer.Cursor
        :type end_cursor:   codeedit.buffer.Cursor
        '''

        if start_cursor.pos > end_cursor.pos:
            end_cursor, start_cursor = start_cursor, end_cursor

        self.start_cursor = start_cursor
        self.end_cursor = end_cursor

    @property
    def buffer(self):
        '''
        Get the buffer associated with this selection.
        :rtype: codeedit.buffer.Buffer
        '''

        return self.start_cursor.buffer

    def remove(self):
        self.start_cursor.remove_until(self.end_cursor)


    def iterranges(self):
        '''
        :rtype: (int, codeedit.attributed_string.AttributedString, int, int)
        '''
        if self.start_cursor.line == self.end_cursor.line:
            yield self.start_cursor.line, self.buffer.lines[self.start_cursor.line], self.start_cursor.col, self.end_cursor.col
        else:
            line = self.buffer.lines[self.start_cursor.line]
            yield self.start_cursor.line, line, self.start_cursor.col, len(line)

            for linenum, line in enumerate(self.buffer.lines[self.start_cursor.line+1:self.end_cursor.line], self.start_cursor.line):
                yield linenum, line, 0, len(line)

            yield self.end_cursor.line, self.buffer.lines[self.end_cursor.line], 0, self.end_cursor.col


    def set_attribute(self, key, value):
        for linenum, line, start, end in self.iterranges():
            line.set_attribute(start, end, key, value)

    @property
    def text(self):
        return '\n'.join(line.text[start:end] for (_, line, start, end) in self.iterranges())         

    
    def iterchunks(self):
        for linenum, line, start, end in self.iterranges():
            yield from line.iterchunks()
            yield '\n', {k: None for k in line.keys} # reset all attributes



class InsertOperation(undo.Operation):

    def __init__(self, curs, text):
        super().__init__()
        self.curs = curs
        self.text = text
        self.start_pos = curs.pos
        self.end_pos   = None

    def execute(self):
        super().execute()

        if self.end_pos is not None:
            self.curs.move_to(*self.start_pos)
        self.curs._raw_insert(self.text)
        self.end_pos = self.curs.pos
    
    def reverse(self):
        super().reverse()

        self.curs.move_to(*self.start_pos)

        end_curs = self.curs.clone()
        end_curs.move_to(*self.end_pos)

        self.curs._raw_remove_until(end_curs)


import logging
class RemoveOperation(undo.Operation):

    def __init__(self, curs, other_curs):
        super().__init__()

        self.curs = curs

        if curs.pos > other_curs.pos:
            self.direction = -1
        else:
            self.direction = 1

        self.start_pos = curs.pos

        
        self.reverse_start_pos = None
        self.removed_text = self.curs.selection_until(other_curs).text
        self.end_pos = None

    def execute(self):
        super().execute()
        self.curs.move_to(*self.start_pos)
        other = self.curs.clone()
        other.advance(len(self.removed_text) * self.direction)
        self.end_pos = other.pos
        if self.removed_text != self.curs.selection_until(other).text:
            logging.error('Expected text = %r, got text = %r', self.removed_text, self.curs.selection_until(other).text)
        assert self.removed_text == self.curs.selection_until(other).text
        #print('removed {!r}'.format(self.removed_text))
        self.curs._raw_remove_until(other)
        self.reverse_start_pos = self.curs.pos
    
    def reverse(self):
        super().reverse()
        self.curs.move_to(*self.reverse_start_pos)
        self.curs._raw_insert(self.removed_text)

        if self.direction > 0:
            self.curs.move_to(*self.start_pos)


    def coalesce(self, other):
        if isinstance(other, RemoveOperation):
            if ' ' in self.removed_text or ' ' in other.removed_text or self.direction != other.direction:
                return None
            #if other.removed_text.endswith(' ') or other.removed_text.endswith('\n')\
            #        or self.removed_text.startswith(' ') or self.removed_text.startswith('\n')\
            #        or other.direction != self.direction:
            #    return None

            logging.debug('Coalesce %s and %s', util.dump_object(self), util.dump_object(other))
        
            if self.start_pos == other.start_pos: # adjacent forwards delete
                self.removed_text = other.removed_text + self.removed_text
                return self
            elif self.start_pos == other.end_pos: # adjacent backwards delete
                self.removed_text = self.removed_text + other.removed_text
                #self.start_pos = other.start_pos
                return self

            else: # non-adjacent
                return None
    
        else:
            return None





#    def coalesce(self, other):
#        if not isinstance(other, RemoveOperation): return None
#        
#        if other.removed_text.endswith(' ') or other.removed_text.endswith('\n'):
#            return None
#        else:
#            start_pos = min(self.start_pos, other.start_pos)
#            end_pos   = max(self.end_pos, other.end_pos)
#            self.reverse_start_pos = min(self.reverse_start_pos, other.reverse_start_pos)
#
#            if self.start_pos > other.start_pos:
#                self.removed_text = other.removed_text + self.removed_text
#            else:
#                self.removed_text = self.removed_text + other.removed_text
#
#            self.start_pos = start_pos
#            self.end_pos = end_pos
#
#            
#                
#            return self
#
        



class UndoCursor(Cursor):

    def __init__(self, buf):
        super().__init__(buf)

    def insert(self, text):
        self._forward_calls = True
        if text:
            #print('insert')
            self.buffer.history.execute(InsertOperation(self, text))

    def remove_until(self, other):
        if other.pos != self.pos:
            #print('remove')
            self.buffer.history.execute(RemoveOperation(self, other))

    def clone(self):
        result = UndoCursor(self.buffer)
        result.move_to(*self.pos)
        return result



