

from ..                     import util
from ..core                 import Signal, Struct, AttributedString

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
        self._line_view = util.ImmutableListView(self._lines)
        self.code_model = None
        self.history = None

    @Signal
    def text_modified(self, modification):
        '''
        Text was changed.

        :type modification: TextModification
        '''

    @Signal
    def lines_added_or_removed(self, index, count):
        '''
        This signal may help make view implementations more efficient.
        '''

    def append_from_path(self, path, *, codec_errors='strict'):
        '''
        Append this buffer with the contents of the file located at `path`
        decoded using UTF-8.
        '''
        import pathlib

        with pathlib.Path(path).open('r', encoding='utf-8', errors=codec_errors) as f:
            def gen():
                for line in f:
                    yield line.rstrip('\n')

            self.insert_lines(self.end_pos, gen())


    @property
    def lines(self):
        return self._line_view

    def insert(self, pos, text):
        if not text:
            return

        text_lines = text.split('\n')
        self.insert_lines(pos, text_lines, text=text)

    def insert_lines(self, pos, lines, text=None):

        y, x = pos
        text_lines = list(lines) # TODO: use generator directly

        # TODO: this appears to be the best possible with builtin lists. It's also
        # fast enough for my purposes, but it could use improvement. This library
        # looks like it might be useful:
        # https://pypi.python.org/pypi/blist/0.9.4
        # Just for proof that this technique is actually fast enough:
        # In [14]: xs = [0 for _ in range((1<<30))]
        # 
        # In [15]: %timeit xs.insert(int(len(xs)/2), 0)
        # 1 loops, best of 3: 437 ms per loop
        # 
        # In [16]: len(xs)
        # Out[16]: 1073741828
        #
        # This, of course, does not cover the case of multi-line insertions.

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
            self._line_view = util.ImmutableListView(self._lines)

            y += len(text_lines)-1

            line = self._lines[y]
            line.append(removed_text)

            result = (y, len(removed_text))

        if text is None:
            text = '\n'.join(text_lines)
        self.text_modified(TextModification(pos=pos, insert=text))
        if len(text_lines) > 1:
            self.lines_added_or_removed(y, len(text_lines))
    @property
    def text(self):
        return '\n'.join(line.text for line in self._lines)

    def remove(self, pos, length):
        if length == 0:
            return

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

        if sy != ey:
            self.lines_added_or_removed(ey, sy - ey)

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

        try:
            while line_start_offset > len(self._lines[y]):
                line_start_offset -= len(self._lines[y]) + 1
                y += 1
        except IndexError:
            return self.end_pos

        while line_start_offset < 0:
            y -= 1
            line_start_offset += len(self._lines[y]) + 1

        return y, line_start_offset
    
    def calculate_index(self, pos):
        py, px = pos
        
        index_to_line = sum(len(line) + 1 for line in self._lines[:py])
        
        return index_to_line + px
        
    
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


    @classmethod
    def from_text(cls, text):
        result = cls()
        result.insert((0,0), text)
        return result



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
