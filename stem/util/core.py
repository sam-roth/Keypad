

import collections
import inspect
import functools
import warnings



class ImmutableListView(collections.Sequence):
    def __init__(self, list_):
        self._list =  list_

    def __len__(self):
        return len(self._list)

    def __getitem__(self, i):
        return self._list[i]

def singleton(cls):
    return cls()

def dump_object(obj):
    header = type(obj).__name__ + "{\n    "
     
    body = ',\n    '.join('{:<10}{!r}'.format(name + ':', value) 
                          for (name, value) in vars(obj).items()
                          if not (name.startswith('__') and name.endswith('__')))

    end = '\n}'

    return header + body + end


def alphabetical_dict_repr(dictionary):
    return '{' + ', '.join(
        '{!r}: {!r}'.format(k, v) 
        for (k, v) in sorted(dictionary.items(), key=lambda x: x[0])) + '}'


def clamp(lo, hi, val):
    if val < lo:
        return lo
    elif val >= hi:
        return hi - 1
    else:
        return val


def default(x, y):
    if x is None:
        return y
    else:
        return x



def deprecated(func):
    already_warned = [False]
    @functools.wraps(func)
    def result(*args, **kw):
        if not already_warned[0]:
            warnings.warn(DeprecationWarning(func), stacklevel=3)
            already_warned[0] = True
        return func(*args, **kw)
    return result

class FatalError(BaseException):
    pass
