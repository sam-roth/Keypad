

from collections import defaultdict

def identity(x): return x

def bound(coll, value, compare, key=identity):
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
    'Find the first element in `coll` greater than or equal to `value`.'
    return bound(coll, value, compare=lambda x, y: x < y, key=key)
    
def upper_bound(coll, value, key=identity):
    'Find the first element in `coll` greater than `value`.'
    return bound(coll, value, compare=lambda x, y: y >= x, key=key)
    

class RangeDict(object):
    def __init__(self, length=0):
        self._data = []
        self._length = length

    @property 
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        if value < self.length:
            del self._data[value:]
        self._length = value

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
        if delta < 0:
            self._set(slice(index, index-delta), None, delonly=True)
            
        for i, (k, v) in enumerate(self._data):
            if k >= index:
                self._data[i] = k + delta, v
            
        self.length += delta

    def __repr__(self):
        return repr(self._data)

class AttributedString(object):
    def __init__(self, text):
        self._text = text
        self._attributes = defaultdict(RangeDict)
        self.caches = {}

    def invalidate(self):
        self.caches = {}
    
    def set_attribute(self, begin, end, key, value):
        self.invalidate()
        attr = self._attributes[key]
        if attr.length != len(self._text):
            attr.length = len(self._text)
        attr[begin:end] = value

    def attributes(self, index):
        for key, attr in self._attributes.items():
            yield key, attr[index]

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
        return self._text

    @text.setter
    def text(self, value):
        self.invalidate()
        self._text = value
        self._attributes.clear()

    def insert(self, index, text):
        self.invalidate()
        left = self._text[:index]
        right = self._text[index:]
        self._text = left + text + right

        text_len = len(text)
        for attr in self._attributes.values():
            attr.splice(index, text_len)


    

ansi_codes = {
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
            yield '\x1b[3{}m'.format(ansi_codes[color])
        yield ch

    yield '\x1b[0m'

def chunk_ansi_color(astr):
    unchanged = object()
    def gen():
        yield '\x1b[0m'
        
        for s, delta in astr.iterchunks():
            color = delta.get('color', unchanged)
            if color is None:
                yield '\x1b[0m'
            elif color is not unchanged:
                yield '\x1b[3{}m'.format(ansi_codes[color])
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
    attrstring_test()
