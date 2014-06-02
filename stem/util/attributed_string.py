

from .attributes import Attributes

class AttributedString:

    def __init__(self, text='', **attrs):
        self._text = text
        self._attrs = Attributes()

        self.caches = {}

        self._attrs.set_attributes(0, len(text), **attrs)

    def invalidate(self):
        self.caches.clear()

    def copy(self):
        result = AttributedString(self._text)
        result._attrs = self._attrs.copy()
        return result

    def clone(self):
        return self.copy()

    def __len__(self):
        return len(self._text)

    def __delitem__(self, index):
        if isinstance(index, slice):
            start, stop, stride = index.indices(len(self))
            left = self._text[:start]
            right = self._text[stop:]

            self._text = left + right
            self._attrs.splice(start, start - stop)
            self.invalidate()
        else:
            raise TypeError


    def __getitem__(self, index):
        if isinstance(index, slice):
            result = self.copy()
            start, stop, stride = index.indices(len(self))
            del result[stop:]
            del result[:start]

            return result
        else:
            return self._text[index]

    @property
    def text(self):
        return self._text


    def insert(self, index, text):
        if index is None:
            index = len(self._text)

        if isinstance(text, AttributedString):
            string = text.text
        else:
            string = text

        left = self._text[:index]
        right = self._text[index:]
        self._text = left + string + right

        insert_end = index + len(string)

        self._attrs.splice(index, len(text))

        if isinstance(text, AttributedString):
            for start, end, deltas in text._attrs.iterchunks():
                self._attrs.set_attributes(start + index, insert_end, **deltas)

        self.invalidate()


    def remove(self, start, stop):
        del self[start:stop]

    def append(self, text):
        self.insert(None, text)

    def iterchunks(self):
        for start, end, deltas in self._attrs.iterchunks():
            if start != len(self._text):
                yield self.text[start:end], deltas


    def set_attributes(self, start=0, end=None, **attrs):
        if end is None:
            end = len(self)
        self._attrs.set_attributes(start, end, **attrs)
        self.invalidate()

    def attributes(self, index):
        for key, attr in self._attrs.items():
            yield key, attr[index]

            