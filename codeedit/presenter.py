

    
from .qt.view import TextView
from PyQt4.Qt import *
from .buffer import Buffer, Cursor

from .key import *

from .attributed_string import AttributedString

def set_attribute(lines, attribute, value, start_line, start_col, end_line, end_col):

    if start_line > end_line:
        start_col, end_col = end_col, start_col
        start_line, end_line = end_line, start_line


    if start_line == end_line:
        if start_col > end_col:
            start_col, end_col = end_col, start_col
        
        lines[start_line].set_attribute(start_col, end_col, attribute, value)

    else:
        lines[start_line].set_attribute(start_col, None, attribute, value)
        for line in lines[start_line+1:end_line]:
            line.set_attribute(0, None, attribute, value)
        lines[end_line].set_attribute(0, end_col, attribute, value)


def line_syntax_c(line):
    import re
    for match in re.finditer(r'int|char|void', line.text):
        line.set_attribute(match.start(), match.end(), 'color', '#b58900')

    for match in re.finditer(r'return', line.text):
        line.set_attribute(match.start(), match.end(), 'color', '#859900')

    for match in re.finditer(r'\d+', line.text):
        line.set_attribute(match.start(), match.end(), 'color', '#2aa198')

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


    def view_scrolled(self, start_line):
        self.view.start_line = start_line

        
    def refresh_view(self):
        #self.view.lines = []
        
        #for line in self.buffer.lines:
        #    self.view.lines.append(AttributedString(line.text))
        
        for line in self.buffer.lines:
            if line.caches.get('polished', False):
                continue
            line.set_attribute('color', None)
            line.set_attribute('bgcolor', None)
            line.set_attribute('cursor_after', False)

            line_syntax_c(line)
            line.caches['polished'] = True

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
        anchor = self.buffer.anchor_cursor
        
        # draw selection
        if anchor is not None:
            set_attribute(self.view.lines, 
                          attribute='bgcolor',
                          value='#666',
                          start_line=anchor.line, start_col=anchor.col,
                          end_line=curs.line, end_col=curs.col)


        
        
        #self.view.update_plane_size()
        self.view.partial_redraw()



class CursorMoveAction(object):
    def __init__(self, move_func):
        self.move_func = move_func

    def __call__(self, eff, evt):
        key = evt.key
        if key.modifiers & Modifiers.Shift:
            # Use old cursor as anchor cursor if there isn't an anchor cursor set.
            if eff.buff.anchor_cursor is None:
                eff.buff.anchor_cursor = eff.buff.canonical_cursor.clone()
        else:
            # Remove anchor cursor
            eff.buff.anchor_cursor = None
        curs = eff.buff.canonical_cursor
        self.move_func(curs)

class EditAction(object):
    def __init__(self, edit_func):
        self.edit_func = edit_func

    def __call__(self, eff, evt):
        key = evt.key
        erased = False
        if eff.buff.anchor_cursor is not None:
            erased = eff.buff.anchor_cursor.pos != eff.buff.canonical_cursor.pos
            eff.buff.canonical_cursor.remove_until(eff.buff.anchor_cursor)
            eff.buff.anchor_cursor = None
        curs = eff.buff.canonical_cursor
        self.edit_func(eff, evt, curs, erased)

                

@EditAction
def backspace_action(eff, evt, curs, erased):
    if not erased:
        curs.backspace()


@EditAction
def delete_action(eff, evt, curs, erased):
    if not erased:
        copy = curs.clone()
        copy.advance(1)
        curs.remove_until(copy)

