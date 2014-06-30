import re
import keyword
import logging
import textwrap

from concurrent import futures

from stem.api import BufferController, autoconnect, Plugin, register_plugin, command
from stem.options import GeneralSettings
from stem.plugins.semantics.syntax import SyntaxHighlighter, lazy
from stem.abstract.code import IndentRetainingCodeModel, AbstractCompletionResults
from stem.core import AttributedString
from stem.buffers.cursor import Cursor
from stem.core import nconfig, filetype
from stem.core.fuzzy import FuzzyMatcher
from stem.core.executors import future_wrap

from stem.plugins.semantics.syntaxlib import RegexLexer

@lazy
def yaml_lexer():
    from stem.plugins.semantics.syntaxlib import keyword, regex, region
    import re
    
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

    HEX         = r'[a-fA-F0-9]'

    NSCHAR      = r'[^\s]'
    
    Keyword     = keyword('true false'.split(), KEYWORD)

    Key         = regex(NSCHAR + r'+\s*:', FUNCTION)

    Tag         = regex(r'!' + NSCHAR + r'+', TYPE)


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
    
    SQEsc       = regex(r"''", ESCAPE)
    SQString    = region(guard=regex(r"'(?!'')"),
                         exit=regex(r"'"),
                         contains=[SQEsc],
                         attrs=STRING)
    

    HexLit      = regex(r'\b0x[0-9a-fA-F]?\b', NUMBER)
    DecLit      = regex(r'\b[\d]+\b', NUMBER)
    FloatLit    = regex(r'\b(?:\d+\.\d*|\.\d+)\b', NUMBER)
    
    Todo        = regex(r'\btodo:|\bfixme:|\bhack:', TODO, flags=re.IGNORECASE)
    Comment     = region(guard=regex('#'),
                         exit=regex('$'),
                         contains=[Todo],
                         attrs=COMMENT)
    
    Ref         = regex('[&*]' + NSCHAR + '+', PREPROC)
    
    Delim       = regex(r'^(---|\.\.\.)$', PREPROC)
    
    YAML = region(
            guard=None,
            exit=None,
            contains=[Keyword, Key, DQString, SQString, Comment, Tag,
                      Ref, HexLit, DecLit, FloatLit, Delim]
        )


    return YAML

class YAMLCompletionResults(AbstractCompletionResults):

    def __init__(self, token_start, results):
        super().__init__(token_start)

        self.results = [x[:2] for x in results]
        self.docs = [x[2] for x in results]

            
        self.filter()        
    
    @future_wrap
    def doc_async(self, index):
        '''
        Return a Future for the documentation for a given completion result as a list of 
        AttributedString.        
        '''
        
        d = self.docs[self._filtered.indices[index]]
        if d is None:
            return []
        else:
            if d.__doc__ is not None:
                docs = [AttributedString(textwrap.dedent(d.__doc__))]
            else:
                docs = []
            return [AttributedString.join(': ', [AttributedString(d.name),
                                                 AttributedString(d.type.__name__, lexcat='type')])] + docs
        return f
        
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
        

class YAMLCodeModel(IndentRetainingCodeModel):
    
    completion_triggers = []
    
    def highlight(self):
        highlighter = SyntaxHighlighter(
            'stem.plugins.yaml',
            yaml_lexer(),
            dict(lexcat=None)
        )
    
        highlighter.highlight_buffer(self.buffer)

    
    @future_wrap
    def completions_async(self, pos):
        '''
        Return a future to the completions available at the given position in the document.
        
        Raise NotImplementedError if not implemented.
        '''

        c = Cursor(self.buffer).move(pos)
        text_to_pos = c.line.text[:c.x]
        
        for x, ch in reversed(list(enumerate(text_to_pos))):
            if ch.isspace():
                x += 1
                break
        else:
            x = 0
        
        pos = c.y, x
        
        def indent():
            m = c.searchline(r'^\s*')
            if m:
                return len(m.group(0).expandtabs())
            else:
                return 0
            
        cur_indent = indent()
        for _ in c.walklines(-1):
            if indent() < cur_indent:
                cur_key = c.line.text.strip().strip(':')
                break
        else:
            cur_key = None
            
                
        
        buffer_text = AttributedString('buffer text', lexcat='comment')
        namespace = AttributedString('namespace', lexcat='preprocessor')
        
        sfield = AttributedString('safe field', lexcat='function')
        ufield = AttributedString('unsafe field', lexcat='escape')
        
        compls = [] 
        compls += [(AttributedString(s), namespace, None) for s in nconfig.namespaces()]
        
        if cur_key is not None:
            try:
                ns = nconfig.namespaces()[cur_key]
            except KeyError:
                pass
            else:
                compls += [(AttributedString(f.name), sfield if f.safe else ufield, f) for f in ns._fields_.values()]
        compls += [(AttributedString(s), buffer_text, None) for s in re.findall(r'[\w\d]+', self.buffer.text)]
        return YAMLCompletionResults(pos, compls)


@register_plugin
class YAMLPlugin(Plugin):
    name = 'YAML Plugin'
    author = 'Sam Roth'

    def attach(self):
        filetype.Filetype('yaml',
                          suffixes=('.yaml', ),
                          code_model=YAMLCodeModel,
                          tags={'parmatch': True})

        self.app.editor_created.connect(self.on_editor_creation)

    def detach(self):
        self.app.editor_created.disconnect(self.on_editor_creation)


    def on_editor_path_change(self, ed):
        if ed.path is not None and ed.path.suffix == '.yaml':
            settings = GeneralSettings.from_config(ed.config)
            if '\t' in settings.indent_text:
                settings.indent_text = settings.tab_stop * ' '
    

    def on_editor_creation(self, ed):
        ed.path_changed.connect(self.on_editor_path_change, add_sender=True)
        


