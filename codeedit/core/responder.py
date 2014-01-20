
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
        self.next_responder = None
        
        cls = type(self)
        if getattr(cls, '_responder_derived', None) is not cls:
            def gen_method_for_command():
                for name, method in vars(cls).items():
                    responsible = _get_responsible(method)
                    for command in responsible:
                        yield command, method
            
            cls._method_for_command = dict(gen_method_for_command())
            cls._responder_derived = cls

    @property
    def next_responder(self): 
        return self._next_responder
    
    @next_responder.setter
    def next_responder(self, value): 
        old_responder = getattr(self, '_next_responder', None)
        if old_responder is not None:
            old_responder.responder_chain_changed.disconnect(self.responder_chain_changed)
        
        self._next_responder = value
        if value is not None:
            value.responder_chain_changed.connect(self.responder_chain_changed)

        self.responder_chain_changed()

    
    def perform_or_forward(self, command, *args):
        cls = type(self)
        method = cls._method_for_command.get(command)
        if method is None:
            if self.next_responder is None:
                logging.warning('No responder for %r.', command)
                return False
            else:
                return self.next_responder.perform_or_forward(command, *args)
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

        if self.next_responder is not None:
            result.update(self.next_responder.responder_known_commands)

        return result
        
    def responds_to(self, command):
        cls = type(self)
        return command in cls._method_for_command

    def any_responds_to(self, command):
        return (
            self.responds_to(command) or (
                self.next_responder is not None and 
                self.next_responder.any_responds_to(command)
            )
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



