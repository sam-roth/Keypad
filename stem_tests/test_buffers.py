

import unittest

from stem.buffers import Buffer, Span, Region, Cursor, TextModification, BufferHistory
from stem.core import write_atomically, errors


import random

buff_text = '''\
12
34
56
'''

def make_random_change(prng, buff):
    '''
    Return a random valid TextModification for the buffer. Does not execute it.

    :type prng: random.Random
    :type buff: stem.buffers.Buffer
    '''

    buflen = len(buff.text)

    start_idx = prng.randrange(buflen)
    start_pos = buff.calculate_pos((0,0), start_idx)

    if prng.randrange(2):
        return TextModification(pos=start_pos, 
                                insert=random_printable(prng))
    else:
        end_idx = prng.randrange(start_idx, buflen)
        rm_len = end_idx - start_idx

        return TextModification(pos=start_pos,
                                remove=buff.span_text(start_pos,
                                                      offset=rm_len))


class TestBufferHistory(unittest.TestCase):

    def setUp(self):
        self.buffer = Buffer()
        self.buffer.insert((0,0), buff_text)
        self.history = BufferHistory(self.buffer)
        self.prng = random.Random(1234)
        
    def test_simple_undo(self):
        for i in range(1000):
            orig_text = self.buffer.text
            #print('orig text:', orig_text)
            rchg = make_random_change(self.prng, self.buffer)
            with self.history.transaction():
                #print('rchg:', rchg)
                self.buffer.execute(rchg)
            new_text = self.buffer.text
            
            #print('new text:', new_text)
            
            if rchg.insert or rchg.remove:
                self.history.undo()
            else:
                try:
                    self.history.undo()
                except errors.CantUndoError:
                    pass
                else:
                    assert False, "shouldn't be able to undo that"
            
            assert self.buffer.text == orig_text
        
    def test_complex_undo_redo(self):
        orig_state = self.buffer.text
        for i in range(100):
            with self.history.transaction():                    
                rchg = make_random_change(self.prng, self.buffer)
                self.buffer.execute(rchg)
        new_state = self.buffer.text

        try:
            while True: self.history.undo()
        except errors.CantUndoError:
            pass

        assert self.buffer.text == orig_state

        try:
            while True: self.history.redo()
        except errors.CantRedoError:
            pass

        assert self.buffer.text == new_state            
        

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

def random_printable(prng):
    return ''.join(
        prng.choice(string.printable)
        for _ in range(1024)
    )
class TestAtomicWrites(unittest.TestCase):
    def setUp(self):
        self.prng = prng = random.Random(1234)



        self.corpus1 = random_printable(prng)
        self.corpus2 = random_printable(prng)

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


def test_walk():
    buff = Buffer()
    buff.insert((0,0), 'hello\nworld')
    
    curs = Cursor(buff).move(0,0)
    chs = []
    for ch in curs.walk(1):
        chs.append(ch)
        print(ch)
    assert ''.join(chs) == 'hello\nworld'

if __name__ == '__main__':
    unittest.main()
