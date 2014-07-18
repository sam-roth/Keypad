import logging

from .syntaxlib import AbstractTokenizer, Tokenizer, TokenizerEvent
from keypad.util import time_limited
class SyntaxHighlighter(object):

    def __init__(self, name, lexer, base_attrs):
        if isinstance(lexer, AbstractTokenizer):
            self._tokenizer = lexer
        else:
            self._tokenizer = Tokenizer(lexer)
        self._name = name

        self._end_state_key     = name + '.' + 'end_state'
        self._start_state_key   = name + '.' + 'start_state'
        self._token_stack_key   = name + '.' + 'token_stack'

        self._base_attrs = base_attrs


    def highlight_buffer(self, buff):
        self._tokenizer.reset()
        state = self._tokenizer.save()
        token_stack = []
        # TODO: start on modified line
        for i, line in time_limited(enumerate(buff.lines), ms=100):
            line_start_state = line.caches.get(self._start_state_key) 

            if line_start_state != state:
                # reset line attributes
                line.set_attributes(0, None, **self._base_attrs)
                self._tokenizer.restore(state)


                attr_ranges = []

                # Handle tokens that end on this line
                for ty, lexer, pos in self._tokenizer.tokenize(line, 0, len(line)):
                    if ty == TokenizerEvent.token_start:
                        token_stack.append((lexer, pos))
                    else:
                        start_lexer = None
                        # Find the token to pop by going through the token
                        # stack until a match is found.
                        for i, (start_lexer, start) in enumerate(reversed(token_stack)):
                            if start_lexer is lexer:
                                attr_ranges.append((start, pos, lexer.attrs))
                                del token_stack[-(i+1)]
                                break
                        else:
                            logging.warning('Expected %r, which was not in the token stack.', lexer)

                # Handle tokens that go past the end of the line
                next_line_token_stack = []

                for lexer, start in token_stack:
                    line.set_attributes(start, None, **lexer.attrs)
                    next_line_token_stack.append((lexer, 0))

                for start, end, attrs in reversed(attr_ranges):
                    line.set_attributes(start, end, **attrs)

                token_stack = next_line_token_stack

                line.caches[self._token_stack_key] = tuple(token_stack)
                line.caches[self._start_state_key] = state
                state = self._tokenizer.save()
                line.caches[self._end_state_key] = state
            else:
                state = line.caches[self._end_state_key]
                token_stack = list(line.caches[self._token_stack_key])



from keypad.api import autoconnect, BufferController
import functools
def lazy(f):
    '''
    Return a function ``g`` that runs `f` the first time it is called, saving
    and returning its output. Upon subsequent calls, ``g`` returns the saved
    output without calling `f`.

    >>> @lazy
    ... def foo():
    ...     print('foo')
    ...     return 5
    >>> output = foo()
    foo
    >>> print(output)
    5
    >>> output = foo()
    >>> print(output)
    5
    '''
    cache = []
    @functools.wraps(f)
    def result():
        if not cache:
            cache.append(f())
        return cache[0]
    return result

@lazy
def kaleidoscope_lexer():
    from .syntaxlib import keyword, regex, region

    Comment = regex(r'#.*', dict(lexcat='comment'))

    Keyword = keyword('def if then else extern for in binary unary'.split(),
                      dict(lexcat='keyword'))

    Number = regex('[0-9.]+', dict(lexcat='literal'))

    FuncName = regex(r'(?:(?<=\bdef\b)|(?<=\bunary\b)|(?<=\bbinary\b))\s*(?P<body>[^\s()]+)', dict(lexcat='function'))
    Kaleidoscope = region(
        guard=None,     # Always enter this lexer if it is reached.
        exit=None,      # Leave this lexer only at the end of file.
        contains=[Comment, Keyword, Number, FuncName]
    )

    return Kaleidoscope


#@autoconnect(BufferController.buffer_needs_highlight,
#             lambda tags: tags.get('syntax') == 'kal')
def kaleidoscope_syntax(bufctl):
    hl = SyntaxHighlighter('keypad.plugins.semantics.syntax.kal', kaleidoscope_lexer(), dict(lexcat=None))
    hl.highlight_buffer(bufctl.buffer)

