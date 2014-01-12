
from .new_buffer import TextModification

class Cursor(object):

    def __init__(self, manip):    
        self.manip = manip
        
        # allow either a buffer or a buffer manipulator through duck typing
        self.buffer = getattr(manip, 'buffer', manip)

        self.buffer.text_modified.connect(self._on_buffer_text_modified)

        self.pos = 0, 0

        
    def _on_buffer_text_modified(self, change):
        '''
        :type change: codeedit.new_buffer.TextModification
        '''
        
        self_y, self_x = self.pos
        chg_y, chg_x = change.pos
        end_y, end_x = change.insert_end_pos


        if change.insert:
            if self_y >= chg_y:
                self_y += end_y - chg_y

            if self_y == end_y:
                if end_y == chg_y:
                    self_x += (end_x - chg_x)
                else:
                    self_x += end_x

        if change.remove:
            end_y, end_x = change.inverse.insert_end_pos

            if (chg_y, chg_x) < (self_y, self_x) < (end_y, end_x):
                self_y, self_x = chg_y, chg_x

            else:
                if self_y >= end_y:
                    self_y -= end_y - chg_y
                

                dx = -(end_x if self_y == end_y and self_x >= end_x else 0) + \
                      (chg_x if self_y == chg_y and chg_y == end_y  and self_x >= end_x else 0)

                
                self_x += dx

        self.pos = self_y, self_x

    def insert(self, text):        
        self.manip.execute(TextModification(pos=self.pos, insert=text))

    def text_to(self, other):
        return self.buffer.span_text(self.pos, end_pos=other.pos)

    def remove_to(self, other):
        self.manip.execute(TextModification(pos=self.pos, remove=self.text_to(other)))

    def delete(self, n=1):
        start_pos = self.buffer.calculate_pos(self.pos, n)
        end_pos = self.pos

        start_pos, end_pos = sorted([start_pos, end_pos])
        
        remove = self.buffer.span_text(start_pos, end_pos=end_pos)
        
        mod = TextModification(pos=start_pos, remove=remove)
        self.manip.execute(mod)

    def backspace(self, n=1):
        self.delete(-n)


def main():
    from .new_buffer import Buffer
    from .buffer_manipulator import BufferManipulator

    buff = Buffer()
    manip = BufferManipulator(buff)

    curs = Cursor(manip)
        
    with manip.history.transaction():
        curs.insert("Hello,\n")

    print(curs.pos)
    print(buff.dump())
    with manip.history.transaction():
        curs.insert('world!fj')


    print(curs.pos)
    print(buff.dump())

    
    with manip.history.transaction():
        curs.backspace()
        curs.backspace()

    print(curs.pos)
    print(buff.dump())

    curs.pos = 0,0
    with manip.history.transaction():
        curs.insert('abcd')

    print(curs.pos)
    print(buff.dump())


    curs2 = Cursor(manip)
    with manip.history.transaction():
        curs2.remove_to(curs)

    print(curs.pos)
    print(curs2.pos)
    print(buff.dump())

    with manip.history.transaction():
        curs.pos = 0, 6
        curs.delete(1)

    print(curs.pos)
    print(buff.dump())

    manip.history.undo()


    with manip.history.transaction():
        curs.pos = 0, 6
        curs.backspace(1)

    print(curs.pos)
    print(buff.dump())



if __name__ == '__main__':
    main()
    
