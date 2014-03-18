
from abc import ABCMeta, abstractmethod

class AbstractCompletionResults(metaclass=ABCMeta):
    
    @abstractmethod
    def docs(self, index):
        '''
        Return the documentation for a given completion result as a list of 
        AttributedString.
        '''

    @property
    @abstractmethod
    def rows(self):
        '''
        Return a list of tuples of AttributedString containing the contents of 
        each column for each row in the completion results.
        '''
        
    @abstractmethod
    def filter(self, text):
        '''
        Filter the completion results using the given text.
        '''
        
class AbstractCodeModel(metaclass=ABCMeta):
    '''
    The code model represents the editor's knowledge of the semantics of the
    buffer contents.
    
    :ivar buffer:  The buffer that this code model is built from.
    :ivar path:    The path where the buffer will be saved
    '''
    def __init__(self, buff):
        '''
        :type buff: stem.buffers.Buffer
        '''
        self.buffer = buff
        self.path = None
    
    @abstractmethod
    def indent_level(self, line):
        '''
        Return the indentation level as a multiple of the tab stop for a given line.
        
        Thread safety: perform in main thread only.
        '''
        
    @abstractmethod
    def completions(self, pos):
        '''
        Return the completions available at the given position in the document.

        Thread safety: perform in any thread.
        '''
    
    @abstractmethod
    def highlight(self):
        '''
        Rehighlight the buffer.        
        
        Thread safety: perform in main thread only.
        '''
        