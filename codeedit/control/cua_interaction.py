
import re
import logging

from ..core                     import AttributedString, errors
from ..core.key                 import KeySequenceDict, Keys, Ctrl, Alt, Shift, Meta, Modifiers
from ..core.attributed_string   import lower_bound


import unicodedata

def isprint(ch):
    try:
        return not unicodedata.category(ch).startswith('C')
    except TypeError:
        return False


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
                
                if 0 <= idx < len(posns):
                    new_col = posns[idx]
                    self.curs.right(new_col - col)
                elif idx < 0:
                    self.curs.up().end()
                else:
                    self.curs.down().home()

            return result

        
        def delete_word(n):
            advance = advance_word(n)
            def result(evt):
                if self.pres.anchor_cursor is None:
                    self.pres.anchor_cursor = self.curs.clone()
                    advance()
                self.curs.remove_to(self.pres.anchor_cursor)
                self.pres.anchor_cursor = None
            return result




        manip = self.curs.manip

        pres.view.completions = [(str(x),) for x in range(100)]
        
        self.keybindings = KeySequenceDict(
            (Keys.left      .optional(Shift),   cursor_move(self.curs.left)), 
            (Keys.right     .optional(Shift),   cursor_move(self.curs.right)), 
            (Alt.left       .optional(Shift),   cursor_move(advance_word(-1))),
            (Alt.right      .optional(Shift),   cursor_move(advance_word(1))),
            (Alt.backspace,                     delete_word(-1)),
            (Alt.delete,                        delete_word(1)),
            (Keys.up        .optional(Shift),   cursor_move(self.curs.up)), 
            (Keys.down      .optional(Shift),   cursor_move(self.curs.down)),
            (Keys.pagedown  .optional(Shift),   cursor_move(page_move(1))),
            (Keys.pageup    .optional(Shift),   cursor_move(page_move(-1))),
            (Keys.backspace,                    remove(-1)),
            (Keys.delete,                       remove(1)),
            (Keys.home      .optional(Shift),   cursor_move(self.curs.home)),
            (Keys.end       .optional(Shift),   cursor_move(self.curs.end)),
            (Keys.enter,                        lambda evt: self.curs.insert('\n')),
            (Ctrl.a,                            select_all),
            (Ctrl.z,                            lambda evt: manip.history.undo()),
            (Ctrl.shift.z,                      lambda evt: manip.history.redo()),
            (Meta.space,                        lambda evt: pres.completion_requested()),
            (Keys.f1,                           lambda evt: pres.user_requested_help()),
            (Keys.tab,                          lambda evt: self.curs.insert('    ')),
        )



        kb = self.keybindings

        kb[Keys.return_]                = kb[Keys.enter]

        # mainly for Mac users (though Home and End are mapped too)
        kb[Ctrl.left.optional(Shift)]   = kb[Keys.home]
        kb[Ctrl.right.optional(Shift)]  = kb[Keys.end]


        self.pres.view.key_press.connect(self._on_key_press)
        self.pres.view.scrolled.connect(self._on_view_scrolled)
        self.pres.view.mouse_down_char.connect(self._on_mouse_down)
        self.pres.view.mouse_move_char.connect(self._on_mouse_move)

    def _on_view_scrolled(self, start_line):
        pass
        #self.pres.refresh_view(full=True)
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
        with self.curs.manip.history.transaction():
            try:
                binding = self.keybindings[evt.key]
            except KeyError:
                if isprint(evt.text):
                    if self.pres.anchor_cursor is not None:
                        self.curs.remove_to(self.pres.anchor_cursor)
                        self.pres.anchor_cursor = None
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
        

