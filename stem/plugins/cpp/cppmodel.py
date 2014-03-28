
from concurrent.futures import Future

from stem.abstract.code import IndentRetainingCodeModel, AbstractCompletionResults
from stem.plugins.semantics.syntax import SyntaxHighlighter
from stem.core.processmgr.client import AsyncServerProxy
from stem.core.fuzzy import FuzzyMatcher, Filter
from stem.core.conftree import ConfTree

from .syntax import cpplexer
from .worker import SemanticEngine

class CXXCompletionResults(AbstractCompletionResults):
    def __init__(self, token_start, results):
        '''
        token_start - the (line, col) position at which the token being completed starts
        '''
        super().__init__(token_start)

        self._results = results        
        self.filter()
        
    def doc_async(self, index):
        '''
        Return a Future for the documentation for a given completion result as a list of 
        AttributedString.        
        '''
        
        raise NotImplementedError

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
        
        return self._get_typed_text(self._filt.rows[index][0])

    def filter(self, text=''):
        '''
        Filter the completion results using the given text.
        '''
        
        fm = FuzzyMatcher(text)
        self._filt = fm.filter(self._results, lambda item: item[0].text)    
        
    def dispose(self):
        pass
        
    @staticmethod
    def _get_typed_text(cstring):
        def gen():
            for chunk, deltas in cstring.iterchunks():
                if deltas.get('kind') == 'TypedText':
                    yield chunk
        return ''.join(gen())

from .modelworker import InitWorkerTask, CompletionTask, FindRelatedTask
from .config import CXXConfig        

class CXXCodeModel(IndentRetainingCodeModel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cxx_config = CXXConfig.from_config(self.conf)
        self.prox = AsyncServerProxy()
        self.prox.start()
        self.prox.submit(InitWorkerTask(self.cxx_config)).result()

    
    def completions_async(self, pos):
        '''
        Return a future to the completions available at the given position in the document.
        
        Raise NotImplementedError if not implemented.
        '''
        
        return self.prox.submit(
            CompletionTask(
                self.path,
                pos,
                [(str(self.path), self.buffer.text)]
            ),
            transform=lambda r: CXXCompletionResults(pos, r)
        )
    
    def find_related_async(self, pos, types):
        '''
        Find related names for the token at the given position.
        
        decl       - find declarations
        defn       - find definitions
        assign     - find assignments
        
        
        Raises NotImplementedError by default.
        
        :rtype: concurrent.futures.Future of list of RelatedName
        '''
        
        return self.prox.submit(
            FindRelatedTask(
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
        
