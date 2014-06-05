
import itertools
import collections

from .listdict import ListDict

SpanInfo = collections.namedtuple('SpanInfo', 'start end value')

class RangeDict(collections.MutableMapping):
    '''
    Provides a mapping of an interval of integers to a value.

    Insert complexity: O(len(self)) worst-case

    Query complexity: O(log(len(self))) worst-case

    .. todo::
        
       No check is performed that would ensure that inserting at the end is O(1)
       amortized. This ought to be possible.

    >>> rd = RangeDict()
    >>> rd[0:4] = 1
    >>> rd
    RangeDict({0: 1, 4: None})
    >>> rd[0], rd[1]
    (1, 1)
    >>> rd[4] is None
    True
    >>> rd[5:6] = 2
    >>> rd
    RangeDict({0: 1, 4: None, 5: 2, 6: None})
    >>> rd[7] = 3 # only slice assignment is supported
    Traceback (most recent call last):
        ...
    TypeError
    '''
    __slots__ = '_data',

    def __init__(self):
        self._data = ListDict()


    def copy(self):
        rd = RangeDict()
        rd._data = self._data.copy()
        return rd

    def put_interval(self, lo, hi, value):
        if lo == hi:
            return

        start = self._data.lower_bound(lo)
        end   = self._data.upper_bound(hi)

        if end > 0:
            try:
                prev_value = self._data.value(end - 1)
            except IndexError:
                prev_value = None
        else:
            prev_value = None

        self._data.erase(slice(start, end))

        if hi not in self._data:
            self._data[hi] = prev_value

        self._data[lo] = value

    def del_interval(self, lo, hi):
        if hi is not None:
            self.put_interval(lo, hi, None)
        else:
            self.put_interval(lo, lo+1, None)

        i = self._data.lower_bound(lo)
        ks, vs = self._data.item(slice(i, None))
        self._data.erase(slice(i, None))

        if hi is not None:
            delta = hi - lo    
            for k, v in zip(ks, vs):
                nk = k - delta
                if nk >= lo:
                    self._data[nk] = v

    def splice(self, key, delta):
        '''
        Alter the length of the `RangeDict` by `delta` at `key`.

        >>> rd = RangeDict()

        >>> rd[0:3] = 1
        >>> rd
        RangeDict({0: 1, 3: None})
        >>> rd.splice(2, 10)
        >>> rd
        RangeDict({0: 1, 13: None})
        >>> rd.splice(2, -10)
        >>> rd
        RangeDict({0: 1, 2: 1, 3: None})
        '''
        if delta == 0:
            return
        elif delta < 0:
            self.del_interval(key, key - delta)
        else:
            lb = self._data.lower_bound(key)
            for i in range(len(self._data)-1, lb-1, -1):
                self._data.set_key(i, self._data.key(i) + delta)

                

    def get_inst(self, key):
        index = self._data.upper_bound(key) - 1

        if index >= 0:
            try:
                return self._data.value(index)
            except IndexError:
                return None
        else:
            return None

    def span_info(self, key):
        '''
        Return a `SpanInfo` namedtuple containing the endpoints of the span
        that contains the key, as well as the value assigned to that span.

        >>> rd = RangeDict()
        >>> rd[0:3] = 1
        >>> rd.span_info(2)
        SpanInfo(start=0, end=3, value=1)
        >>> rd.span_info(10000)
        SpanInfo(start=3, end=None, value=None)
        '''
        ub = self._data.upper_bound(key)
        if ub - 1 >= 0:
            try: 
                lo = self._data.key(ub - 1)
                v = self._data.value(ub - 1)
            except IndexError: 
                v = None
                lo = None
        else:
            v = None
            lo = None

        if ub >= 0:
            try:
                hi = self._data.key(ub)
            except IndexError:
                hi = None
        else:
            hi = None

        return SpanInfo(lo, hi, v)

    @property
    def iterrange(self):
        for (k1, v1), (k2, v2) in zip(self._data.items(),
                                      itertools.islice(self._data.items(), 1, None)):
            yield from [v1] * (k2-k1)


    def __repr__(self):
        prefix = 'RangeDict({'
        suffix = '})'

        content = ', '.join('{!r}: {!r}'.format(k, v)
                            for (k, v) in self.items())

        return prefix + content + suffix

    # `dict`-like interface

    def __getitem__(self, key):
        return self.get_inst(key)

    def __setitem__(self, key, value):
        if isinstance(key, slice) and key.step is None:
            self.put_interval(key.start, key.stop, value)
        else:
            raise TypeError

    def __delitem__(self, key):
        if isinstance(key, slice) and key.step is None:
            self.del_interval(key.start, key.stop)
        else:
            raise TypeError

    def keys(self):
        return self._data.keys()

    def values(self, keys=None):
        if keys is None:
            yield from self._data.values()
        else:
            for key in keys:
                yield self[key]

    def items(self):
        return self._data.items()

    def __iter__(self):
        yield from self.keys()

    def __len__(self):
        if not self._data:
            return 0
        else:
            return self._data.value(len(self._data) - 1)

