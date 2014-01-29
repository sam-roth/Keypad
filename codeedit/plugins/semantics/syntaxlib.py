
'''
Simple lexer combinator library for syntax highlighting.


Let's say we want to highlight the LLVM project's toy example language, "Kaleidoscope" 
(http://llvm.org/docs/tutorial/OCamlLangImpl1.html).

The language has a few keywords, namely:
    def
    if 
    then 
    else
    extern

Thus, our first lexer is Keyword:

>>> Keyword = keyword('def if then else extern'.split())
>>> Keyword.attrs['lexcat'] = 'keyword'

Kaleidoscope has only one literal, a floating point literal.
    Number      ::= [0-9.]+

>>> Number = regex('[0-9.]+')
>>> Number.attrs['lexcat'] = 'literal'


Putting these together, we have:

>>> Kaleidoscope = region(
...     guard=None,     # Always enter this lexer if it is reached.
...     exit=None,      # Leave this lexer only at the end of file.
...     contains=[Keyword, Number]
... )

'''
import abc
from abc import abstractmethod
import re

class Lexer(metaclass=abc.ABCMeta):
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
class AnyLexer(Lexer):
    def guard_match(self, string, start, stop):
        return start, start

Any = AnyLexer()

class NothingLexer(Lexer):
    def guard_match(self, string, start, stop):
        return None

Nothing = NothingLexer()

class RegexLexer(Lexer):

    def __init__(self, regex, attrs=None):
        super().__init__(attrs)
        self.regex = re.compile(regex)

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


class Tokenizer(object):
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

        while lexer_stack and start < stop:
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
                    yield 'token_end', lexer_stack[-1], fg_stop
                    lexer_stack.pop()
                else:
                    lexer_stack.append(fg_lexer)
                    yield 'token_start', lexer_stack[-1], fg_start
                                        
                start = fg_stop

def keyword(kws, attrs=None):
    return RegexLexer('|'.join(map(re.escape, kws)), attrs)

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

    from codeedit.core import AttributedString


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
