
import logging
import weakref
from .signal import Signal

def responds(*commands, add_command=None):
    def result(func):
        if not hasattr(func, '_responder_reponds'):
            func._responder_responds = set()
        func._responder_responds.update(commands)
        if add_command is not None:
            func._responder_add_command = add_command
        return func
    return result

def _get_responsible(func):
    return getattr(func, '_responder_responds', set())

def _should_add_command(func):
    return getattr(func, '_responder_add_command', False)

class Responder(object):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._next_responders = set()
        
        cls = type(self)
        if getattr(cls, '_responder_derived', None) is not cls:
            def gen_method_for_command():
                for name, method in vars(cls).items():
                    responsible = _get_responsible(method)
                    for command in responsible:
                        yield command, method
            
            cls._method_for_command = dict(gen_method_for_command())
            cls._responder_derived = cls

    
    def add_next_responders(self, *responders):
        new_responders = set(responders) - self._next_responders
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
        yield from self._next_responders
    

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
    
    def perform_or_forward(self, command, *args):
        cls = type(self)
        method = cls._method_for_command.get(command)
        if method is None:
            if self.next_responder is None:
                logging.warning('No responder for %r.', command)
                return False
            else:
                return any(next_responder.perform_or_forward(command, *args) 
                           for next_responder in self.next_responders)
        else:
            if _should_add_command(method):
                method(self, command, *args)
            else:
                method(self, *args)
            return True

    @property
    def responder_known_commands(self):
        cls = type(self)
        result = set(cls._method_for_command.keys()) 

        
        for next_responder in self.next_responders:
            result.update(next_responder.responder_known_commands)

        return result
        
    def responds_to(self, command):
        cls = type(self)
        return command in cls._method_for_command

    def any_responds_to(self, command):
        return (
            self.responds_to(command) or 
            any(next_responder.any_responds_to(command)
                for next_responder in self.next_responders)
        )

    @Signal
    def responder_chain_changed(self):
        pass

def main():
    from . import command

    open_cmd = command.Command('Open')
    save_cmd = command.Command('Save')


    class Base(Responder):
        
        @responds(open_cmd)
        def open(self):
            print('Base.open')

    class Derived(Base):

        @responds(open_cmd)
        def open(self):
            print('Derived.open')


    class Delegated(Responder):

        @responds(save_cmd)
        def save(self):
            print('Delegated.save')
    
    b = Base()
    d = Derived()

    d.next_responder = Delegated()

    assert Base._responder_derived is not Derived._responder_derived

    d.perform_or_forward(open_cmd)
    b.perform_or_forward(open_cmd)
    d.perform_or_forward(save_cmd)
    b.perform_or_forward(save_cmd)


    d2 = Derived()
    b2 = Base()
    d2.perform_or_forward(open_cmd)
    b.perform_or_forward(open_cmd)

if __name__ == '__main__':
    main()



