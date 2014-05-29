

from stem.core.attributed_string import RangeDict


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
