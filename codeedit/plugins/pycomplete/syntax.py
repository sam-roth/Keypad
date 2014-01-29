
import re
import keyword
import logging

from codeedit.api import BufferController, autoconnect

def highlight_kw(kwds):
    return highlight_regex('|'.join(r'\b' + k + r'\b' for k in kwds))


def highlight_regex(regex, flags=0):
    rgx = re.compile(regex, flags)

    def result(astr, **attrs):
        for match in rgx.finditer(astr.text):
            for attr, val in attrs.items():
                astr.set_attribute(match.start(), match.end(), attr, val)

    return result


_python_kwlist = frozenset(keyword.kwlist) - frozenset('from import None False True'.split())
_python_kw_highlighter = highlight_kw(_python_kwlist)
_d_string_highlighter = highlight_regex(r'"([^"]|\\")*"')
_q_string_highlighter = highlight_regex(r"'([^']|\\')*'")
_python_func_highlighter = highlight_regex(
    r"""
      (?<= def  ) \s+\w+        
    | (?<= class) \s+\w+
    | (?<= @    ) (\w|\.)+      # decorators
    """,
    re.VERBOSE
)
_python_morefunc_highlighter = highlight_kw('None False True'.split())
_python_import_highlighter = highlight_regex(r'\bfrom\b|\bimport\b|@')


def python_syntax(buff):
    last_line_state = None
    rehighlight_count = 0
    for line in buff.lines:
        if not (line.caches.get('polished', False) and line.caches.get('last_line_state') 
                == last_line_state):
            rehighlight_count += 1
            line.set_attribute('lexcat', None)

            _python_kw_highlighter       (line, lexcat='keyword')
            _python_func_highlighter     (line, lexcat='function')
            _python_morefunc_highlighter (line, lexcat='function')
            _python_import_highlighter   (line, lexcat='preprocessor')
            _d_string_highlighter        (line, lexcat='literal')
            _q_string_highlighter        (line, lexcat='literal')
            
            line_state = last_line_state

            start = 0
            for match in re.finditer(r"'''", line.text):
                if line_state == 'single_string':
                    line_state = None
                    line.set_attribute(start, match.end(), 'lexcat', 'literal')
                else:
                    line_state = 'single_string'
                    start = match.start()

            if line_state == 'single_string':
                line.set_attribute(start, None, 'lexcat', 'literal')

            for match in re.finditer(r'#.*', line.text):
                attrs = dict(line.attributes(match.start()))
                if attrs.get('lexcat') is None:
                    line.set_attribute(match.start(), match.end(), 'lexcat', 'comment')


            line.caches['last_line_state'] = last_line_state
            line.caches['polished'] = True
            last_line_state = line_state
            line.caches['line_state'] = line_state
        else:
            last_line_state = line.caches.get('line_state')
    
#@autoconnect(BufferController.buffer_needs_highlight,
#             lambda tags: tags.get('syntax') == 'python')
def python_syntax_highlighting(controller):
    python_syntax(controller.buffer)



from codeedit.plugins.semantics.syntax import SyntaxHighlighter, lazy

@lazy
def pylexer():
    from codeedit.plugins.semantics.syntaxlib import keyword, regex, region

    Keyword     = keyword(_python_kwlist, dict(lexcat='keyword'))
    Import      = keyword('from import'.split(), dict(lexcat='preprocessor'))
    Const       = keyword('None True False'.split(), dict(lexcat='function'))

    
    ESCAPE      = dict(lexcat='escape')
    STRING      = dict(lexcat='literal')
    
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
            exit=regex(r"(?<!\\)" + quote),
            contains=[regex(r"\\" + quote, ESCAPE)],
            attrs=STRING
        )

    RSQString = make_raw_string("'")
    RDQString = make_raw_string('"')
    
    NUMBER = dict(lexcat='literal')

    FloatLiteral = regex(r'\b\d*\.\d+', NUMBER)
    IntLiteral   = regex(r'\b\d+L?', NUMBER)
    

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
        FloatLiteral
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
    highlighter = SyntaxHighlighter('codeedit.plugins.pycomplete.syntax', pylexer(), dict(lexcat=None))
    highlighter.highlight_buffer(controller.buffer)


def main():
    from codeedit.plugins.semantics.syntaxlib import Tokenizer
    from codeedit.core import AttributedString
    from codeedit.buffers import Buffer

    buf = Buffer()
    buf.insert((0,0), "'\\b")

    highlighter = SyntaxHighlighter('h', pylexer(), dict(lexcat=None))

    highlighter.highlight_buffer(buf)

    print(buf.lines[0])

if __name__ == '__main__':
    main()

