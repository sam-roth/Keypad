
import re
import keyword
import logging
import builtins

from stem.api import BufferController, autoconnect
from stem.plugins.semantics.syntax import SyntaxHighlighter, lazy


_python_kwlist = frozenset(keyword.kwlist) - frozenset('from import None False True'.split())
_python_builtins = frozenset(x for x in dir(builtins) if not isinstance(getattr(builtins, x), type))
_python_types = frozenset(x for x in dir(builtins) if isinstance(getattr(builtins, x), type))

@lazy
def pylexer():
    from stem.plugins.semantics.syntaxlib import keyword, regex, region

    Keyword     = keyword(_python_kwlist, dict(lexcat='keyword'))
    Import      = keyword('from import'.split(), dict(lexcat='preprocessor'))
    Const       = keyword(_python_builtins, dict(lexcat='function'))
    Type        = keyword(_python_types, dict(lexcat='type'))

    
    ESCAPE      = dict(lexcat='escape')
    STRING      = dict(lexcat='literal')
    COMMENT     = dict(lexcat='comment')
    FUNCTION    = dict(lexcat='function')

    Comment     = regex(r'#.*', COMMENT)

    HEX         = r'[a-fA-F0-9]'
    
    
    Esc1        = regex(r'''\\[abfnrtv'"\\]''', ESCAPE)
    Esc2        = regex(r'''\\\[0-7]{1,3}''', ESCAPE)
    Esc3        = regex(r'''\\x[a-fA-F0-9]{2}''', ESCAPE)

    Esc4        = regex(r'\\u' + HEX + r'{4}|\\U' + HEX + '{8}', ESCAPE)
    Esc5        = regex(r'\\N\{[a-zA-Z]+(?:\s[a-zA-Z]+)*}', ESCAPE)
    Esc6        = regex(r'\\$', ESCAPE)


    DQDoctest   = region(
                    guard=regex(r'^\s*>>>\s'),
                    exit=regex(r'$|(?=""")'),
                    contains=(),
                    attrs=ESCAPE
                )

    SQDoctest   = region(
                    guard=regex(r'^\s*>>>\s'),
                    exit=regex(r"$|(?=''')"),
                    contains=(),
                    attrs=ESCAPE
                )

    Escs        = [Esc1, Esc2, Esc3, Esc4, Esc5, Esc6]
    
    DQString    = region(
                    guard=regex(r'"(?!"")'),
                    exit=regex(r'"'),
                    contains=Escs,
                    attrs=STRING
                )
    SQString    = region(
                    guard=regex(r"'(?!'')"),
                    exit=regex(r"'"),
                    contains=Escs,
                    attrs=STRING
                ) 

    
    TDQString   = region(
                    guard=regex(r'"""'),
                    exit=regex(r'"""'),
                    contains=Escs + [DQDoctest],
                    attrs=STRING
                )
    TSQString   = region(
                    guard=regex(r"'''"),
                    exit=regex(r"'''"),
                    contains=Escs + [SQDoctest],
                    attrs=STRING
                ) 


    def make_raw_string(quote):
        
        
        return region(
            guard=regex(r"r" + quote),
            exit=regex(r"\\\\" + quote + "|" + r"(?<!\\)" + quote),
            contains=[regex(r"(?<!\\)\\" + quote, ESCAPE)],
            attrs=STRING
        )

    RSQString = make_raw_string("'")
    RDQString = make_raw_string('"')
    
    RTSQString = make_raw_string("'''")
    RTDQString = make_raw_string('"""')
    
    NUMBER = dict(lexcat='literal')

    FloatLiteral = regex(r'\b\d*\.\d+', NUMBER)
    IntLiteral   = regex(r'\b\d+L?', NUMBER)
    HexLiteral   = regex(r'\b0x' + HEX + r'+L?', NUMBER)
    OctLiteral   = regex(r'\b0o[0-7]+L?', NUMBER)
    BinLiteral   = regex(r'\b0b[01]+L?', NUMBER)

    FuncDef = regex(r'(?:(?<=def)|(?<=class)|(?<=@))\s+\w+', FUNCTION)
    Deco    = regex(r'(?<=@)\s*[\w.]+', FUNCTION)
    CommAt = regex(re.escape('@'), ESCAPE)
    

    PythonLexers = [
        Keyword,
        Const,
        Import,
        DQString, 
        SQString,
        TDQString,
        TSQString,
        RSQString,
        RDQString,
        IntLiteral,
        HexLiteral,
        OctLiteral,
        BinLiteral,
        FloatLiteral,
        Comment,
        FuncDef,
        CommAt,
        RTSQString,
        RTDQString,
        Deco,
        Type
    ]

    DQDoctest.contains = tuple(PythonLexers)
    SQDoctest.contains = tuple(PythonLexers)
    

        
    Python      = region(
                    guard=None,
                    exit=None,
                    contains=PythonLexers
                )
    
    return Python



@autoconnect(BufferController.buffer_needs_highlight,
             lambda tags: tags.get('syntax') == 'python')
def python_syntax_highlighting(controller):
    highlighter = SyntaxHighlighter('stem.plugins.pycomplete.syntax', pylexer(), dict(lexcat=None))
    highlighter.highlight_buffer(controller.buffer)


def main():
    from stem.plugins.semantics.syntaxlib import Tokenizer
    from stem.core import AttributedString
    from stem.buffers import Buffer

    buf = Buffer()
    buf.insert((0,0), "'\\b")

    highlighter = SyntaxHighlighter('h', pylexer(), dict(lexcat=None))

    highlighter.highlight_buffer(buf)

    print(buf.lines[0])

if __name__ == '__main__':
    main()

