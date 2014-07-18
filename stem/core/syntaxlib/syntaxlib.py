
'''
Simple lexer "combinator" library for syntax highlighting.


Let's say we want to highlight the LLVM project's toy example language, Kaleidoscope
(http://llvm.org/docs/tutorial/OCamlLangImpl1.html).

The language has a few keywords, namely

.. productionlist::
    Keyword: "def" | "if" | "then" | "else" | "extern"

Thus, our first lexer is Keyword::

    Keyword = keyword('def if then else extern'.split())
    Keyword.attrs['lexcat'] = 'keyword'

Kaleidoscope has only one literal, a floating point literal:

.. productionlist::
    Number: [0-9.]+

This can be translated using the `regex` lexer::

    Number = regex('[0-9.]+')
    Number.attrs['lexcat'] = 'literal'


Putting these together, we have::

    Kaleidoscope = region(
        guard=None,     # Always enter this lexer if it is reached.
        exit=None,      # Leave this lexer only at the end of file.
        contains=[Keyword, Number]
    )

'''
import abc
from abc import abstractmethod
import re
import logging
import enum
import heapq

class Lexer(metaclass=abc.ABCMeta):
    atomic = False
    def __init__(self, attrs=None):
        self.attrs = attrs or {}
        self.contains = ()

    @abstractmethod
    def guard_match(self, string, start, stop):
        '''
        Find the first match of this lexer.

        Returns None to indicate no match.

        Otherwise, returns a tuple of ``(start, stop)`` where ``start`` is the
        first index in the match and ``stop`` is the index after the last index
        in the match.
        ''' 

    def exit_match(self, string, start, stop):
        return start, start

    def __repr__(self):
        return 'Lexer({!r})'.format(self.attrs)

    def enter(self):
        '''
        If this lexer matches, put the resulting lexer on the stack. By default
        this method returns self; however, you may override it in case the
        correct close token depends on what the open token was.
        '''
        return self


class AnyLexer(Lexer):
    def guard_match(self, string, start, stop):
        return start, start

Any = AnyLexer()

class NothingLexer(Lexer):
    def guard_match(self, string, start, stop):
        return None

Nothing = NothingLexer()

class RegexLexer(Lexer):
    atomic = True
    def __init__(self, regex, attrs=None, flags=0):
        super().__init__(attrs)
        self.regex = re.compile(regex, flags)

    def guard_match(self, string, start, stop):
        match = self.regex.search(
            string.text,
            start, 
            stop
        )


        if match is None:
            return None
        else:
            try:
                return match.start('body'), match.end('body')
            except LookupError:
                return match.start(), match.end()


class RegionLexer(Lexer):
    def __init__(self, guard, exit, contains, attrs=None):
        super().__init__(attrs)
        self.guard = guard or Any
        self.exit = exit or Nothing
        self.contains = tuple(contains or ())

    def guard_match(self, string, start, stop):
        return self.guard.guard_match(string, start, stop)
    
    def exit_match(self, string, start, stop):
        return self.exit.guard_match(string, start, stop)


class TokenizerEvent(enum.Enum):
    token_start = 0
    token_end = 1

class AbstractTokenizer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def reset(self):
        pass

    @abc.abstractmethod
    def save(self):
        pass

    @abc.abstractmethod
    def restore(self, state):
        pass

    @abc.abstractmethod
    def tokenize(self, string, start, stop):
        '''
        Generator yielding a sequence of tuples 
        ``(event: TokenizerEvent, lexer: Lexer, pos: int)``
        each giving an event type, the lexer that caused the event, and
        the position of the event in the string.
        '''
        pass



