


from abc import ABCMeta, abstractmethod
from ..core import Signal


class AbstractCompletionView(metaclass=ABCMeta):

    @Signal
    def row_changed(self, row):
        pass

    @property
    @abstractmethod
    def current_row(self): 
        pass

    @Signal
    def done(self):
        pass

    @property
    @abstractmethod
    def completions(self):
        pass

    @completions.setter
    @abstractmethod
    def completions(self, val):
        pass

    @property
    @abstractmethod
    def visible(self): 
        pass
    
    @visible.setter
    @abstractmethod
    def visible(self, value): 
        pass

    @property
    @abstractmethod
    def anchor(self): 
        '''
        The (line, col) position to which the completion view should be 
        anchored.
        '''
        pass
    
    @anchor.setter
    @abstractmethod
    def anchor(self, value): 
        pass

    
    @property
    @abstractmethod
    def doc_view_visible(self): 
        pass
    
    @doc_view_visible.setter
    @abstractmethod
    def doc_view_visible(self, value): 
        pass

    @property
    @abstractmethod
    def doc_view(self): 
        pass

class TextPopupView(metaclass=ABCMeta):

    @property
    @abstractmethod
    def anchor(self): 
        pass
    
    @anchor.setter
    @abstractmethod
    def anchor(self, value): 
        pass

    @property
    @abstractmethod
    def visible(self): 
        pass
    
    @visible.setter
    @abstractmethod
    def visible(self, value): 
        pass

    

