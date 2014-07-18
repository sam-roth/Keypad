
import collections


from .rangedict import RangeDict
from .listdict import ListDict
from .core import alphabetical_dict_repr

class Attributes(object):
    __slots__ = '_attrs'

    def __init__(self):
        self._attrs = collections.defaultdict(RangeDict)


    def items(self):
        return self._attrs.items()

    def splice(self, key, delta):
        for attr in self._attrs.values():
            attr.splice(key, delta)

    def find_deltas(self):
        result = ListDict()
        for attrname, attr in self._attrs.items():
            for key, value in attr.items():
                items = result.setdefault(key, [])
                items.append((attrname, value))
        return result

    def iterchunks(self):
        last_key = 0
        last_attrs = {}
        for key, attrs in self.find_deltas().items():
            if last_key != key:
                yield last_key, key, last_attrs
            last_attrs, last_key = dict(attrs), key

        yield last_key, None, last_attrs

    def set_attributes(self, begin=0, end=None, **kw):
        invalidated = False
        for k, v in kw.items():
            attr = self._attrs[k]
            span_info = attr.span_info(begin)

            numeric_end = end if end is not None else len(attr)

            needs_update = ((span_info.start, span_info.end, span_info.value) !=
                            (begin, numeric_end, v))

            if needs_update:
                invalidated = True
                attr[begin:end] = v
        return invalidated

    def __repr__(self):
        return alphabetical_dict_repr(self._attrs)

    def copy(self):
        result = Attributes()
        for k, v in self._attrs.items():
            result._attrs[k] = v.copy()
        return result

