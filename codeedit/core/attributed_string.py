import logging

from collections import defaultdict

def identity(x): return x

def bound(coll, value, compare, key=identity):
    '''
    See `lower_bound` and `upper_bound`.

    Credit: Based on the implementations of the functions of the same names from
    http://en.cppreference.com/w/cpp/algorithm/lower_bound.
    '''
    first = 0
    count = len(coll)

    value_key = key(value)

    while count > 0:
        i = first
        step = count // 2
        i += step

        if compare(key(coll[i]), value_key):
            i += 1
            first = i
            count -= step + 1
        else:
            count = step

    return first


def lower_bound(coll, value, key=identity):
    '''
    Find the index of the first element in `coll` equal to or greater than
    `value`. 
    
    The collection must be partitioned with respect to `_ < value`.
    (Sorting it will suffice for this requirement.)

    Complexity: ``O(log(len(coll)))``.
    
    >>> lower_bound(list(range(10)), 5)
    5
    >>> lower_bound([1,2,9,10], 5)
    2
    '''
    return bound(coll, value, compare=lambda x, y: x < y, key=key)
    
def upper_bound(coll, value, key=identity):
    '''
    Find the index of the first element in `coll` greater than `value`.

    The collection must be partitioned with respect to `_ >= value`.
    (Sorting it will suffice for this requirement.)

    Complexity: ``O(log(len(coll)))``.

    >>> upper_bound(list(range(10)), 5)
    6
    >>> upper_bound([1,2,9,10], 5)
    2
    '''
    return bound(coll, value, compare=lambda x, y: y >= x, key=key)
    
from collections import namedtuple

class RangeDict(object):
    '''
    A mapping from an integer interval to a value.

    Non-standard interface alerts:
        1.  The container does not distinguish between `None` and the absence of
            an item.
        2.  In `self[n:m] = v`, `v` is not a `RangeDict`, but a value instead.
        3.  `self[n:m] = v` is valid, but `v = self[n:m]` is invalid (and
            meaningless). Use `v = self[n]` instead.

    >>> d = RangeDict(length=10)
    >>> d[0:3] = 1
    >>> d[3:]  = 2
    >>> d[0]
    1
    >>> [d[n] for n in range(10)]
    [1, 1, 1, 2, 2, 2, 2, 2, 2, 2]
    >>> del d[6:]
    >>> [d[n] for n in range(10)]
    [1, 1, 1, 2, 2, 2, None, None, None, None]
    '''

    SpanInfo = namedtuple('SpanInfo', 'start end value')

    def __init__(self, length=0):
        self._data = []
        self._length = length

    @property 
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        '''
        Resize the RangeDict by removing ranges from the end or smearing the last range
        to the new length.

        >>> rd = RangeDict(length=3)
        >>> rd[0:2] = 1
        >>> rd[2:] = 2
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, 2]
        >>> rd.length=10
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, 2, 2, 2, 2, 2, 2, 2, 2]
        >>> rd.length=2
        >>> [rd[n] for n in range(len(rd))]
        [1, 1]
        '''
        if value < self.length:
            del self._data[value:]
        self._length = value

    def __len__(self):
        return self.length

    def span_info(self, idx):
        data_index = upper_bound(self._data, (idx, None), key=lambda x: x[0]) - 1
        if idx >= 0 and idx < len(self._data):
            return RangeDict.SpanInfo(start=self._data[idx][0],
                                      end=self._data[idx+1][0] if idx + 1 < len(self._data) else self.length,
                                      value=self._data[idx][1])

    def __getitem__(self, key):
        idx = upper_bound(self._data, (key, None), key=lambda x: x[0]) - 1
        if idx >= 0 and idx < len(self._data):
            return self._data[idx][1]
        else:
            return None

    def __delitem__(self, key):
        self.__setitem__(key, None)
    
    def _set(self, key, value, delonly=False):
        if isinstance(key, slice):
            start, stop, step = key.indices(self.length)
            assert step == 1

            endcap = self[stop]

            lo = lower_bound(self._data, (start, None), key=lambda x: x[0])
            hi = lower_bound(self._data, (stop, None), key=lambda x: x[0])

            if ((not (hi < len(self._data) and self._data[hi][0] == stop)) 
                    and stop < self.length 
                    and not delonly):
                self._data.insert(hi, (stop, endcap))

            del self._data[lo:hi]

            if not delonly:
                self._data.insert(lo, (start, value))
        else:
            self[key:key+1] = value

    def __setitem__(self, key, value):
        self._set(key, value)


    def splice(self, index, delta):
        '''
        Change the length of `self` by `delta` elements before the given `index`.

        >>> rd = RangeDict(length=3)
        >>> rd[0:2] = 1
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, None]
        >>> rd[3:] = 2
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, None]
        >>> rd[2:] = 2
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, 2]
        >>> rd.splice(2, 4)
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, 1, 1, 1, 1, 2]
        >>> rd.splice(2, -4)
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, 2]
        >>> rd.splice(3, 4)
        >>> [rd[n] for n in range(len(rd))]
        [1, 1, 2, 2, 2, 2, 2]
        '''
        if delta < 0:
            self._set(slice(index, index-delta), None, delonly=True)
            
        for i, (k, v) in enumerate(self._data):
            if k >= index:
                self._data[i] = k + delta, v
            
        self.length += delta

    def __repr__(self):
        return repr(self._data)

