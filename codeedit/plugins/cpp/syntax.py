import re
import keyword
import logging

from codeedit.api import BufferController, autoconnect
from codeedit.plugins.semantics.syntax import SyntaxHighlighter, lazy

@lazy
def cpplexer():
    from codeedit.plugins.semantics.syntaxlib import keyword, regex, region
    

    keywords = '''
        alignas alignof and and_eq asm auto bitand bitor bool break case catch char
        char16_t char32_t class compl const constexpr const_cast continue decltype
        default delete do double dynamic_cast else enum explicit export extern false
        float for friend goto if inline int long mutable namespace new noexcept not
        not_eq nullptr operator or or_eq private protected public register
        reinterpret_cast return short signed sizeof static static_assert static_cast
        struct switch template this thread_local throw true try typedef typeid typename
        union unsigned using virtual void volatile wchar_t while xor xor_eq
    '''.split()

    
    KEYWORD     = dict(lexcat='keyword')
    ESCAPE      = dict(lexcat='escape')
    STRING      = dict(lexcat='literal')
    NUMBER      = dict(lexcat='literal')
    COMMENT     = dict(lexcat='comment')
    DOC         = dict(lexcat='docstring')
    PREPROC     = dict(lexcat='preprocessor')

    HEX         = r'[a-fA-F0-9]'
    

    Preproc = regex(r'^\s*#\s*\w+', PREPROC)


    Keyword = keyword(keywords, KEYWORD) # Semantically satiated yet [ZONG2006CHI]?

    
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


    CPPComment  = regex(r'//(?!/).*', COMMENT)
    CComment    = region(
                    guard=regex(r'/\*(?!\*)'),
                    exit=regex(r'\*/'),
                    contains=[],
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
                      Preproc]
        )


    return CPP


@autoconnect(BufferController.buffer_needs_highlight,
             lambda tags: tags.get('syntax') == 'c++')
def cpp_syntax_highlghting(bufctl):
    highlighter = SyntaxHighlighter(
        'codeedit.plugins.cpp.syntax',
        cpplexer(),
        dict(lexcat=None)
    )

    highlighter.highlight_buffer(bufctl.buffer)
# Bibliography
# ============
# [ZONG2006CHI]  D. Zongker, “Chicken chicken chicken: Chicken chicken,” Annals
#                of Improbable Research, vol. 12, no. 5, pp. 16–21, September 2006.
#                [Online]. Available: http://www.improbable.com/airchives/paperair/
#                                     volume12/v12i5/chicken-12-5.pdf
