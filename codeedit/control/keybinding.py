

from ..core import key
from . import interactive



class KeybindingController(object):
    
    def __init__(self):    
        self._bindings = key.KeySequenceDict()

    def add_binding(self, key_seq, interactive_name):
        self._bindings[key_seq] = interactive_name

    def remove_binding(self, key_seq):
        del self._bindings[key_seq]

    
    def invoke_binding(self, responder, key_seq):
        try:
            binding = self._bindings[key_seq]
        except KeyError:
            return False
        else:
            interactive.dispatcher.dispatch(
                responder,
                binding
            )

            return True

controller = KeybindingController()
