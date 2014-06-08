



import bisect
import collections.abc

class ListDict(collections.abc.MutableMapping):

    __slots__ = '_keys', '_vals'

    def __init__(self):
        super().__init__()
        self._keys = []
        self._vals = []

    def copy(self):
        result = ListDict()
        result._keys = self._keys.copy()
        result._vals = self._vals.copy()

        return result

    def lower_bound(self, key):
        '''
        Return the index of the first key greater than or equal to `key`.
        '''

        return bisect.bisect_left(self._keys, key)

    def upper_bound(self, key):
        '''
        Return the index of the first key greater than `key`.
        '''

        return bisect.bisect_right(self._keys, key)


    def index(self, key):
        index = self.lower_bound(key)

        if 0 <= index < len(self._keys) and self._keys[index] == key:
            return index
        else:
            raise KeyError(key)

    def erase(self, index):
        del self._keys[index]
        del self._vals[index]
        
    def items(self):
        return zip(self._keys, self._vals)

    def keys(self):
        yield from self._keys

    def values(self):
        yield from self._vals

    def item(self, index):
        return self._keys[index], self._vals[index]

    def key(self, index):
        return self._keys[index]

    def value(self, index):
        return self._vals[index]

    def set_key(self, index, value):
        assert ((index == 0 or self._keys[index - 1] < value) and
                (index + 1 >= len(self) or self._keys[index + 1] > value)), \
               'Setting this key at this index violates the dictionary\'s ordering.'

        self._keys[index] = value

    def __setitem__(self, key, value):
        index = self.lower_bound(key)
        if 0 <= index < len(self._keys) and self._keys[index] == key:
            self._vals[index] = value
        else:
            self._keys.insert(index, key)
            self._vals.insert(index, value)


    def __delitem__(self, key):
        self.erase(self.index(key))

    def __getitem__(self, key):
        return self.value(self.index(key))

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return self.keys()

    def __repr__(self):
        prefix = 'ListDict({'
        suffix = '})'
        content = ', '.join('{!r}: {!r}'.format(k, v) for (k, v) in self.items())
        return prefix + content + suffix



