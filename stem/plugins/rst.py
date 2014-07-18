from stem import api
from stem.core import syntaxlib
import re

@syntaxlib.lazy
def lexer():
    from stem.core.syntaxlib import regex, region, keyword

    class RSTLexer:

        KEYWORD     = dict(lexcat='keyword')
        ESCAPE      = dict(lexcat='escape')
        STRING      = dict(lexcat='literal')
        NUMBER      = dict(lexcat='literal')
        COMMENT     = dict(lexcat='comment')
        DOC         = dict(lexcat='docstring')
        PREPROC     = dict(lexcat='preprocessor')
        TODO        = dict(lexcat='todo')
        TYPE        = dict(lexcat='type')
        FUNCTION    = dict(lexcat='function')


        Bullet = regex('''
                       ^\\s*(
                           \\d+\\. |
                           #\\. |
                           \\* |
                           \N{TRIANGULAR BULLET} |
                           \N{BULLET} |
                           \N{HYPHEN BULLET} |
                           -
                       )\\s
                       ''',
                       flags=re.VERBOSE,
                       attrs=KEYWORD)

        SQString = regex(r'`[^`]+`', TYPE)
        DQString = regex(r'``((?!``).)*``', DOC)

        Emph = regex(r''' (?<! \w )
                          (?P<quote> \*\* | \* )
                          (?:(?!(?P=quote)).)*
                          (?P=quote)
                     ''',
                     flags=re.VERBOSE,
                     attrs=STRING)

        Header = regex(r'^(\*{2,}|={2,}|\^{2,}|-{2,}|"{2,}|#{2,})', PREPROC)

        Comment = regex(r'^\.\.(?!\s*(?::?\w+[:]|_)).*', COMMENT)

        All = region(guard=None,
                     exit=None,
                     contains=[Bullet, SQString, DQString, Emph, Header, Comment])
        
    return RSTLexer

class RSTCodeModel(api.IndentRetainingCodeModel):
    completion_triggers = []
    call_tip_triggers = []
    open_braces = ''
    close_braces = ''
    statement_start = ['::']
    reindent_triggers = ''
    line_comment = '..'

    indent_after = r'::'
    dedent_before = None



    def highlight(self):
        highlighter = syntaxlib.SyntaxHighlighter(
            'stem.plugins.rst',
            lexer().All,
            dict(lexcat=None)
        )

        highlighter.highlight_buffer(self.buffer)




@api.register_plugin
class RSTPlugin(api.Plugin):
    name = 'reStructuredText Code Model'

    def attach(self):
        api.Filetype('reST', ['.rst'], RSTCodeModel)

    def detach(self):
        pass


