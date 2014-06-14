
import re
from stem.api import interactive, autoconnect, BufferController
from stem.control.interactive import run as run_interactive
from stem.buffers import Cursor, Span


class RegexSearcher(object):
    '''
    Searches for a regex in a buffer.

    >>> from stem.plugins.search import *
    >>> from stem.buffers import Buffer
    >>> buff = Buffer()
    >>> buff.insert((0,0), 'ab\ncd\nef')
    >>> rs = RegexSearcher(buff)
    >>> rs.search((0,0), 'b\nc')
    ((0, 1), 3)
    >>> rs.search((0,0), '\\w\n\\w')
    ((0, 1), 3)
    >>> rs.search((1,0), '\\w\n\\w')
    ((1, 1), 3)
    >>> rs.search((2,0), '\\w\n\\w', backwards=True)
    ((0, 1), 3)
    '''



    def __init__(self, buff):
        self.buff = buff
        self._cached_text = None
        self.pattern = None

        self.buff.text_modified.connect(self._on_buffer_change)

    def _on_buffer_change(self, chg):
        self._cached_text = None
    
    @property
    def buffer_text(self):
        if self._cached_text is None:
            self._cached_text = self.buff.text

        return self._cached_text

    def _translate_match(self, match):
        if match is not None:
            start_pos = self.buff.calculate_pos((0, 0), match.start())
            return start_pos, match.end() - match.start()
        else:
            return None

    def searchall(self, pattern=None):
        if pattern is None:
            pattern = self.pattern
        else:
            pattern = self.pattern = re.compile(pattern, re.MULTILINE)

        yield from map(self._translate_match, pattern.finditer(self.buffer_text))


    

    def search(self, pos, pattern=None, backwards=False):
        index = self.buff.calculate_index(pos)
        if pattern is not None:
            pattern = re.compile(pattern)
            self.pattern = pattern
        else:
            pattern = self.pattern

        if not backwards:
            match = pattern.search(self.buffer_text, pos=index+1)
        else:
            # TODO: make this more efficient
            matches = list(pattern.finditer(self.buffer_text, pos=0, endpos=index))
            if matches:
                match = matches[-1]
            else:
                match = None

        return self._translate_match(match)


def _get_searcher(bufctl):
    try:
        searcher = bufctl.tags['regex_searcher']
    except KeyError:
        searcher = RegexSearcher(bufctl.buffer)
        bufctl.add_tags(regex_searcher=searcher)

    return searcher


from stem.core import errors

@interactive('find', 'f')
def find(bufctl: BufferController, *pattern):
    '''
    : f[ind] [<pattern>...]

    Find the match of the given pattern following the cursor. (Uses Python
    regex syntax.) Omitting the pattern repeats the previous search.

    Example: 
    
    : find boost((::|/|\.)\w+)*
    '''
    assert isinstance(bufctl, BufferController)
    
    searcher = _get_searcher(bufctl)
    pattern = ' '.join(pattern) if pattern else None
    res = searcher.search(bufctl.canonical_cursor.pos,
                          pattern)

    if res is None:
        raise errors.UserError('No match for {!r}'.format(pattern))

    (y, x), _ = res

    bufctl.selection.move(y, x)
    bufctl.refresh_view()


@interactive('findall', 'fall', 'fa')
def findall(bufctl: BufferController, *pattern):
    '''
    : findall|fa[ll] [<pattern>...]

    Highlight all matches of the given pattern. The highlighting will be
    cleared upon the next edit. Omitting the pattern is the same as using the 
    previously used pattern.

    '''
    searcher = _get_searcher(bufctl)
    pattern = ' '.join(pattern) if pattern else None
    

    def make_span(y, x, length):
        start = Cursor(bufctl.buffer).move(y, x)
        end = Cursor(bufctl.buffer).move(y, x).advance(length)
    
        end.chirality = end.Chirality.Left

        return Span(start, end)


    bufctl.view.set_overlays('search', [
        (make_span(y, x, length),
         'lexcat',
         'search')
        for ((y, x), length) in searcher.searchall(pattern)
    ])
    

@interactive('findclear', 'fc')
def findclear(bufctl: BufferController):
    '''
    : findclear|fc

    Remove the highlighting from a previous use of "findall".
    '''
    try:
        bufctl.view.set_overlays('search', [])
    except KeyError:
        pass


@autoconnect(BufferController.buffer_was_changed,
             lambda tags: tags.get('regex_searcher'))
def buffer_modified(bufctl, chg):
    findclear(bufctl)
