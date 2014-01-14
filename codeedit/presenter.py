
import logging
import re
from .cursor import Cursor
from .attributed_string import AttributedString, lower_bound
from . import errors


from . import syntax, util

import unicodedata

def isprint(ch):
    try:
        return not unicodedata.category(ch).startswith('C')
    except TypeError:
        return False

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


from .key import *

class CUAInteractionMode(object):
    def __init__(self, pres):
        self.pres = pres
        self.view = pres.view

        self.modeline = AttributedString()
        self.view.modelines.append(self.modeline)

        def cursor_move(fn):
            def result(evt):
                if evt.key.modifiers & Modifiers.Shift:
                    if self.pres.anchor_cursor is None:
                        self.pres.anchor_cursor = self.curs.clone()
                else:
                    self.pres.anchor_cursor = None
                fn()
            return result
        
        
        
        def remove(n):
            def result(evt):
                if self.pres.anchor_cursor is not None:
                    self.curs.remove_to(self.pres.anchor_cursor)
                    self.pres.anchor_cursor = None
                else:
                    self.curs.delete(n)

            return result

        def page_move(n):
            def result():
                height, width = self.view.plane_size
                self.curs.down(n * height - 1)
            return result


        def select_all(evt):
            c = self.curs
            c.move(0, 0)
            other = c.clone()
            other.move(*self.pres.buffer.end_pos)
            self.pres.anchor_cursor = other


        def advance_word(n):
            rgx = re.compile(
                r'''
                  \b 
                | $ 
                | ^ 
                | _                     # for snake_case idents
                | (?<= _ ) \w           #  -> match after "_" too
                | (?<= [a-z] ) [A-Z]    # for camelCase and PascalCase idents
                | ['"]                  # match strings
                | (?<= ['"] ) .         # match after strings
                ''',
                re.VERBOSE
            )
            def result():
                line, col = self.curs.pos
                posns = [match.start() for match in 
                         rgx.finditer(self.curs.line.text)]
                idx = lower_bound(posns, col)
                idx += n
                
                try:
                    new_col = posns[idx]
                except IndexError:
                    if n < 0:
                        self.curs.up().end()
                    else:
                        self.curs.down().home()
                else:
                    self.curs.right(new_col - col)

            return result


        manip = self.curs.manip

        pres.view.completions = [(str(x),) for x in range(100)]

        
        self.keybindings = KeySequenceDict(
            (key.left       .optional(shift),   cursor_move(self.curs.left)), 
            (key.right      .optional(shift),   cursor_move(self.curs.right)), 
            (alt.left       .optional(shift),   cursor_move(advance_word(-1))),
            (alt.right      .optional(shift),   cursor_move(advance_word(1))),
            (key.up         .optional(shift),   cursor_move(self.curs.up)), 
            (key.down       .optional(shift),   cursor_move(self.curs.down)),
            (key.pagedown   .optional(shift),   cursor_move(page_move(1))),
            (key.pageup     .optional(shift),   cursor_move(page_move(-1))),
            (key.backspace,                     remove(-1)),
            (key.delete,                        remove(1)),
            (key.home       .optional(shift),   cursor_move(self.curs.home)),
            (key.end        .optional(shift),   cursor_move(self.curs.end)),
            (key.enter,                         lambda evt: self.curs.insert('\n')),
            (ctrl.a,                            select_all),
            (ctrl.z,                            lambda evt: manip.history.undo()),
            (ctrl.shift.z,                      lambda evt: manip.history.redo()),
            (meta.space,                        lambda evt: pres.view.show_completions()),
        )



        kb = self.keybindings

        kb[key.return_] = kb[key.enter]

        # mainly for Mac users (though Home and End are mapped too)
        kb[ctrl.left.optional(shift)] = kb[key.home]
        kb[ctrl.right.optional(shift)] = kb[key.end]


        self.pres.view.key_press.connect(self._on_key_press)
        self.pres.view.scrolled.connect(self._on_view_scrolled)
        self.pres.view.mouse_down_char.connect(self._on_mouse_down)
        self.pres.view.mouse_move_char.connect(self._on_mouse_move)

    def _on_view_scrolled(self, start_line):
        self.pres.refresh_view(full=True)
        #y, x = self.curs.pos
        #max_y = start_line + self.pres.view.buffer_lines_visible
        #new_y = util.clamp(start_line, max_y, y)

        #dy = new_y - y
        #
        #self.curs.down(dy)

        #self._show_default_modeline()
        #self.pres.refresh_view(full=True)

    def _on_mouse_down(self, line, col):
        self.pres.anchor_cursor = None
        self.curs.move(0,0).down(line).right(col)
        self._show_default_modeline()
        self.pres.refresh_view()

    def _on_mouse_move(self, buttons, line, col):
        if buttons & self.pres.view.MouseButtons.Left:
            if self.pres.anchor_cursor is None:
                self.pres.anchor_cursor = self.curs.clone()
            self.curs.move(0,0).down(line).right(col)
            self._show_default_modeline()
            self.pres.refresh_view()



    @property
    def curs(self):
        return self.pres.canonical_cursor


    def show_modeline(self, text):
        self.modeline.remove(0, None)
        self.modeline.append(text)
        if isinstance(text, str):
            self.modeline.set_attribute('color', '#268bd2')


    def _show_default_modeline(self):
        self.modeline.remove(0, None)
        self.modeline.append('{:<20} [{}]'.format(self.curs.pos, type(self).__name__))
        self.modeline.set_attribute('color', '#268bd2')

    
    def _on_key_press(self, evt):
        success = True
        logging.debug('key press: %s', evt)
        with self.curs.manip.history.transaction():
            try:
                binding = self.keybindings[evt.key]
            except KeyError:
                if isprint(evt.text):
                    self.curs.insert(evt.text)
            else:
                try:
                    binding(evt)
                except errors.UserError as exc:
                    logging.exception(exc)
                    
                    self.pres.view.beep()
                    self.modeline.remove(0, None)
                    self.modeline.append(str(exc) + ' [' + type(exc).__name__ + ']')
                    self.modeline.set_attribute('bgcolor', '#dc322f') #'#800')
                    self.modeline.set_attribute('color', '#fdf6e3')
                    #self.modeline.set_attribute('color', '#FFF')
                    success = False

            if success:
                self._show_default_modeline()

        plane_height, plane_width = self.pres.view.plane_size

        
        full_redraw_needed = False

        if self.view.start_line > self.curs.pos[0]:
            self.view.scroll_to_line(self.curs.pos[0])
            full_redraw_needed = True
        elif self.view.start_line + self.view.buffer_lines_visible <= self.curs.pos[0]:
            self.view.scroll_to_line(self.curs.pos[0] - self.view.buffer_lines_visible + 1)
            full_redraw_needed = True

        self.pres.refresh_view(full=full_redraw_needed)
        

def main():
    from PyQt4 import Qt
    from .qt.view import TextView
    from .buffer import Buffer
    from .buffer_manipulator import BufferManipulator
    from .cursor import Cursor
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
