
import abc
import collections.abc

def keysplit(k):
    if isinstance(k, str):
        return tuple(k.split('.'))
    else:
        return k

_sentinel = object()
def most_specific(d, key, keysplit=keysplit, default=_sentinel):
    ks = keysplit(key)
    for i in range(len(ks)):
        subkey = ks[:len(ks) - i]
        result = d.get(subkey, _sentinel)
        if result is not _sentinel:
            return result
    else:
        if default is _sentinel:
            raise KeyError(key)
        else:
            return default

def splitkeys(d, keysplit=keysplit):
    return {keysplit(k): v for (k, v) in d.items()}



class AbstractScopeDict(collections.abc.MutableMapping, 
                        metaclass=abc.ABCMeta):

    @classmethod
    @abc.abstractmethod
    def make_key(cls, key):
        pass

    @classmethod
    @abc.abstractmethod
    def parents(cls, key):
        pass

    def __init__(self, *args, **kw):
        super().__init__()
        self._data = {}
        self.update(*args, **kw)

    def __getitem__(self, key):
        sentinel = object()

        for parent in self.parents(self.make_key(key)):
            result = self._data.get(parent, sentinel)
            if result is not sentinel:
                return result
        else:
            raise KeyError(key)


    def __setitem__(self, key, value):
        self._data[self.make_key(key)] = value

    def __delitem__(self, key):
        del self._data[self.make_key(key)]


    def __iter__(self):
        yield from self._data

    def __len__(self):
        return len(self._data)

class ScopeDict(AbstractScopeDict):
    '''
    Dictionary with a notion of key inheritance.


    >>> sd = ScopeDict()
    >>> sd['comment.block.preprocessor']
    Traceback (most recent call last):
    KeyError: 'comment.block.preprocessor'

    >>> sd['comment'] = 'gray'
    >>> sd['comment.block.preprocessor']
    'gray'
    >>> sd['comment.block.preprocessor'] = 'green'
    >>> sd['comment.block.preprocessor']
    'green'
    >>> sd['comment.block']
    'gray'
    >>> sd['comment.sarcastic']
    'gray'
    >>> sd['comment']
    'gray'
    >>> sd['']
    Traceback (most recent call last):
    KeyError: ''
    '''
    @classmethod
    def make_key(cls, key):
        if isinstance(key, tuple):
            return key
        elif isinstance(key, str):
            return tuple(key.split('.'))
        else:
            raise TypeError('expected tuple or str for key, not %s' % type(key).__name__)
            
    @classmethod
    def parents(cls, key):
        for i in range(len(key), -1, -1):
            yield key[:i]