class Tokenizer(AbstractTokenizer):
    def __init__(self, lexer):
        self.start_lexer = lexer
        self.lexer_stack = [lexer]

    def reset(self):
        self.lexer_stack = [self.start_lexer]

    def save(self):
        return list(self.lexer_stack)

    def restore(self, stack):
        self.lexer_stack = list(stack)

    def tokenize(self, string, start, stop):
        pop = object()

        lexer_stack = self.lexer_stack

        while lexer_stack and start <= stop:
            # find the expected end of the lexer (if it isn't occluded by a contained expression)
            exit_match = lexer_stack[-1].exit_match(string, start, stop)
            if exit_match:
                exit_start, exit_stop = exit_match
                first_guard = exit_start, exit_stop, pop
            else:
                first_guard = None

            # find the first contained expression
            for lexer in lexer_stack[-1].contains:
                lresult = lexer.guard_match(string, start, stop)
                # this contained expression starts before all others seen before
                if lresult and (not first_guard or first_guard[0] >= lresult[0]):
                    lstart, lstop = lresult
                    first_guard = lstart, lstop, lexer

            # no more tokens begin or end this line
            if not first_guard:
                break
            else:
                fg_start, fg_stop, fg_lexer = first_guard

                # check for the sentinel `pop` indicating that the lexer is done
                if fg_lexer is pop:
                    yield TokenizerEvent.token_end, lexer_stack[-1], fg_stop
                    lexer_stack.pop()
                else:
                    lexer_stack.append(fg_lexer.enter())
                    yield TokenizerEvent.token_start, lexer_stack[-1], fg_start

                start = fg_stop

class UnionTokenizer(AbstractTokenizer):
    def __init__(self, *tokenizers):
        self._tokenizers = tuple(tokenizers)

    def reset(self):
        for t in self._tokenizers:
            t.reset()

    def save(self):
        return [t.save() for t in self._tokenizers]

    def restore(self, state):
        assert len(state) == len(self._tokenizers)
        for t, s in zip(self._tokenizers, state):
            t.restore(s)


    def tokenize(self, string, start, stop):
        # FIXME: How should this handle simultaneous state transitions?
        '''
        Generator yielding a sequence of tuples
        ``(event: TokenizerEvent, lexer: Lexer, pos: int)``
        each giving an event type, the lexer that caused the event, and
        the position of the event in the string.
        '''
        q = [] # This will be used as a priority queue.

        # Prime the iterators.
        for tok in self._tokenizers:
            it = iter(tok.tokenize(string, start, stop))
            v = next(it, None)
            if v is not None:
                heapq.heappush(q, (v[-1], v, it))

        # Reorder the events so that they are sequential.
        while q:
            _, value, it = heapq.heappop(q)
            yield value
            value = next(it, None)
            # Add the next value into the heap if the iterator is not
            # exhausted.
            if value is not None:
                heapq.heappush(q, (value[-1], value, it))


def keyword(kws, attrs=None, caseless=False):
    if caseless:
        flags = re.IGNORECASE
    else:
        flags = 0

    return RegexLexer('|'.join(r'\b' + re.escape(x) + r'\b' 
                               for x in kws),
                      attrs,
                      flags=flags)

regex = RegexLexer
region = RegionLexer

def main():
    Keyword = keyword('def if then else extern'.split())
    Keyword.attrs['lexcat'] = 'keyword'

    Number = regex('[0-9.]+')
    Number.attrs['lexcat'] = 'literal'

    ParenGroup = region(
        guard=regex(r'\('),
        contains=[],
        exit=regex(r'\)')
    )


    Kaleidoscope = region(
        guard=None,     # Always enter this lexer if it is reached.
        exit=regex(r'(?=\))'),      # Leave this lexer only at the end of file.
        contains=[Keyword, Number, ParenGroup]
    )

    ParenGroup.contains = (Kaleidoscope,)#.contains
    

    tokenizer = Tokenizer(Kaleidoscope)

    from stem.core import AttributedString


    astring = AttributedString('''
    def fib(x)
      if x < 3 then
        1
      else
        fib(x-1)+fib(x-2)
    ''')
    
    tokens = []
    for ty, lexer, pos in tokenizer.tokenize(astring, 0, len(astring)):
        if ty == 'token_start':
            tokens.append((lexer, pos))
        else:
            tlexer, start = tokens.pop()
            assert tlexer is lexer
            print(tlexer, start, pos, astring.text[start:pos])

if __name__ == '__main__':
    main()



