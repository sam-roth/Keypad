
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


from collections import defaultdict
from ..core import responder, errors


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
            raise errors.UserError('No match for command. Tried: ' + ', '.join(map(str, tried)))



dispatcher = InteractiveDispatcher()

def interactive(*names):
    def result(func):
        for name in names:
            dispatcher.register(name, func)
        return func
    return result
