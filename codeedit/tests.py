

import unittest

from .buffers import Buffer, Span, Region, Cursor


buff_text = '''\
12
34
56
'''



class TestSpan(unittest.TestCase):

    def setUp(self):
        self.buff = Buffer()

        self.buff.insert((0,0), buff_text)
        b = self.buff

        self.line0 = Span(Cursor(b).move(0,0), Cursor(b).move(0,0).end())
        self.line2 = Span(Cursor(b).move(2,0), Cursor(b).move(2,0).end())

        self.span15 = Span(Cursor(b).move(0,0), Cursor(b).move(2, 0))
        self.span16 = Span(Cursor(b).move(0,0), Cursor(b).move(2,1))
        self.line1 = Span(Cursor(b).move(1,0), Cursor(b).move(1,0).end())


        
    def test_subtract_nonoverlap(self):

        result = self.line0 - self.line2
        assert result == self.line0.region

    
    def test_span16(self):
        assert self.span16.start_curs.text_to(self.span16.end_curs) == '12\n34\n5'
    

    def test_span1E(self):
        assert self.span15.start_curs.text_to(self.span15.end_curs) == '12\n34\n'

    def test_subtract_overlapping(self):
        span = (self.span16 - self.line2)
        assert span.text == self.span15.text

    
    def test_inverse_subtract_overlapping(self):
        span = (self.line2 - self.span16)
        assert span.text == '6'

    def test_inverse_subtract_contained(self):
        span = self.line1 - self.span16
        assert span.text == ''
        

    def test_subtract_null(self):

        span = self.line0 - Region()
        assert span.text == '12'

    def test_subtract_from_null(self):
        span = Region() - self.line0
        assert span.text == ''


if __name__ == '__main__':
    unittest.main()
