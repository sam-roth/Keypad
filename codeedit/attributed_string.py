

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
    def __init__(self, length):
        self._data = []
        self.length  = length


    def __getitem__(self, key):
        idx = upper_bound(self._data, (key, None), key=lambda x: x[0]) - 1
        if idx >= 0 and idx < len(self._data):
            return self._data[idx][1]
        else:
            return None


    def __delitem__(self, key):
        self.__setitem__(key, None)
        
    
    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop, step = key.indices(self.length)
            assert step == 1

            endcap = self[stop]

            lo = lower_bound(self._data, (start, None), key=lambda x: x[0])
            hi = lower_bound(self._data, (stop, None), key=lambda x: x[0])

            
            if not (hi < len(self._data) and self._data[hi][0] == stop):
                self._data.insert(hi, (stop, endcap))

            del self._data[lo:hi]

            self._data.insert(lo, (start, value))
        else:
            self[key:key+1] = value



def main():

    def dump(d):
        print(''.join(d[i] or '_' for i in range(10)))
            

    rd = RangeDict(10)
    rd._data = [(0, 'a'), (5, 'b'), (7, 'c'), (9, 'd')]

    dump(rd)

    del rd[:9]

    dump(rd)

    rd[0] = 'a'

    dump(rd)

    rd[1:9] = 'a'
    dump(rd)

    print(rd._data)

if __name__ == '__main__':
    main()