class AttributedString(object):
    '''
    A mutable string-like datatype that stores a string and a parallel mapping
    of an attribute ID to a mapping of ranges of indices (automatically
    updated) to a value for the attribute over that range.

    These objects also contain a dictionary for caching derived data (such as
    rendered pixmaps of the string). The dictionary is automatically cleared
    upon modifying the string.

    Beware: String mutation operations are potentially expensive, as the
    underlying string implementation is immutable; however, they are less
    expensive than constructing an entirely new AttributedString for all
    operations.

    Note: The dicts in the __repr__ shown only include changes between each
    chunk.

    >>> astr = AttributedString('Hello, world!', italic=True)
    >>> astr
    AttributedString(('Hello, world!', {'italic': True}))
    >>> astr.set_attribute(-6, None, 'italic', False)
    >>> astr
    AttributedString(('Hello, ', {'italic': True}), ('world!', {'italic': False}))
    >>> astr.set_attribute(-6, -1, 'color', 'blue')
    >>> astr
    AttributedString(('Hello, ', {'italic': True}), ('world', {'italic': False, 'color': 'blue'}), ('!', {'color': None}))



    '''

    def __init__(self, text='', **attrs):
        '''
        Construct an AttributedString with the given text and attributes. The
        attributes cover the entire length of the string.
        '''
        self._text = text
        self._attributes = defaultdict(RangeDict)
        self.caches = {}

        for attr, val in attrs.items():
            self.set_attribute(attr, val)

    def __len__(self):
        return len(self._text)

    def invalidate(self):
        self.caches = {}
    
    def set_attribute_range(self, begin, end, key, value):
        attr = self._attributes[key]
        span_info = attr.span_info(begin)
        
        numeric_end = end if end is not None else len(self)
        if span_info is None or attr.length != len(self._text) or \
                (span_info.start, span_info.end, span_info.value) != (begin, numeric_end, value):
            self.invalidate()
            if attr.length != len(self._text):
                attr.length = len(self._text)
            attr[begin:end] = value


    def set_attribute(self, *args, **kw):
        '''
        set_attribute(begin=0, end=None, key, value)

        Set the attribute `key` to `value` starting at `begin` and ending
        before `end`. If `end` is `None`, set the attribute to the end of
        the string.
        '''
        try:
            def signature1(begin, end, key, value):
                pass
            signature1(*args, **kw)
        except TypeError:
            def signature2(key, value):
                return key, value
            key, value = signature2(*args, **kw)
            self.set_attribute_range(0, None, key, value)
        else:
            self.set_attribute_range(*args, **kw)


    def attributes(self, index):
        for key, attr in self._attributes.items():
            yield key, attr[index]


    @property
    def keys(self):
        return self._attributes.keys()

    def iterchars(self):
        # TODO make this more efficient
        for idx, ch in enumerate(self._text):
            yield ch, self.attributes(idx)


    def find_deltas(self):
        deltas = defaultdict(dict)
        for key, attr in self._attributes.items():
            for idx, value in attr._data:
                deltas[idx][key] = value
        
        return deltas

    def iterchunks(self):
        '''
        Return an iterator over the "chunks" (regions without attribute
        changes) in the string. 

        Each yielded value is a pair containing the text in the chunk and any
        changed attributes as a dictionary since the last chunk. If the
        attributes were not changed since the last chunk, the changed
        attributes dictionary will be empty.
        '''
        last_idx = 0
        last_attrs = {}
        for delta_idx, delta_attrs in sorted(self.find_deltas().items(), key=lambda x: x[0]):
            if last_idx != delta_idx:
                yield self.text[last_idx:delta_idx], last_attrs
            last_attrs, last_idx = delta_attrs, delta_idx
        
        if last_idx < len(self.text):
            yield self.text[last_idx:], last_attrs
            
    @property
    def text(self):
        '''
        The unformatted text as a string.
        '''
        return self._text


    def insert(self, index, text):
        '''
        Insert text before the index specified.

        :type text: AttributedString or str
        '''

        if isinstance(text, AttributedString):
            astr = text
            text = astr.text
            assert not isinstance(text, AttributedString)
        else:
            astr = None


        self.invalidate()
        left = self._text[:index]
        right = self._text[index:] if index is not None else ''
        self._text = left + text + right

        text_len = len(text)
        if index is not None:
            for attr in self._attributes.values():
                attr.splice(index, text_len)
        else:
            for attr in self._attributes.values():
                attr.length = len(self._text)


        if astr is not None:
            offset = index

            if offset is None:
                offset = len(self._text) - len(text)
            elif offset < 0:
                offset += len(self._text) - len(text)

            for chunk, attrs in astr.iterchunks():
                for attr, value in attrs.items():
                    self.set_attribute(offset, offset + len(chunk), attr, value)
                offset += len(chunk)

    def append(self, text):
        '''
        Insert text at the end of the string.

        :type text: AttributedString or str
        '''
        self.insert(None, text)

                
    
    def remove(self, start, stop):
        '''
        Remove text in ``(start..stop]``.
        '''
        start, stop, _ = slice(start, stop).indices(len(self))

        self.invalidate()
        left = self._text[:start]
        right = self._text[stop:]
        self._text = left + right
        
        text_len = stop - start
        for attr in self._attributes.values():
            attr.splice(start, -text_len)

    
    
    @classmethod
    def join(cls, sep_or_strings, strings=None):
        '''
        join(separator='', strings)
        
        attributed string formed by the concatenation of the elements of the
        second argument, separated by the given separator
               

        >>> s1=AttributedString('Hello,', color='green')
        >>> s2=AttributedString(' world!', color='blue')
        >>> s1, s2
        (AttributedString(('Hello,', {'color': 'green'})), AttributedString((' world!', {'color': 'blue'})))
        >>> AttributedString.join([s1,s2])
        AttributedString(('Hello,', {'color': 'green'}), (' world!', {'color': 'blue'}))
        '''
        if strings is None:
            sep, strings = '', sep_or_strings
        else:
            sep, strings = sep_or_strings, strings

        def text(s):
            if isinstance(s, AttributedString):
                return s.text
            else:
                return s
        
        def gen():
            for i, part in enumerate(strings):
                if i != 0:
                    yield sep
                yield part
        

        parts = list(gen())

        result = AttributedString(''.join(map(text, parts)))
        
        accumulated_len = 0
        for part in parts:
            part_end   = accumulated_len + len(part)

            if isinstance(part, AttributedString):
                for chunk, deltas in part.iterchunks():
                    for key, value in deltas.items():
                        result.set_attribute(
                            accumulated_len,
                            part_end,
                            key,
                            value
                        )
                    accumulated_len += len(chunk)
            else:
                accumulated_len += len(part)


        return result

    def clone(self):
        '''
        Make a copy of the string. It will not change with this string.
        '''
        result = AttributedString()
        result.append(self)
        return result


    def __repr__(self):
        return 'AttributedString(' + ', '.join(map(str, self.iterchunks())) + ')'

    