@EditAction
def insert_action(eff, evt, curs, erased):
    curs.insert(evt.text)





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
        
        #self.view.installEventFilter(self)

        self.view.mouse_down_char.connect(self.mouse_down_char)
        self.view.mouse_move_char.connect(self.mouse_move_char)
        self.view.key_press.connect(self.key_press)

        #K = self.view.ui.parse_keystroke
        
        def page_move(c, n):
            _, height = self.view.plane_size
            c.go(down=n * height)
            #print('scrolling to', c.line)
            self.view.scroll_to_line(c.line)
            self.view.full_redraw()


        def undo(eff, evt):
            self.buff.history.undo()
            self.pres.refresh_view()

        def redo(eff, evt):
            self.buff.history.redo()
            self.pres.refresh_view()


        def find_word(direction):
            def result(c):
                while True:
                    st = c.select(forwards=direction).text 
                    if not st or st in (' ', '\t', '\n'):
                        c.advance(direction)
                        break
                    c.advance(direction)

            return result



        

        self.keybindings = KeySequenceDict(
			(key.left      .optional(shift),       CursorMoveAction(lambda c: c.go(left=1))),
			(key.right     .optional(shift),       CursorMoveAction(lambda c: c.go(right=1))),
			(key.down      .optional(shift),       CursorMoveAction(lambda c: c.go(down=1))),
			(key.up        .optional(shift),       CursorMoveAction(lambda c: c.go(up=1))),
			(key.home      .optional(shift),       CursorMoveAction(lambda c: c.go_to_home())),
			(key.end       .optional(shift),       CursorMoveAction(lambda c: c.go_to_end())),
			(key.backspace .optional(shift),       backspace_action),
			(key.delete    .optional(shift),       delete_action),
			(meta.h        .optional(shift),       CursorMoveAction(lambda c: c.advance(-1))),
			(meta.l        .optional(shift),       CursorMoveAction(lambda c: c.advance(1))),
			(key.pagedown  .optional(shift),       CursorMoveAction(lambda c: page_move(c, 1))),
			(key.pageup    .optional(shift),       CursorMoveAction(lambda c: page_move(c, -1))),
			(ctrl.z,                               undo),
			(ctrl.shift.z,                         redo),
			(alt.right     .optional(shift),       CursorMoveAction(find_word(1))),
			(alt.left      .optional(shift),       CursorMoveAction(find_word(-1))),
    
		)
        self.keybindings[ctrl.left.optional(shift)] = self.keybindings[key.home]
        self.keybindings[ctrl.right.optional(shift)] = self.keybindings[key.end]


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

    def key_press(self, event):
        curs = self.buff.canonical_cursor
        binding = self.keybindings.get(event.key, insert_action)

        if binding is not None:
            binding(self, event)
        else:
            # deletion
            if key.backspace.optional(shift).matches(event.key):
                if old_anchor is not None:
                    old_anchor.remove_until(curs)
                else:
                    curs.backspace()
            elif key.delete.optional(shift).matches(event.key):
                if old_anchor is not None:
                    old_anchor.remove_until(curs)
                else:
                    copy = curs.clone()
                    copy.advance(1)
                    curs.remove_until(copy)
            # insertion
            elif event.text:
                curs.insert(event.text.replace('\r', '\n'))

        self.pres.refresh_view()



#    def eventFilter(self, obj, event):
#        if obj == self.view:
#            if event.type() == QEvent.KeyPress:
#                assert isinstance(event, QKeyEvent)
#                old_anchor = None
#                if event.modifiers() & Qt.ShiftModifier:
#                    if self.buff.anchor_cursor is None:
#                        self.buff.anchor_cursor = self.buff.canonical_cursor.clone()
#                else:
#                    old_anchor = self.buff.anchor_cursor
#                    self.buff.anchor_cursor = None
#                curs = self.buff.canonical_cursor
#                k = event.key()
#                if k == Qt.Key_Left:
#                    curs.go(right=-1)
#                elif k == Qt.Key_Right:
#                    curs.go(right=1)
#                elif k == Qt.Key_Down:
#                    curs.go(down=1)
#                elif k == Qt.Key_Up:
#                    curs.go(down=-1)
#                elif k == Qt.Key_Home:
#                    curs.go_to_home()
#                elif k == Qt.Key_End:
#                    curs.go_to_end()
#                elif k == Qt.Key_Backspace:
#                    if old_anchor is None:
#                        curs.backspace()
#                    else:
#                        #curs.go(right=-1)
#                        old_anchor.remove_until(curs)
#                elif event.text():
#                    curs.insert(event.text().replace('\r', '\n'))
#                else:
#                    
#                    return super().eventFilter(obj, event)
#                
#                self.pres.refresh_view()
#                return True
#
        
        #return super().eventFilter(obj, event)



    
import weakref

def main():

    buf = Buffer.from_text(open('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.9.sdk/usr/include/stdio.h', 'r').read())
#'''\
#int main(int argc, char **argv)
#{
#    return 0;
#}
#'''
    #)

    buf.canonical_cursor = buf.cursor(0, 0)
    buf.anchor_cursor = buf.cursor(0, 0)

    import sys
    import logging

    logging.basicConfig(level=logging.DEBUG)

    #with codeedit.console.view.Application() as app:

    app = QApplication(sys.argv)
    #tv = codeedit.console.view.TextView(app.stdscr)
    tv = TextView()
    tv.show()
    tv.raise_()
    #app.keystroke.connect(tv.key_press)

    pres = BufferPresenter(tv, buf)
    #presref = weakref.ref(pres, lambda x: print('***WILL DELETE', x))
    pres.refresh_view()

    eff = BufferEffector(tv, buf, pres)

    app.exec_()

    #app.run()






if __name__ == '__main__':
    main()

