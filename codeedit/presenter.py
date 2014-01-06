

    
from .qt.view import TextView
from PyQt4.Qt import *
from .buffer import Buffer, Cursor

from .attributed_string import AttributedString

def set_attribute(lines, attribute, value, start_line, start_col, end_line, end_col):

    if start_line > end_line:
        print('swapped start and end 1')
        start_col, end_col = end_col, start_col
        start_line, end_line = end_line, start_line

    print(start_col, end_col, start_line, end_line)

    if start_line == end_line:
        if start_col > end_col:
            start_col, end_col = end_col, start_col
        
        lines[start_line].set_attribute(start_col, end_col, attribute, value)
        print(lines[start_line]._attributes)

    else:
        lines[start_line].set_attribute(start_col, None, attribute, value)
        for line in lines[start_line+1:end_line]:
            line.set_attribute(0, None, attribute, value)
        lines[end_line].set_attribute(0, end_col, attribute, value)


def line_syntax_c(line):
    import re
    for match in re.finditer(r'int|char|void', line.text):
        line.set_attribute(match.start(), match.end(), 'color', '#5FF967')

    for match in re.finditer(r'return', line.text):
        line.set_attribute(match.start(), match.end(), 'color', '#FEFB67')

    for match in re.finditer(r'\d+', line.text):
        line.set_attribute(match.start(), match.end(), 'color', '#FF76FF')

class BufferPresenter(object):
    def __init__(self, view, buff):
        '''
        :type view: codeedit.qt.view.TextView
        :type buff: codeedit.buffer.Buffer
        '''
        self.view = view
        self.buffer = buff
        self.view.lines = self.buffer.lines
        self.view.keep = self

        self.view.scrolled.connect(self.view_scrolled)

    def __del__(self):
        print('deleted buffer presenter')

    def view_scrolled(self, start_line):
        print('view scrolled')
        self.view.start_line = start_line

        
    def refresh_view(self):
        #self.view.lines = []
        
        #for line in self.buffer.lines:
        #    self.view.lines.append(AttributedString(line.text))
        
        for line in self.buffer.lines:
            line.set_attribute('color', None)
            line.set_attribute('bgcolor', None)
            line.set_attribute('cursor_after', False)

            line_syntax_c(line)

        curs = self.buffer.canonical_cursor
        curs_line = self.view.lines[curs.line]
        self.view.cursor_pos = curs.line, curs.col
        
        # draw cursor
        #if curs.col == len(curs_line.text):
        #    curs_line.insert(curs.col, ' ')

        #if curs.col == len(curs_line):
        #    curs_line.set_attribute(len(curs_line)-1, len(curs_line), 'cursor_after', True)

        #curs_line.set_attribute(curs.col-1, curs.col, 'cursor_after', True)
        #curs_line.set_attribute(curs.col, curs.col+1, 'bgcolor', '#FFF')
        #curs_line.set_attribute(curs.col, curs.col+1, 'color',   '#000')
        
        # draw selection
        anchor = self.buffer.anchor_cursor
        if anchor is not None:
            set_attribute(self.view.lines, 
                          attribute='bgcolor',
                          value='#666',
                          start_line=anchor.line, start_col=anchor.col,
                          end_line=curs.line, end_col=curs.col)


        
        print(list(curs_line.iterchunks()))
        
        self.view.update_plane_size()
        self.view.viewport().update()


class BufferEffector(QObject):
    def __init__(self, view, buff, pres):
        '''
        :type view: codeedit.qt.view.TextView
        :type buff: codeedit.buffer.Buffer
        :type pres: codeedit.presenter.BufferPresenter
        '''

        super().__init__()

        self.view = view
        self.buff = buff
        self.pres = pres
        
        self.view.installEventFilter(self)

        self.view.mouse_down_char.connect(self.mouse_down_char)
        self.view.mouse_move_char.connect(self.mouse_move_char)

    def mouse_move_char(self, buttons, line, col):
        if buttons & TextView.MouseButtons.Left:
            if self.buff.anchor_cursor is None:
                self.buff.anchor_cursor = self.buff.canonical_cursor.clone()

            self.buff.canonical_cursor.go_to(line=line, col=col)
            self.pres.refresh_view()

    def mouse_down_char(self, line, col):
        self.buff.anchor_cursor = None
        curs = self.buff.canonical_cursor
        curs.go_to(line=line, col=col)
        self.pres.refresh_view()

    

    def eventFilter(self, obj, event):
        if obj == self.view:
            if event.type() == QEvent.KeyPress:
                assert isinstance(event, QKeyEvent)
                old_anchor = None
                if event.modifiers() & Qt.ShiftModifier:
                    if self.buff.anchor_cursor is None:
                        self.buff.anchor_cursor = self.buff.canonical_cursor.clone()
                else:
                    old_anchor = self.buff.anchor_cursor
                    self.buff.anchor_cursor = None
                curs = self.buff.canonical_cursor
                k = event.key()
                if k == Qt.Key_Left:
                    curs.go(right=-1)
                elif k == Qt.Key_Right:
                    curs.go(right=1)
                elif k == Qt.Key_Down:
                    curs.go(down=1)
                elif k == Qt.Key_Up:
                    curs.go(down=-1)
                elif k == Qt.Key_Home:
                    curs.go_to_home()
                elif k == Qt.Key_End:
                    curs.go_to_end()
                elif k == Qt.Key_Backspace:
                    if old_anchor is None:
                        curs.backspace()
                    else:
                        #curs.go(right=-1)
                        old_anchor.remove_until(curs)
                elif event.text():
                    curs.insert(event.text().replace('\r', '\n'))
                else:
                    
                    return super().eventFilter(obj, event)
                
                self.pres.refresh_view()
                return True

        
        return super().eventFilter(obj, event)



    
import weakref

def main():
    global presref

    buf = Buffer.from_text(
'''\
int main(int argc, char **argv)
{
    return 0;
}
'''
    )

    buf.canonical_cursor = buf.cursor(0, 0)
    buf.anchor_cursor = buf.cursor(0, 0)

    import sys
    app = QApplication(sys.argv)
    tv = TextView()
    tv.show()
    tv.raise_()

    pres = BufferPresenter(tv, buf)
    presref = weakref.ref(pres, lambda x: print('***WILL DELETE', x))
    pres.refresh_view()

    eff = BufferEffector(tv, buf, pres)

    app.exec_()






if __name__ == '__main__':
    main()

