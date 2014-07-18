import re
import keyword
import logging

from keypad.api import BufferController, autoconnect
from keypad.core.syntaxlib import (SyntaxHighlighter, lazy, Lexer)


keywords = '''
    and and_eq asm bitand bitor break case catch
    compl continue
    default delete do  else enum explicit export extern 
    for goto if inline namespace new noexcept not
    not_eq operator or or_eq private protected public
    return switch  throw try  typeid 
    using virtual while xor xor_eq
'''.split()


context_keywords = 'final override'.split()

builtin_names = 'true false NULL nullptr this'.split()

# not all of these are types, but I was tired of seeing so much green.
cpp_types = '''
union 
template thread_local static  static_assert static_cast alignas alignof const_cast reinterpret_cast
sizeof typename double dynamic_cast typedef class struct typename friend
int long bool auto char16_t char32_t char const register mutable void volatile wchar_t
float short signed unsigned decltype size_t ssize_t constexpr
'''.split()
cpp_types += ['{}int{}_t'.format(u, 2**n) for u in ('u', '') for n in range(3, 7)]


class RawStringEndLexer(Lexer):
    def __init__(self, text, attrs):
        super().__init__(attrs)
        self.text = text

    def guard_match(self, string, start, stop):
        return None

    def exit_match(self, string, start, stop):
        index = string.text[start:].find(self.text)
        if index >= 0:
            return index + start, index + len(self.text) + start
        else:
            return None

class RawStringStartLexer(Lexer):
    rgx = re.compile(r'R"(.*?)\(')

    def guard_match(self, string, start, stop):
        match = self.rgx.search(
            string.text,
            start, 
            stop
        )

        if match is None:
            return None
        else:
            self.eof_pat = match.group(1)
            try:
                return match.start('body'), match.end('body')
            except LookupError:
                return match.start(), match.end()

    def exit_match(self, string, start, stop):
        return None


    def enter(self):
        return RawStringEndLexer(')' + self.eof_pat + '"', self.attrs)
        

@lazy
def cpplexer():
    from keypad.core.syntaxlib import keyword, regex, region
    import re




    CONTEXT_KW  = dict(lexcat='keyword.context')    
    NAME        = dict(lexcat='identifier')
    KEYWORD     = dict(lexcat='keyword')
    ESCAPE      = dict(lexcat='literal.string.escape')
    STRING      = dict(lexcat='literal.string')
    NUMBER      = dict(lexcat='literal.numeric')
    COMMENT     = dict(lexcat='comment')
    DOC         = dict(lexcat='comment.documentation')
    PREPROC     = dict(lexcat='preprocessor')
    TODO        = dict(lexcat='todo')
    TYPE        = dict(lexcat='identifier.type')


    HEX         = r'[a-fA-F0-9]'

    IncludeString = regex(r'<[^>]*>', STRING)

    PreprocIf = region(guard=regex(r'^\s*#if(def)?'),
                       exit=regex(r'^\s*#endif'),
                       contains=[])

    PreprocComment = region(guard=regex(r'^\s*#if\s+0$'),
                            exit=regex(r'^\s*#endif'),
                            contains=[PreprocIf],
                            attrs=dict(lexcat='comment.preprocessor'))
    
    Preproc = region(guard=regex(r'^\s*#(?!if\s+0)\s*\w+'),
                     exit=regex(r'(?<!\\)$'),
                     contains=[IncludeString],
                     attrs=PREPROC)



    Keyword = keyword(keywords, KEYWORD) 
    CtxKeywords = keyword(context_keywords, CONTEXT_KW)
    BuiltinNames = keyword(builtin_names, NAME)
    Type    = keyword(cpp_types, TYPE)


    QualName = regex(r'(::|\.|->)\s*(?P<body>\b\w+\b)', NAME)



    Esc1        = regex(r'''\\[abfnrtv'"\\]''', ESCAPE)
    Esc2        = regex(r'''\\\[0-7]{1,3}''', ESCAPE)
    Esc3        = regex(r'''\\x[a-fA-F0-9]{2}''', ESCAPE)

    Esc4        = regex(r'\\u' + HEX + r'{4}|\\U' + HEX + '{8}', ESCAPE)
    Esc5        = regex(r'\\N\{[a-zA-Z]+(?:\s[a-zA-Z]+)*}', ESCAPE)

    Escs        = [Esc1, Esc2, Esc3, Esc4, Esc5]

    DQString    = region(
                    guard=regex(r'"(?!"")'),
                    exit=regex(r'"'),
                    contains=Escs,
                    attrs=STRING
                )
    RawString   = RawStringStartLexer()
    RawString.attrs = STRING
    CharLit     = region(guard=regex(r"'(?!'')"),
                         exit=regex(r"'"),
                         contains=Escs,
                         attrs=STRING)

    HexLit      = regex(r'\b0x[0-9a-fA-F]+L?\b', NUMBER)
    DecLit      = regex(r'\b[\d]+L?\b', NUMBER)
    FloatLit    = regex(r'\b(?:\d+\.\d*|\.\d+)f?\b', NUMBER)
    
    Todo        = regex(r'\btodo:|\bfixme:|\bhack:', TODO, flags=re.IGNORECASE)


    CPPComment  = region(
                    guard=regex(r'//'),
                    exit=regex(r'$'),
                    contains=[Todo],
                    attrs=COMMENT
                )
                
    CComment    = region(
                    guard=regex(r'/\*(?!\*)'),
                    exit=regex(r'\*/'),
                    contains=[Todo],
                    attrs=COMMENT
                )

    DoxyCComment= region(
                    guard=regex(r'/\*\*'),
                    exit=regex(r'\*/'),
                    contains=[],
                    attrs=DOC
                )

    DoxyCPPComment = regex('///.*', DOC)

    CPP = region(
            guard=None,
            exit=None,
            contains=[RawString, DQString, Keyword, CPPComment, BuiltinNames, QualName,
                      CComment, DoxyCPPComment, DoxyCComment,
                      PreprocComment,
                      Preproc, Type, HexLit, DecLit, FloatLit, CharLit,
                      CtxKeywords]
        )

    Preproc.contains += CPP.contains
    return CPP

# 
# @autoconnect(BufferController.buffer_needs_highlight,
#              lambda tags: tags.get('syntax') == 'c++')
# def cpp_syntax_highlghting(bufctl):
#     highlighter = SyntaxHighlighter(
#         'keypad.plugins.cpp.syntax',
#         cpplexer(),
#         dict(lexcat=None)
#     )
# 
#     highlighter.highlight_buffer(bufctl.buffer)
# 
# 
