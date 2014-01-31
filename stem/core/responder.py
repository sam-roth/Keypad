
import logging
import weakref
from .signal import Signal
import sys

class Responder(object):
    '''
    Base class for objects that control the distribution of user interaction
    (`@interactive`) commands.
    '''
    # TODO: Example

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._next_responders = weakref.WeakSet()
        
    def add_next_responders(self, *responders):
        '''
        If there's no matching `@interactive` command at this level, try finding one that matches
        one of these objects.
        '''
        new_responders = weakref.WeakSet(responders) - self._next_responders
        for responder in new_responders:
            responder.responder_chain_changed.connect(self.responder_chain_changed)
        self._next_responders.update(new_responders)

        self.responder_chain_changed()


    def remove_next_responders(self, *responders):
        for responder in responders:
            self._next_responders.remove(responder)
            responder.responder_chain_changed.disconnect(self.responder_chain_changed)

        self.responder_chain_changed()

    def clear_next_responders(self):
        self.remove_next_responders(*self._next_responders)

    @property
    def next_responders(self):
        return list(self._next_responders)
    

    @property
    def next_responder(self): 
        if self._next_responders:
            return next(iter(self._next_responders))
        else:
            return None
    
    @next_responder.setter
    def next_responder(self, value): 
        self.clear_next_responders()
        self.add_next_responders(value)
    
    @Signal
    def responder_chain_changed(self):
        pass

