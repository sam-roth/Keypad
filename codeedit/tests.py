

import unittest


from . import buffer as buffer_


class TestBufferAndCursorWithSingleLine(unittest.TestCase):

    def setUp(self):
        self.buff = buffer_.Buffer.from_text('abcd')

    
    def test_insert_start(self):
        curs = self.buff.cursor(0, 0)
        curs.insert('XYZ')

        assert curs.col == 3
        assert curs.line == 0
        assert self.buff.to_plain_text() == 'XYZabcd'

    def test_insert_end(self):
        curs = self.buff.cursor()
        curs.go_to_end()
        curs.insert('XYZ')

        assert curs.col == 7
        assert curs.line == 0
        assert self.buff.to_plain_text() == 'abcdXYZ'


    def test_insert_middle(self):
        curs = self.buff.cursor(0, 1)
        curs.insert('XYZ')

        assert curs.col == 4
        assert curs.line == 0
        assert self.buff.to_plain_text() == 'aXYZbcd'

    

    def remove_start(self, backwards=False):
        start_curs = self.buff.cursor(0, 0)
        end_curs   = self.buff.cursor(0, 2)

        if backwards:
            end_curs.remove_until(start_curs)
        else:
            start_curs.remove_until(end_curs)

        assert  start_curs.pos == end_curs.pos and \
                start_curs.pos == (0, 0) and \
                self.buff.to_plain_text() == 'cd'
        

    def test_remove_start(self):
        self.remove_start()

    def test_remove_start_backwards(self):
        self.remove_start(backwards=True)


    def test_remove_end(self):
        start_curs = self.buff.cursor(0, 2)
        end_curs   = self.buff.cursor(0, 4)
        
        start_curs.remove_until(end_curs)

        assert (start_curs.pos == end_curs.pos and
                start_curs.pos == (0, 2) and 
                self.buff.to_plain_text() == 'ab')
                
        

    def test_remove_all(self):
        start_curs = self.buff.cursor(0, 0)
        end_curs   = self.buff.cursor(0, 4)
        
        start_curs.remove_until(end_curs)
        
        assert (start_curs.pos == end_curs.pos and
                start_curs.pos == (0, 0) and
                self.buff.to_plain_text() == '')


    def test_backspace_start(self):
        curs = self.buff.cursor(0, 0)
        curs.backspace()
        assert curs.pos == (0, 0) and self.buff.to_plain_text() == 'abcd'


    def test_advance_forward(self):
        curs = self.buff.cursor(0, 0)
        curs.advance(2)
        assert curs.pos == (0, 2)

    def test_advance_backward(self):
        curs = self.buff.cursor(0, 4)
        curs.advance(-3)
        assert curs.pos == (0, 1)

    def test_advance_over_start(self):
        curs = self.buff.cursor(0, 4)
        curs.advance(-1000)
        assert curs.pos == (0, 0)

    def test_advance_over_end(self):
        curs = self.buff.cursor(0, 0)
        curs.advance(1000)
        assert curs.pos == (0, 4)

class TestBufferAndCursorWithTwoLines(unittest.TestCase):

    def setUp(self):
        self.buff = buffer_.Buffer.from_text('abcd\nefgh')
 

    def test_advance_backwards_over_start_of_line2(self):
        curs = self.buff.cursor(1, 0)
        curs.advance(-1)
        assert curs.pos == (0, 4)
    
    def test_backspace_line2(self):
        curs = self.buff.cursor(1, 0)
        curs.backspace()
        assert self.buff.to_plain_text() == 'abcdefgh'

    
    def test_backspace_line2_more(self):
        curs = self.buff.cursor(1, 2)
        for _ in range(4):
            curs.backspace()
        assert self.buff.to_plain_text() == 'abcgh'