ansi_escape_codes = {
    'black': 0,
    'red': 1,
    'green': 2,
    'yellow': 3,
    'blue': 4,
    'magenta': 5,
    'cyan': 6,
    'white': 7
}
def ansi_color(astr):
    yield '\x1b[0m'

    for ch, attrs in astr.iterchars():
        attrs = dict(attrs)
        color = attrs.get('color')
        if color is None:
            yield '\x1b[0m'
        else:
            yield '\x1b[3{}m'.format(ansi_escape_codes[color])
        yield ch

    yield '\x1b[0m'

def chunk_ansi_color(astr):
    unchanged = object()
    def gen():
        reset = '\x1b[0m'
        yield reset


        for s, delta in astr.iterchunks():
            color = delta.get('color', unchanged)

            if color is None:
                yield '\x1b[39m'
            elif color is not unchanged:
                yield '\x1b[3{}m'.format(ansi_escape_codes[color])

            underline = delta.get('underline', unchanged)
            if underline is not unchanged:
                if underline:
                    yield '\x1b[4m'
                else:
                    yield '\x1b[24m'
            yield s
        yield '\x1b[0m'

    return ''.join(gen())

def attrstring_test():

    astr = AttributedString('Hello, world!')
    
    astr.set_attribute(0, 4, 'color', 'red')
    astr.set_attribute(7, 12, 'color', 'blue')
    astr.set_attribute(12, 13, 'color', 'yellow')

    print(''.join(ansi_color(astr)))  

    astr.insert(13, '!!')


    print(''.join(ansi_color(astr)))  

    print(list(astr.iterchunks()))
    
    print(chunk_ansi_color(astr))

    astr.append('abcd')
    print(chunk_ansi_color(astr))
    print(list(astr.iterchunks()))

    astr2 = AttributedString('efgh')
    astr2.set_attribute(0, -1, 'color', None)
    astr.append(astr2)

    print(chunk_ansi_color(astr))


