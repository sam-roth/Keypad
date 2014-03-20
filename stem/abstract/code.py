
from abc import ABCMeta, abstractmethod
from enum import IntEnum

class AbstractCompletionResults(metaclass=ABCMeta):

    def __init__(self, token_start):
        '''
        token_start - the (line, col) position at which the token being completed starts
        '''
        self.token_start = token_start

    @abstractmethod
    def doc_async(self, index):
        '''
        Return a Future for the documentation for a given completion result as a list of 
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
    def text(self, index):
        '''
        Return the text that should be inserted for the given completion.
        '''

    @abstractmethod
    def filter(self, text=''):
        '''
        Filter the completion results using the given text.
        '''

    @abstractmethod
    def dispose(self):
        pass

class RelatedNameType(IntEnum):
    decl = 1
    defn = 2
    assign = 4
    use = 8
    
    all = decl | defn | assign | use

class RelatedName(object):

    Type = RelatedNameType
            
    def __init__(self, type_, path, pos, name):
        self.type = type_
        self.path = path
        self.pos = pos
        self.name = name
    
    
    def __repr__(self):
        return 'RelatedName{!r}'.format((
            self.type,
            self.path,
            self.pos,
            self.name
        ))
        
class AbstractCodeModel(metaclass=ABCMeta):   
    '''
    The code model represents the editor's knowledge of the semantics of the
    buffer contents.
    
    :ivar buffer:      The buffer that this code model is built from.
    :ivar path:        The path where the buffer will be saved
    :ivar conf:        The ConfTree containing configuration information for this object.
    '''
    
    RelatedNameType = RelatedNameType
    completion_triggers = ['.']
    
    def __init__(self, buff, conf):
        '''
        :type buff: stem.buffers.Buffer
        :type conf: stem.core.conftree.ConfTree
        '''
        self.buffer = buff
        self.path = None
        self.conf = conf
    
    @abstractmethod
    def indent_level(self, line):
        '''
        Return the indentation level as a multiple of the tab stop for a given line.
        '''
        
    @abstractmethod
    def completions_async(self, pos):
        '''
        Return a future to the completions available at the given position in the document.
        
        Raise NotImplementedError if not implemented.
        '''
    
    def find_related_async(self, pos, types):
        '''
        Find related names for the token at the given position.
        
        decl       - find declarations
        defn       - find definitions
        assign     - find assignments
        
        
        Raises NotImplementedError by default.
        
        :rtype: concurrent.futures.Future of list of RelatedName
        '''
        raise NotImplementedError

    
    @abstractmethod
    def highlight(self):
        '''
        Rehighlight the buffer.        
        
        Note: This is different than other methods in the code model in that
        it involves mutation of the buffer, and it may be better to make
        the code model a factory for a "Highlighter" object.        
        '''
        
    @abstractmethod
    def dispose(self):
        '''
        Release system resources held by the model.
        '''