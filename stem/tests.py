

import unittest

from .buffers import Buffer, Span, Region, Cursor
from .core import write_atomically 


buff_text = '''\
12
34
56
'''


class TestBuffer(unittest.TestCase):

    def setUp(self):
        self.buff = Buffer()
        self.buff.insert((0,0), buff_text)

    def test_content_correct(self):
        assert self.buff.text == buff_text

    def test_insert(self):
        self.buff.insert((0,1), 'ab\ncd')

        assert self.buff.text == '1ab\ncd2\n34\n56\n'

    def test_insert2(self):
        self.buff.insert((0,1), 'ab\ncd\n')

        assert self.buff.text == '1ab\ncd\n2\n34\n56\n'

    def test_insert_empty(self):
        self.buff.insert((0,0), '')
        assert self.buff.text == buff_text

    def test_insert_newline(self):
        self.buff.insert((0,0), '\n')
        
        assert self.buff.text == '\n12\n34\n56\n'
        


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


import random
import string
import tempfile
import logging
import os


class TestAtomicWrites(unittest.TestCase):
    def setUp(self):
        self.prng = prng = random.Random(1234)

        def random_printable():
            return ''.join(
                prng.choice(string.printable)
                for _ in range(1024)
            )

        self.corpus1 = random_printable()
        self.corpus2 = random_printable()

        fd, self.filename = tempfile.mkstemp(text=False)

        enc = self.corpus1.encode()
        with open(fd, 'wb') as f:
            f.write(enc)

        print('write to file %r' % self.filename)
        self.check_file(self.filename, enc)


    def tearDown(self):
        os.unlink(self.filename)
        
               
    def check_file(self, path, text):
        with open(path, 'rb') as f:
            assert f.read() == text
    

    def test_atomic_write(self):

        with write_atomically(self.filename) as f:
            f.write(self.corpus2.encode())

        self.check_file(self.filename, self.corpus2.encode())



if __name__ == '__main__':
    unittest.main()