def attrstring_test_2():

    def gen():
        for colorname in ansi_escape_codes.keys():
            result = AttributedString(colorname)
            result.set_attribute('color', colorname)
            yield result

    

    print()
    print(chunk_ansi_color(AttributedString.join(AttributedString(', ', color=None), gen())))
    print(chunk_ansi_color(AttributedString.join(
        AttributedString(', ', color=None, underline=False), [
            AttributedString('underlined', underline=True),
            AttributedString('not underlined', underline=False),
            AttributedString('underlined and red', underline=True, color='red')
    ])))
    print()

def main():

    def dump(d):
        print(''.join(d[i] or '_' for i in range(d.length)))
            

    rd = RangeDict(10)
    rd[ :5]     = 'a'
    rd[5:7]     = 'b'
    rd[7:9]     = 'c'
    rd[9: ]     = 'd'

    #rd._data = [(0, 'a'), (5, 'b'), (7, 'c'), (9, 'd')]
    
    dump(rd)

    rd.splice(8, 4)

    dump(rd)
    print('a', rd._data)

    rd.splice(8, -4)

    print('b', rd._data)
    dump(rd)

    

    if False:

        del rd[:9]

        dump(rd)

        rd[0] = 'a'

        dump(rd)

        rd[1:9] = 'a'
        dump(rd)

        rd.length = 20
        dump(rd)


        rd.length = 5
        dump(rd)

    print(rd._data)

if __name__ == '__main__':
    attrstring_test_2()
