
import collections
from .signal import Signal
import logging

class ConfTreeProxy(object):
    
    def __init__(self, conf_tree, root):
        self._conf_tree = conf_tree
        self._root = root
        if self._conf_tree is not self:
            self._conf_tree.modified.connect(self._parent_modified)
        
    def __getattr__(self, key):
        if not key or not key[0].isupper():
            raise AttributeError(key)
        try:
            return self._conf_tree.get_property(self._root + (key,))
        except KeyError:
            return ConfTreeProxy(self._conf_tree, self._root + (key,))
    
    def __setattr__(self, key, val):
        if not key or not key[0].isupper():
            object.__setattr__(self, key, val)
        else:
            self._conf_tree.set_property(self._root + (key,), val)
            
    def update(self, **kw):
        for k, v in kw.items():
            self.__setattr__(k, v)
            
    def get(self, key, default=None, ty=None):
        if not key or not key[0].isupper():
            raise KeyError('invalid key')
            
        result = getattr(self, key)
        
        if isinstance(result, ConfTreeProxy):
            result = default
        
        if ty is not None and not isinstance(result, ty):
            try:
                result = ty(result)
            except:
                logging.exception('Failed to convert value %r for setting %r to the type %r.',
                    result,
                    '.'.join(self._root + (key,)),
                    ty.__name__
                )
                result = default
        
        return result
    
    def _parent_modified(self, key, value):
        if len(key) >= len(self._root) and key[:len(self._root)] == self._root:
            self.modified(key, value)
 
    @Signal
    def modified(self, key, value):
        pass
    
class ConfTree(ConfTreeProxy):
    '''
    Chained mapping/namespace type for storing configuration. Keys must begin with capital
    letters.
    
    >>> root = ConfTree()
    >>> root.Cpp.ClangFlags = '-std=c++11 -stdlib=libc++'
    >>> root.Cpp.ClangFlags
    '-std=c++11 -stdlib=libc++'
    >>> child = root.inherit()
    >>> child.Cpp.ClangFlags
    '-std=c++11 -stdlib=libc++'
    >>> root.Cpp.ClangFlags += ' -Wall'
    >>> root.Cpp.ClangFlags
    '-std=c++11 -stdlib=libc++ -Wall'
    >>> child.Cpp.ClangFlags
    '-std=c++11 -stdlib=libc++ -Wall'
    >>> child.Cpp.ClangFlags += ' -Werror'
    >>> child.Cpp.ClangFlags
    '-std=c++11 -stdlib=libc++ -Wall -Werror'
    >>> root.Cpp.ClangFlags
    '-std=c++11 -stdlib=libc++ -Wall'
    '''
    # Inherits from ConfTreeProxy to share implementation of __getattr__ and __setattr__.
    
    def __init__(self, *, _backing_store=None):
        super().__init__(self, ()) 
        if _backing_store is None:
            _backing_store = collections.ChainMap()
        
        self._backing_store = _backing_store

    def _on_parent_modified(self, key, value):
        # don't emit signal if the key has been overriden
        if self.get(key) is value:
            self.modified(key, value)
    
    def items(self):
        return self._backing_store.items()
        
    def inherit(self):
        bs = self._backing_store.new_child()
        result = ConfTree(_backing_store=bs)
        self.modified.connect(result._on_parent_modified)

    @staticmethod
    def path_components(path):
        if isinstance(path, str):
            return tuple(path.split('.'))
        else:
            return path
        
    def set_property(self, path, value):
        components = self.path_components(path)
        self._backing_store[components] = value
        self.modified(components, value)
    
    def get_property(self, path):
        return self._backing_store[self.path_components(path)]
    
    def del_property(self, path):
        del self._backing_store[self.path_components(path)]
