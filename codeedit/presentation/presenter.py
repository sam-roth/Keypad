
import logging
import re

from .                          import syntax
from .cua_interaction           import CUAInteractionMode
from ..                         import util
from ..buffers                  import Cursor
from ..core                     import AttributedString, errors
from ..core.attributed_string   import lower_bound
from ..core.key                 import *

class Presenter(object):
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

        self.canonical_cursor = Cursor(buff)
        self.anchor_cursor = Cursor(buff)


    def view_scrolled(self, start_line):
        self.view.start_line = start_line

        
    def refresh_view(self, full=False):
        self.view.lines = self.buffer.lines
        
        syntax.python_syntax(self.buffer)

        curs = self.canonical_cursor
        if curs is not None:
            curs_line = curs.line
            self.view.cursor_pos = curs.pos

        anchor = self.anchor_cursor
        
        # draw selection
        if anchor is not None:
            curs.set_attribute_to(anchor, 'bgcolor', '#666')
        
        if full:
            self.view.full_redraw()
        else:
            self.view.partial_redraw()


def main():
    from PyQt4 import Qt
    from .qt.view import TextView
    from .buffers import Buffer, BufferManipulator
    import re

    import sys

    app = Qt.QApplication(sys.argv)

    tv = TextView()
    buff = Buffer()
    manip = BufferManipulator(buff)

    @manip.executed_change.connect
    def autoindent(chg):
        if chg.insert.endswith('\n'):
            beg_curs = Cursor(manip.buffer).move(*chg.pos)
            indent = re.match(r'^\s*', beg_curs.line.text)
            if indent is not None:
                Cursor(manip.buffer)\
                    .move(*chg.insert_end_pos)\
                    .insert(indent.group(0))

    curs = Cursor(manip)

    with manip.history.transaction():
        curs.insert(open('/Users/Sam/Desktop/Projects/codeedit2/codeedit/presenter.py', 'r').read())
    
    pres = Presenter(tv, buff)
    pres.canonical_cursor = curs
    pres.anchor_cursor = None

    imode = CUAInteractionMode(pres)

    tv.show()
    tv.raise_()

    pres.refresh_view()

    app.exec_()
        
if __name__ == '__main__':
    main()
