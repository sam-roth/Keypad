
import inspect


# from .buffer_controller import BufferController
# 
# 
# # Just a little function to remind me what I'm doing:
# 
# @interactive('write')
# def write_buffer(obj:   BufferController,
#                  path:  str):
#     
#     from pathlib import Path
#     obj.write_to_path(Path(path))
# 
# 
# write_buffer.__annotations__


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
        argspec = inspect.getfullargspec(impl)

        annots = [argspec.annotations.get(arg) for arg in argspec.args]

        assert len(annots) >= 1, 'must annotate at least target object type'


        self._registry[name][annots[0]] = impl
        #self._registry[name].append((annots[0], impl))
    
    def dispatch(self, responder, name, *args):
        handlers = self._registry[name]

        tried = set()

        def rec_helper(resp):
            
            for ty in type(resp).mro():
                try:
                    handler = handlers[ty]
                except KeyError:
                    tried.add(ty)
                else:
                    handler(resp, *args)
                    return True
            else:
                for r in resp.next_responders:
                    if rec_helper(r):
                        return True
                else:
                    return False
        
        if not rec_helper(responder):
            raise errors.UserError('No match for command ' + name + '. Tried: ' + ', '.join(map(str, tried)))





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

def menu(priority, path, interactive_name, *args, keybinding=None):
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


def submenu(priority, path):
    _set_priority_by_path(root_menu, path.split('/'), priority)

def get_menu_item(path):
    return _get_item_by_path(root_menu, path.split('/'))


def interactive(*names):
    def result(func):
        for name in names:
            dispatcher.register(name, func)
        return func
    return result


def run(name, *args):
    dispatcher.dispatch(app().next_responder, name, *args)
