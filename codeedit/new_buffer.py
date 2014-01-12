

from . import util
from .signal import Signal
from .attributed_string import AttributedString
from .struct import Struct

class TextModification(Struct):
    pos         = ()
    insert      = default('')
    remove      = default('')


    @property
    def inverse(self):
        assert not self.inserts_and_removes, 'noninvertible'
        return TextModification(pos=self.pos, insert=self.remove, remove=self.insert)

    @property
    def insert_end_pos(self):
        y, x = self.pos

        for ch in self.insert:
            if ch == '\n':
                y += 1
                x = 0
            else:
                x += 1

        return y, x

    def coalesce(self, other):
        insert_end = other.insert_end_pos
        if (bool(self.insert), bool(self.remove)) != (bool(other.insert), bool(other.remove)) or \
                self.inserts_and_removes:
            return None 
        
        if self.insert and other.insert_end_pos == self.pos:
            return TextModification(other.pos, insert=other.insert + self.insert)
        
        else:
            return None

    @property
    def inserts_and_removes(self):
        return self.insert and self.remove


class Buffer(object):

    def __init__(self):
        self._lines = [AttributedString()]


    @Signal
    def text_modified(self, modification):
        '''
        Text was changed.

        :type modification: TextModification
        '''


    @property
    def lines(self):
        return util.ImmutableListView(self._lines)
    
    def insert(self, pos, text):
        y, x = pos
        
        text_lines = text.split('\n')

        if len(text_lines) == 0:
            result = (y, x)
        elif len(text_lines) == 1:
            self._lines[y].insert(x, text_lines[0])
            result = (y, x + len(text_lines[0]))
        else:
            line = self._lines[y]
            removed_text = line.text[x:]
            line.remove(x, None)
            line.append(text_lines[0])

            self._lines = self._lines[:y+1] + \
                [AttributedString(line) for line in text_lines[1:]] + self._lines[y+1:]

            y += len(text_lines)-1
            
            line = self._lines[y]
            line.insert(0, removed_text)

            result = (y, len(removed_text))

        self.text_modified(TextModification(pos=pos, insert=text))



    def remove(self, pos, length):
        sy, sx = pos
        ey, ex = self.calculate_pos(pos, length)
        text = self.span_text(pos, end_pos=(ey, ex))


        if sy == ey:
            self._lines[sy].remove(sx, ex)
        else:
            self._lines[sy].remove(sx, None)
            self._lines[ey].remove(0, ex)
            self._lines[sy].append(self._lines[ey])
            del self._lines[sy+1:ey+1]

        self.text_modified(TextModification(pos=pos, remove=text))

    def execute(self, modification):
        if modification.insert:
            self.insert(modification.pos, modification.insert)
        if modification.remove:
            self.remove(modification.pos, len(modification.remove))


    def reverse(self, modification):
        self.execute(modification.inverse)
            
    def span_text(self, base_pos, offset=None, end_pos=None):
        if (offset is None and end_pos is None) or (offset is not None and end_pos is not None):
            raise TypeError('Must provide either offset or end_pos, but not both.')
        
        if offset is not None:
            end_pos = self.calculate_pos(base_pos, offset)

        by, bx = base_pos
        ey, ex = end_pos

        parts = []
        
        for y, line in enumerate(self._lines[by:ey+1], by):
            start_index = bx if y == by else 0
            end_index   = ex if y == ey else None

            #print(start_index, end_index, line.text[start_index:end_index])
            
            parts.append(line.text[start_index:end_index])
        
        #print(parts)

        return '\n'.join(parts)

    
    def calculate_pos(self, base_pos, offset):
        by, bx = base_pos
        
        line_start_offset = bx + offset
        y = by

        while line_start_offset > len(self._lines[y]):
            line_start_offset -= len(self._lines[y]) + 1
            y += 1

        while line_start_offset < 0:
            y -= 1
            line_start_offset += len(self._lines[y]) + 1

        return y, line_start_offset

    
    @property
    def end_pos(self):
        return len(self.lines) - 1, len(self.lines[-1])

    def dump(self):
        cyan = '\033[36m'
        norm = '\033[0m'

        return cyan + '=' * 70 + '\n' + norm + '\n'.join(
            line.text.replace(' ', cyan + '.' + norm)
            for line in self._lines
        ) + '\n' + cyan + '=' * 70 + norm



def main():
    buf = Buffer()
    
    new_changes = []

    @buf.text_modified.connect
    def _(modification):
        new_changes.append(modification)

    buf.insert((0,0), 'hello\nworld')
    buf.insert((0,2), '!!!\n')

    print(buf.calculate_pos((0,2), 4))
    print(buf.calculate_pos((1,0), -4))
    
    print(buf.dump())

    buf.remove((0,2), 4)
    print(buf.dump())

    new_changes, changes = [], new_changes

    print(changes)

    rev = []

    
    while changes:
        chg = changes.pop()
        buf.reverse(chg)
        print(buf.dump())
        rev.append(chg)

    while rev:
        chg = rev.pop()
        buf.execute(chg)
        print(buf.dump())


    new_changes = []
    
    buf.insert((0, 0), 'a')
    buf.insert((0, 1), 'b')

    print(buf.dump())

    a, b = new_changes
    c = b.coalesce(a)

    print(a, b, c)


    buf.reverse(c)
    print(buf.dump())
    buf.execute(c)
    print(buf.dump())


if __name__ == '__main__':
    main()
