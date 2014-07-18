
from .cursor import Cursor
from collections import namedtuple
from itertools import zip_longest



class BasicSpan(object):

    Range = namedtuple('Range', 'y line start_x end_x')

    def __init__(self, start_curs): #, end_curs):
        #assert isinstance(start_curs, Cursor)
        #assert isinstance(end_curs, Cursor)
    

        #start_curs = start_curs.clone()
        #end_curs   = end_curs.clone()

        #if end_curs.pos < start_curs.pos:
        #    start_curs, end_curs = end_curs, start_curs

        self.start_curs = start_curs
        #self.end_curs = end_curs

    
    @property
    def buffer(self):
        return self.start_curs.buffer



    def __contains__(self, pos):
        if isinstance(pos, Cursor):
            pos = pos.pos
        
        return self.start_curs.pos <= pos < self.end_curs.pos

    def contains_inclusive(self, pos):
        if isinstance(pos, Cursor):
            pos = pos.pos

        return self.start_curs.pos <= pos <= self.end_curs.pos


    @property
    def ranges(self):
        start_curs, end_curs = self.start_curs, self.end_curs
        start_curs_y, start_curs_x = start_curs.pos
        end_curs_y, end_curs_x = end_curs.pos

        for y, line in enumerate(start_curs.buffer.lines[start_curs_y:end_curs_y+1], start_curs_y):
            start_x = start_curs_x  if y == start_curs_y    else 0
            end_x   = end_curs_x    if y == end_curs_y      else None

            yield self.Range(y, line, start_x, end_x)

    @property
    def region(self):
        return Region(self)


    def set_attributes(self, **kw):
        for key, val in kw.items():
            self.start_curs.set_attribute_to(self.end_curs, key, val)


    def __sub__(self, other):
        return self.region - other.region

    def __repr__(self):
        return 'Span({!r}, {!r})'.format(self.start_curs, self.end_curs)

    def __eq__(self, other):
        return (self.start_curs.pos, self.end_curs.pos) == (other.start_curs.pos, other.end_curs.pos)


    @property
    def text(self):
        return self.start_curs.text_to(self.end_curs)
        
    @text.setter
    def text(self, value):
        self.start_curs.remove_to(self.end_curs)
        p = self.start_curs.pos
        self.start_curs.insert(value)
        self.start_curs.pos = p



    def remove(self):
        self.text = ''
class Span(BasicSpan):
    def __init__(self, start_curs, end_curs):
        assert isinstance(start_curs, Cursor)
        assert isinstance(end_curs, Cursor)

        start_curs = start_curs.clone()
        end_curs   = end_curs.clone()

        if end_curs.pos < start_curs.pos:
            start_curs, end_curs = end_curs, start_curs

        super().__init__(start_curs)
        self.end_curs = end_curs

    @classmethod
    def from_pos(cls, buff, pos, *, length=None, end=None):
        if not ((length is None) ^ (end is None)):
            raise TypeError('Must provide at least one of `length`, `end`.')

        if length is not None:
            c1 = Cursor(buff).move(pos)
            c2 = c1.clone().advance(length)
            return cls(c1, c2)
        else:
            c1 = Cursor(buff).move(pos)
            c2 = c1.clone().move(end)
            return cls(c1, c2)

    def append(self, text):
        self.end_curs.insert(text)

    def prepend(self, text):
        p = self.start_curs.pos
        self.start_curs.insert(text)
        self.start_curs.move(p)

    def clone(self):
        return Span(self.start_curs.clone(),
                    self.end_curs.clone())

    def __getitem__(self, key):
        if not isinstance(key, slice):
            key = slice(key, key + 1)

        start, stop, step = key.indices(len(self.text))

        if step != 1:
            raise TypeError('step is unsupported')

        return Span(self.start_curs.clone().advance(start),
                    self.start_curs.clone().advance(stop))
        

import logging

class Region(object):
    Debug = True

    def __init__(self, *spans):
        self.spans = tuple(sorted(spans, key=lambda span: span.start_curs.pos))

        if self.Debug:
            for span1, span2 in zip(self.spans, self.spans[1:]):
                if span1.end_curs.pos > span2.start_curs.pos:
                    logging.error('spans in regions must be exclusive: %r', self)
                    assert False, 'spans in regions must be exclusive'

    def clone(self):
        return Region(*(s.clone() for s in self.spans))

    def __contains__(self, pos):
        return any(pos in x for x in self.spans)
    

    def contains_inclusive(self, pos):
        return any(x.contains_inclusive(pos) for x in self.spans)


    def __repr__(self):
        return 'Region{!r}'.format(self.spans)

    @property
    def ranges(self):
        for span in self.spans:
            yield from span.ranges

    
    @property
    def region(self):
        return self


    @property
    def buffer(self):
        if self.spans:
            return self.spans[0].buffer
        else:
            return None


    @property
    def text(self):
        return ''.join(span.text for span in self.spans)
    

    def subtract_span(self, other_span):
        def gen():
            for self_span in self.spans:

                start_equal = self_span.start_curs.pos == other_span.start_curs.pos
                end_equal   = self_span.end_curs.pos   == other_span.end_curs.pos

        
                start_contained = self_span.start_curs in other_span
                end_contained = self_span.end_curs in other_span or end_equal

                contained = start_contained and end_contained
                
                if not contained and not (start_equal and end_equal):
                    intersect_head = other_span.start_curs in self_span
                    intersect_tail = other_span.end_curs in self_span or end_equal
                    
                    self_start, self_end = self_span.start_curs, self_span.end_curs
                    other_start, other_end = other_span.start_curs, other_span.end_curs

                    if intersect_head and self_start.pos != other_start.pos:
                        yield Span(self_start, other_start) #self_span.start_curs, other_span.start_curs)
                    if intersect_tail and other_end.pos != self_end.pos:
                        yield Span(other_end, self_end) #other_span.end_curs, self_span.end_curs)
                    
                    if not (intersect_head or intersect_tail):
                        yield self_span

        return Region(*gen())

    def __sub__(self, other):
        other = other.region

        result = self
        while other.spans:
            result = result.subtract_span(other.spans[0])
            other = Region(*other.spans[1:])

        return result

    def set_attributes(self, **kw):
        for span in self.spans:
            span.set_attributes(**kw)
    

    def __eq__(self, other):
        return self.spans == other.spans


    def remove(self):
        for span in self.spans:
            span.remove()

