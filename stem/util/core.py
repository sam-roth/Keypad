

import collections
import inspect
import functools
import warnings
import time
import logging
import operator

_sentinel = object()

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

def time_limited(iterable, *, s=0, ms=0):
    '''
    Return an iterator over the given iterable that stops
    after the given time limit.
    '''
    end = time.time() + s + ms/1000.0
    for element in iterable:
        yield element
        if time.time() >= end:
            break


def deprecated(func):
    already_warned = [False]
    @functools.wraps(func)
    def result(*args, **kw):
        if not already_warned[0]:
            warnings.warn(DeprecationWarning(func), stacklevel=2)
            already_warned[0] = True
        return func(*args, **kw)
    return result

class FatalError(BaseException):
    pass


trace_logger = logging.getLogger('trace')
trace_logger.setLevel(logging.DEBUG)
_trace_indent = 0

def format_args(boundargs):
    '''
    Format the bound arguments object as Python code.

    :type boundargs: inspect.BoundArguments
    '''

    kw = ', '.join('{}={!r}'.format(k, v)
                   for (k, v) in boundargs.kwargs.items())
    args = ', '.join(map(repr, boundargs.args))

    if kw and args:
        return args + ', ' + kw
    elif args:
        return args
    elif kw:
        return kw
    else:
        return ''

def trace(func):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args, **kw):
        global _trace_indent
        ind = '  ' * _trace_indent
        name = '{}({})'.format(func.__qualname__, format_args(sig.bind(*args, **kw)))
        trace_logger.debug(ind + 'entering %s', name)
        _trace_indent += 1
        try:
            result = func(*args, **kw)
        except BaseException as exc:
            trace_logger.debug(ind + '  exception %r', exc)
            raise
        else:
            trace_logger.debug(ind + '  returned %r', result)
            return result
        finally:
            _trace_indent -= 1
            trace_logger.debug('exiting %s', name)


    return wrapper

def bifilter(predicate, xs):
    '''
    Like filter, but also returns items for which the predicate was false.
    '''

    trues = []
    falses = []

    for x in xs:
        if predicate(x):
            trues.append(x)
        else:
            falses.append(x)
    return trues, falses

def setattr_dotted(obj, key, val, *, setattr=setattr, getattr=getattr):
    *head, last = key.split('.')
    for subkey in head:
        obj = getattr(obj, subkey)
    setattr(obj, last, val)

def getattr_dotted(obj, key, default=_sentinel, *, getattr=getattr):
    try:
        for subkey in key.split('.'):
            obj = getattr(obj, subkey)
    except AttributeError:
        if default is _sentinel:
            raise
        else:
            return default
    else:
        return obj

def dotted_pairs_to_dict(pairs):
    result = collections.defaultdict(dict)

    for k, v in pairs:
        setattr_dotted(result, k, v,
                       setattr=operator.setitem,
                       getattr=operator.getitem)
    return dict(result)



