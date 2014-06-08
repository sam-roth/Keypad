import subprocess
import shlex

from stem.api import (Plugin,
                      register_plugin,
                      Filetype,
                      Cursor)

from stem.abstract.code import IndentRetainingCodeModel, AbstractCompletionResults
from stem.plugins.semantics.syntax import SyntaxHighlighter, lazy
from stem.core.processmgr.client import AsyncServerProxy
from stem.core.fuzzy import FuzzyMatcher
from stem.core.executors import future_wrap
from stem.core.attributed_string import AttributedString

@lazy
def lexer():
    from . import bourne_lexer
    return bourne_lexer.Shell
    
class GetManPage:
    def __init__(self, cmd):
        self.cmd = cmd

    def __call__(self, ns):
        with subprocess.Popen(['man', self.cmd], stdout=subprocess.PIPE) as proc:
            out, _ = proc.communicate()



        import re

        return [re.subn('.\x08', '', out.decode())[0]]

class ShellCompletionResults(AbstractCompletionResults):

    def __init__(self, token_start, results, prox):
        '''
        token_start - the (line, col) position at which the token being completed starts
        '''

        super().__init__(token_start)
        self.results = [(AttributedString(x.decode()),) for x in results]
        self._prox = prox

    def doc_async(self, index):
        '''
        Return a Future for the documentation for a given completion result as a list of 
        AttributedString.        
        '''
        
        return self._prox.submit(GetManPage(self.text(index)))

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
        self._filtered = FuzzyMatcher(text).filter(self.results, key=lambda x: x[0].text)
        self._filtered.sort(lambda item: len(item[0].text))

    def dispose(self):
        pass


class GetPathItems:
    def __init__(self, prefix):
        self.prefix = prefix
    def __call__(self, ns):

        with subprocess.Popen(['bash',
                               '-c',
                               'compgen -c ' + shlex.quote(self.prefix)],
                              stdout=subprocess.PIPE) as proc:
            out, _ = proc.communicate()

        return [l.strip() for l in out.splitlines()]

class BourneCodeModel(IndentRetainingCodeModel):
    completion_triggers = []

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._prox = AsyncServerProxy()
        self._prox.start()

    def dispose(self):
        self._prox.shutdown()
        super().dispose()
    
    def highlight(self):
        '''
        Rehighlight the buffer.        
        '''
    
        
        highlighter = SyntaxHighlighter(
            'stem.plugins.shell.syntax',
            lexer(),
            dict(lexcat=None)
        )
        
        highlighter.highlight_buffer(self.buffer)
    
    
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
        

        print('text_to_pos', text_to_pos[x:], pos)

        return self._prox.submit(GetPathItems(text_to_pos[x:]),
                                 transform=lambda r: ShellCompletionResults((pos[0], x), r,
                                                                            self._prox))
        