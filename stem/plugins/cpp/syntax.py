import re
import keyword
import logging

from stem.api import BufferController, autoconnect
from stem.plugins.semantics.syntax import SyntaxHighlighter, lazy

@lazy
def cpplexer():
    from stem.plugins.semantics.syntaxlib import keyword, regex, region
    import re

    keywords = '''
        alignas alignof and and_eq asm bitand bitor break case catch
        class compl constexpr const_cast continue
        default delete do double dynamic_cast else enum explicit export extern false
        for friend goto if inline namespace new noexcept not
        not_eq nullptr operator or or_eq private protected public
        reinterpret_cast return sizeof static static_assert static_cast
        struct switch template this thread_local throw true try typedef typeid typename
        union using virtual while xor xor_eq
    '''.split()
    
    
    cpp_types = '''
    int long bool auto char16_t char32_t char const register mutable void volatile wchar_t
    float short signed unsigned decltype
    '''.split()

    
    KEYWORD     = dict(lexcat='keyword')
    ESCAPE      = dict(lexcat='escape')
    STRING      = dict(lexcat='literal')
    NUMBER      = dict(lexcat='literal')
    COMMENT     = dict(lexcat='comment')
    DOC         = dict(lexcat='docstring')
    PREPROC     = dict(lexcat='preprocessor')
    TODO        = dict(lexcat='todo')
    TYPE        = dict(lexcat='type')

    HEX         = r'[a-fA-F0-9]'
    

    Preproc = regex(r'^\s*#\s*\w+', PREPROC)


    Keyword = keyword(keywords, KEYWORD) 
    Type    = keyword(cpp_types, TYPE)

    
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
            contains=[DQString, Keyword, CPPComment, 
                      CComment, DoxyCPPComment, DoxyCComment,
                      Preproc, Type, HexLit, DecLit, FloatLit]
        )


    return CPP


@autoconnect(BufferController.buffer_needs_highlight,
             lambda tags: tags.get('syntax') == 'c++')
def cpp_syntax_highlghting(bufctl):
    highlighter = SyntaxHighlighter(
        'stem.plugins.cpp.syntax',
        cpplexer(),
        dict(lexcat=None)
    )

    highlighter.highlight_buffer(bufctl.buffer)

