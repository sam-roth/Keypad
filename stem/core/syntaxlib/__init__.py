'''
Lexer support library.
'''

from .syntaxlib import (Any, Lexer, AnyLexer, RegexLexer, 
                        RegionLexer, NothingLexer, TokenizerEvent,
                        UnionTokenizer, AbstractTokenizer,
                        regex, region, keyword)

from .syntax import SyntaxHighlighter, lazy

