

from stem.core.attributed_string import RangeDict
import bisect

class LinearInterpolator:
    '''
    Note: data must be provided in sorted order.
    Queries may only be made between two given data points.
    >>> f = LinearInterpolator([(0, 0), (100, 100)])
    >>> f(0)
    0.0
    >>> f(1)
    1.0
    >>> f(40)
    40.0
    >>> f(100)
    Traceback (most recent call last):
      File "<ipython-input-52-d39afe9c2d70>", line 1, in <module>
        f(100)
      File "./stem/util/coordmap.py", line 27, in __call__
        'or beyond smallest index %s' % (lv, sv))
    ValueError: cannot extrapolate beyond largest index 100 or beyond smallest index 0
    
    >>> f = LinearInterpolator([(0, 0), (100, 100), (200, 110)])
    >>> f(2)
    2.0
    >>> f(102)
    100.2
    >>> f(100)
    100.0
    >>> f(199)
    109.9
    >>> f(1999999)
    Traceback (most recent call last):
      File "<ipython-input-58-ecc986fc17c3>", line 1, in <module>
        f(1999999)
      File "./stem/util/coordmap.py", line 27, in __call__
        'or beyond smallest index %s' % (lv, sv))
    ValueError: cannot extrapolate beyond largest index 200 or beyond smallest index 0
    
    >>> f(199.9999)
    109.99999
    >>> f(200)
    Traceback (most recent call last):
      File "<ipython-input-60-e293f9041bfb>", line 1, in <module>
        f(200)
      File "./stem/util/coordmap.py", line 27, in __call__
        'or beyond smallest index %s' % (lv, sv))
    ValueError: cannot extrapolate beyond largest index 200 or beyond smallest index 0
    '''
    __slots__ = 'indices', 'values'
    def __init__(self, data):
        self.indices = tuple(i for (i, _) in data)
        self.values = tuple(x for (_, x) in data)

    def __call__(self, index, saturate=False):
        value_index = bisect.bisect(self.indices, index) - 1
        if not (0 <= value_index < len(self.indices) - 1):
            if not saturate:
                if self.values:
                    lv = self.indices[-1]
                    sv = self.indices[0]
                else:
                    lv = '<empty>'
                    sv = '<empty>'
    
                raise ValueError('cannot extrapolate beyond largest index %s '
                                 'or beyond smallest index %s' % (lv, sv))
            else:
                if not self.values:
                    raise ValueError('interpolator is empty')
                if value_index >= len(self.indices) - 1:
                    return self.values[-1]
                elif value_index < 0:
                    return self.values[0]


        x1 = self.indices[value_index + 1]
        x0 = self.indices[value_index]

        y1 = self.values[value_index + 1]
        y0 = self.values[value_index]


        frac = (index - x0) / (x1 - x0)

        return (y1 - y0) * frac + y0



class TextCoordMapper:

    def __init__(self):
        self.__lines = RangeDict(1)

    def __line(self, x, y, width, height):
        if self.__lines.length <= y + height:
            self.__lines.length = y + height + 10
        l = self.__lines[y]
        if l is None:
            l = RangeDict(x + width+10)
        elif l.length <= x + width:
            l.length = x + width + 10
        self.__lines[y:y+height] = l

        return l

    def map_from_point(self, x, y):
        l = self.__lines[y]
        if l is not None:
            si = l.span_info(x)
            if si is None:
                return None
            else:
                start, end, datum = si
                if datum is None:
                    return None
                else:
                    line_id, offset, char_width = datum
                    return line_id, offset + int((x - start) / char_width)
        else:
            return None

    def clear(self, first=0, last=None):
        del self.__lines[int(first):int(last)]

    def put_region(self, 
                   *,
                   x, y,
                   char_width,
                   char_count,
                   line_spacing,
                   line_id,
                   offset=0):

        width = char_width * char_count
        height = line_spacing

        datum = line_id, offset, char_width

        l = self.__line(int(x), int(y), int(width), int(height))

        l[int(x):int(x+width)] = datum



    def dump(self):
        print(self.__lines)
