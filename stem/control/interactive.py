
import inspect


from collections import defaultdict, namedtuple
from ..core import responder, errors
from ..abstract.application import app
import threading
import contextlib

class _DynamicScope(threading.local): 
    
    @contextlib.contextmanager
    def let(self, **bindings):
        sentinel = object()
        
        existing_bindings = {attr: getattr(self, attr, sentinel) for attr in bindings.keys()}
        
        for attr, binding in bindings.items():
            setattr(self, attr, binding)

        try:
            yield
        finally:
            for attr, binding in existing_bindings.items():
                if binding is not sentinel:
                    setattr(self, attr, binding)
                else:
                    delattr(self, attr)


Dynamic = _DynamicScope()


class InteractiveDispatcher(object):
    
    def __init__(self):
        self._registry = defaultdict(dict)

    def register(self, name, impl):
        sig = inspect.signature(impl)
        
        annots = [p.annotation
                  for p in sig.parameters.values()]
        

        assert len(annots) >= 1, 'must annotate at least target object type'

        self._registry[name][annots[0]] = impl

    def unregister(self, name, impl):
        sig = inspect.signature(impl)
        
        annots = [p.annotation
                  for p in sig.parameters.values()]

        assert len(annots) >= 1, 'must annotate at least target object type'

        try:
            del self._registry[name][annots[0]]
        except KeyError:
            pass

    def keys(self):
        return self._registry.keys()

    def find_all(self, name):
        return self._registry[name].items()
    

        
    def try_to_find(self, responder, name, *args):    

        handlers = self._registry[name]

        tried = set()

        def rec_helper(resp):
            for ty in type(resp).mro():
                try:
                    handler = handlers[ty]
                except KeyError:
                    tried.add(ty)
                else:
                    return ty, resp, handler
            else:
                if resp is None:
                    return None
                for r in resp.next_responders:
                    result = rec_helper(r)
                    if result is not None:
                        return result
                else:
                    return None
        
        return rec_helper(responder)
        
    def find(self, responder, name, *args):
        result = self.try_to_find(responder, name, *args)
        if result is None:
            raise errors.NoSuchCommandError('No applicable command {!r}'.format(name))

        return result

    def dispatch(self, responder, name, *args):
        ty, resp, handler = self.find(responder, name, *args)
        res = handler(resp, *args)
        if res is interactive.call_next:
            for nresp in resp.next_responders:
                try:
                    self.dispatch(nresp, name, *args)
                except errors.NoSuchCommandError:
                    pass
                else:
                    return
            else:
                raise errors.NoSuchCommandError('No applicable command {!r}'.format(name))
                
                
        
        
class Menu(object):
    def __init__(self, inline=False):
        self._items = {}
        self.inline = inline

    def add_item(self, name, priority, item):
        self._items[name] = priority, item
    
    def remove_item(self, name):
        del self._items[name]

    def set_item_priority(self, name, priority):
        item = self.get_item(name, insert=True)
        self._items[name] = priority, item

    def get_item(self, name, insert=False):
        try:
            return self._items[name][1]
        except KeyError:
            if not insert:
                raise
            
            result = Menu()
            self.add_item(name, priority=100000, item=result)
            return result


    def __iter__(self):
        for name, (priority, item) in sorted(self._items.items(), 
                                             key=lambda x: x[1][0],
                                             reverse=False):
            yield name, item


class MenuItem(object):
    def __init__(self, keybinding, interactive_name, *args):
        self.keybinding = keybinding
        self.interactive_name = interactive_name
        self.interactive_args = args


MenuPath = namedtuple('MenuPath', 'hier priority')

def _add_menu_by_hier(menu, item, hier_parts, priority):
    if len(hier_parts) == 1:
        menu.add_item(hier_parts[0], priority, item)
    else:
        _add_menu_by_hier(menu.get_item(hier_parts[0]), item, hier_parts[1:], priority)


def _set_priority_by_path(menu, path_parts, priority):
    if len(path_parts) == 1:
        menu.set_item_priority(path_parts[0], priority)
    else:
        _set_priority_by_path(menu.get_item(hier_parts[0]), path_parts[1:], priority)
        

def _get_item_by_path(menu, path_parts):
    if len(path_parts) == 1:
        return menu.get_item(path_parts[0], insert=True)
    else:
        return _get_item_by_path(menu.get_item(path_parts[0]), path_parts[1:], priority)


dispatcher = InteractiveDispatcher()

root_menu = Menu()

def menu(priority, path, interactive_name=None, *args, keybinding=None):
    if interactive_name is None:
        _set_priority_by_path(root_menu, path.split('/'), priority)
    else:
        _add_menu_by_hier(
            root_menu,
            MenuItem(
                keybinding,
                interactive_name,
                *args
            ),
            path.split('/'),
            priority
        )


def get_menu_item(path):
    return _get_item_by_path(root_menu, path.split('/'))

class interactive(object):
    """
    Decorator for interactive commands. Use this to mark functions that should be invokable 
    from the command line.
    
    The first argument to the decoratee is the first active :class:`Responder <stem.core.responder.Responder>`
    that matches the parameter's annotation. If you don't care which responder gets injected into the first
    argument, simply use ``object`` as the annotation. Subsequent arguments are the tokens provided on the command
    line. You may annotate these with a string indicating the expected type for code completion purposes.
    Currently, 'Interactive' and 'Path' are recognized.
    
    Example::
            
        @interactive('idecl')
        def find_interactive_declaration(_: object, interactive_name: 'Interactive'):
            '''
            idecl <interactive_name>
        
            Show the file and line where the interactive command is located.
        
            Example
            =======
        
            : idecl idecl
            idecl(object, ...)
              .../stem/control/behavior.py:24
            '''
        
            from .command_line_interaction import writer
            
            for ty, handler in dispatcher.find_all(interactive_name):
                code = handler.__code__
                
                
                filename = code.co_filename
                linenum = code.co_firstlineno
                
                tyname = ty.__name__
        
                writer.write('{interactive_name}({tyname}, ...)\\n  {filename}:{linenum}'.format(**locals()))
                
    """
    call_next = object()
    
    @classmethod
    def run(cls, name, *args):
        run(name, *args)

    def __init__(self, *names):
        self.names = names

    def __call__(self, func):
        for name in self.names:
            dispatcher.register(name, func)
        return func        


def run(name, *args):
    dispatcher.dispatch(app().next_responder, name, *args)
