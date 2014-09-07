

import functools
import threading



def nonreentrant(func):
    in_call = threading.local()
    in_call.value = False
    @functools.wraps(func)
    def replacement(*args, **kw):
        if in_call.value:
            raise AssertionError('Function {name} called reentrantly.'.format(name=func.__qualname__), func)
            
        in_call.value = True
        try:
            return func(*args, **kw)
        finally:
            in_call.value = False

    return replacement




