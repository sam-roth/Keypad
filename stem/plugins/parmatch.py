

from stem.api import autoextend, BufferController
from stem.buffers import Cursor, Span
import sys
def enum_reversibly(iterable, start, back=False):
    if back:
        return reversed(list(enumerate(iterable[:start+1])))
    else:
        return enumerate(iterable[start:], start)

def find_matching_brace(buff, start_pos, lbrace, rbrace, back=False):
    '''
    >>> from stem.buffers import Buffer
    >>> buff=Buffer()
    >>> buff.insert((0,0), '((\\n))')
    >>> find_matching_brace(buff, (0,0), '(', ')')
    (1, 1)
    >>> find_matching_brace(buff, (0,1), '(', ')')
    (1, 0)
    >>> find_matching_brace(buff, (1,0), '(', ')', back=True)
    (0, 1)
    >>> find_matching_brace(buff, (1,1), '(', ')', back=True)
    (0, 0)
    '''
    sy, sx = start_pos
    open_count = 0

    if back:
        lbrace, rbrace = rbrace, lbrace

    count = 0

    curs = Cursor(buff).move(start_pos)
    direction = -1 if back else 1

    for _ in curs.walk(direction):
        ch = curs.rchar

        if ch == lbrace:
            open_count += 1
        elif ch == rbrace:
            open_count -= 1

        if open_count <= 0:
            break

    if open_count <= 0:
        return curs.pos
    else:
        return None

Delimiters = '() [] {}'.split()


def find_matching_delimiter(buff, pos, delims=Delimiters):
    '''
    >>> from stem.buffers import Buffer
    >>> buff=Buffer()
    >>> buff.insert((0,0), '(([))]')
    >>> find_matching_delimiter(buff, (0,0))
    (0, 4)
    >>> find_matching_delimiter(buff, (0,1))
    (0, 3)
    >>> find_matching_delimiter(buff, (0,4))
    (0, 1)
    >>> find_matching_delimiter(buff, (0,5))
    (0, 0)
    >>> find_matching_delimiter(buff, (0,6))
    (0, 2)
    '''
    curs = Cursor(buff).move(pos)
    try:
        rchar = curs.rchar
    except IndexError:
        pass
    else:
        for lbrace, rbrace in delims:
            if rchar == lbrace:
                return find_matching_brace(buff, pos, lbrace, rbrace)
    

    try:
        curs.advance(-1)
    except IndexError:
        pass
    else:
        lchar = curs.rchar
        for lbrace, rbrace in delims:
            if lchar == rbrace:
                return find_matching_brace(buff, curs.pos, lbrace, rbrace, back=True)


@autoextend(BufferController, lambda tags: tags.get('parmatch'))
class ParenMatcher(object):
    def __init__(self, bufctl):
        '''
        :type bufctl: stem.api.BufferController
        '''
        
        self.bufctl = bufctl
        bufctl.canonical_cursor_move.connect(self.__on_cursor_move)
        self.spans = self.bufctl.view.overlay_spans['ParenMatcher'] = []

    def __on_cursor_move(self):
        curs = self.bufctl.canonical_cursor
        self.spans.clear()
        buff = self.bufctl.buffer
        
        bracepos = find_matching_delimiter(buff, curs.pos)

        if bracepos is not None:
            span = Span.from_pos(buff, bracepos, length=1)
            self.spans.extend([
                (span,
                 'sel_bgcolor',
                 'auto'),
                (span,
                 'sel_color',
                 'auto')
            ])
    
    



