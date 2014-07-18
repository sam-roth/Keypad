
import re


from stem.api import *
from stem.core.attributed_string import AttributedString
from stem.abstract.code import IndentRetainingCodeModel, Indent, AbstractCompletionResults
from stem.core.executors import future_wrap
from stem.core.fuzzy import FuzzyMatcher

from stem.core.syntaxlib import (regex, region, keyword,
                                 lazy, SyntaxHighlighter)

# from stem.plugins.semantics.syntaxlib import regex, region, keyword
# from stem.plugins.semantics.syntax import lazy, SyntaxHighlighter

@lazy
def lexer():
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

    var = region(guard=regex(r'\${'),
                 exit=regex(r'}'),
                 contains=[regex(r'[^}]+', PREPROC)],
                 attrs=ESCAPE)

    dqstring = region(guard=regex(r'"'),
                      exit=regex(r'"'),
                      contains=[regex(r'\\.', ESCAPE),
                                var],
                      attrs=STRING)

    func = regex(r'\b(?P<body>\w+)([ \t]*)(?=\()', FUNCTION)

    comment = region(guard=regex('#'),
                     exit=regex('$'),
                     contains=[keyword(['todo', 'hack', 'xxx', 'fixme'], TODO, caseless=True)],
                     attrs=COMMENT)

    return region(guard=None,
                  exit=None,
                  contains=[var, dqstring, func, comment])


class CMakeCodeModel(IndentRetainingCodeModel):
    statement_start = '('
    reindent_triggers = ')'
    indent_after = r'\(\s*$'
    dedent_before = r'^\s*\)\s*$'

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def alignment_column(self, pos, *, timeout_ms=50):
        return None

    @future_wrap
    def completions_async(self, pos):
        c = Cursor(self.buffer).move(pos)
        text_to_pos = c.line.text[:c.x]

        for x, ch in reversed(list(enumerate(text_to_pos))):
            if not ch.isalnum() and ch not in '_':
                x += 1
                break
        else:
            x = 0

        pos = c.y, x

        compls = [(AttributedString(s), ) for s in sorted(frozenset(re.findall(r'[\w\d]+', self.buffer.text)))]


        return CMakeCompletionResults(pos, compls)

    def highlight(self):
        highlighter = SyntaxHighlighter(
            'stem.plugins.cmake',
            lexer(),
            dict(lexcat=None)
        )

        highlighter.highlight_buffer(self.buffer)

class CMakeCompletionResults(AbstractCompletionResults):

    def __init__(self, token_start, results):
        super().__init__(token_start)

        self.results = results
        self.filter()        

    @future_wrap
    def doc_async(self, index):
        '''
        Return a Future for the documentation for a given completion result as a list of 
        AttributedString.        
        '''

        return []
          
    @property
    def rows(self):
        '''
        Return a list of tuples of AttributedString containing the contents of 
        each column for each row in the completion results.
        '''
        return self._filtered.rows


    def text(self, index):
        '''
        Return the text that should be inserted for the given completion.
        '''
        return self._filtered.rows[index][0].text


    def filter(self, text=''):
        '''
        Filter the completion results using the given text.
        '''

        self._filtered = FuzzyMatcher(text).filter(self.results, lambda item: item[0].text)
        self._filtered.sort(lambda item: len(item[0].text))


    def dispose(self):
        pass


@register_plugin
class CMakePlugin(Plugin):
    name = 'CMake Code Model'
    author = 'Sam Roth'
    version = '2014.06.1'

    def attach(self):
        Filetype('cmake', ('.cmake', ), CMakeCodeModel)

        self.app.editor_created.connect(self.editor_created)

    def editor_path_changed(self, editor):
        assert isinstance(editor, AbstractEditor)
        import pathlib
        if editor.path.name == 'CMakeLists.txt':
            editor.buffer_controller.code_model = CMakeCodeModel(editor.buffer_controller.buffer,
                                                                 editor.config)



    def editor_created(self, editor):
        assert isinstance(editor, AbstractEditor)
        editor.path_changed.connect(self.editor_path_changed, add_sender=True)

    def detach(self):
        self.app.editor_created.disconnect(self.editor_created)


