
import string
from concurrent.futures import Future

from stem.abstract.code import IndentRetainingCodeModel, AbstractCompletionResults
from stem.plugins.semantics.syntax import SyntaxHighlighter
from stem.core.processmgr.client import AsyncServerProxy
from stem.core.fuzzy import FuzzyMatcher, Filter
from stem.core.conftree import ConfTree
from stem.buffers import Cursor

from .syntax import cpplexer
from .worker import SemanticEngine
from .modelworker import InitWorkerTask, CompletionTask, FindRelatedTask, GetDocsTask
from .config import CXXConfig        
class CXXCompletionResults(AbstractCompletionResults):
    def __init__(self, token_start, runner, results):
        '''
        token_start - the (line, col) position at which the token being completed starts
        '''
        super().__init__(token_start)
        self._runner = runner
        self._results = results        
        self.filter()
        
    def doc_async(self, index):
        '''
        Return a Future for the documentation for a given completion result as a list of 
        AttributedString.        
        '''
        
        return self._runner.submit(GetDocsTask(self._filt.indices[index]))

    @property
    def rows(self):
        '''
        Return a list of tuples of AttributedString containing the contents of 
        each column for each row in the completion results.
        '''
        
        return self._filt.rows
        
    def text(self, index):
        '''
        Return the text that should be inserted for the given completion.
        '''
        return self._filt.rows[index][0].text

    def filter(self, text=''):
        '''
        Filter the completion results using the given text.
        '''
        
        fm = FuzzyMatcher(text)
        self._filt = fm.filter(self._results, lambda item: item[0].text)    
        
    def dispose(self):
        pass
        

class CXXCodeModel(IndentRetainingCodeModel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cxx_config = CXXConfig.from_config(self.conf)
        self.prox = AsyncServerProxy()
        self.prox.start()
        self.prox.submit(InitWorkerTask(self.cxx_config)).result()

    
    def submit_task(self, task, transform=None):
        '''
        Public interface for submitting tasks to be run in the completion process.
        
        Task must be a pickleable callable that takes one argument. The argument will
        be a SimpleNamespace object containing a field `engine`. The `engine` field 
        contains an instance of `modelworker.Engine`.
        
        The result of the task is returned as a future. If a transform is provided, the
        transform will be applied clientside (i.e., not in the completion process) 
        before setting the future's result. This means that the transform need not be 
        pickleable.
        '''
        
        return self.prox.submit(task, transform)

    def _find_token_start(self, pos):
        c = Cursor(self.buffer).move(pos)

        wordchars = string.ascii_letters + string.digits + '_$'
        for i, ch in reversed(list(enumerate(c.line[:c.x]))):
            if ch not in wordchars:
                break
        else:
            i = -1
            

        return c.y, i + 1
                
    def completions_async(self, pos):
        '''
        Return a future to the completions available at the given position in the document.
        
        Raise NotImplementedError if not implemented.
        '''
        tstart = self._find_token_start(pos)
        return self.prox.submit(
            CompletionTask(
                self.path,
                tstart,
                [(str(self.path), self.buffer.text)]
            ),
            transform=lambda r: CXXCompletionResults(tstart, self.prox, r)
        )
    
    def find_related_async(self, pos, types):
        '''
        Find related names for the token at the given position.      
        
        Raises NotImplementedError by default.
        
        :rtype: concurrent.futures.Future of list of RelatedName
        '''
        
        return self.prox.submit(
            FindRelatedTask(
                types,
                self.path,
                pos,
                [(str(self.path), self.buffer.text)]
            )
        )

    
    def highlight(self):
        '''
        Rehighlight the buffer.        
        
        Note: This is different than other methods in the code model in that
        it involves mutation of the buffer, and it may be better to make
        the code model a factory for a "Highlighter" object.        
        '''
        
        highlighter = SyntaxHighlighter(
            'stem.plugins.cpp.syntax',
            cpplexer(),
            dict(lexcat=None)
        )
        
        highlighter.highlight_buffer(self.buffer)
    
    
    def dispose(self):
        '''
        Release system resources held by the model.
        '''
        
        self.prox.shutdown()
        
