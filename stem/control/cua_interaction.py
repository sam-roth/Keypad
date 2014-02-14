
import re
import logging

from ..core                     import AttributedString, errors
from ..core.key                 import KeySequenceDict, Keys, Ctrl, Alt, Shift, Meta, Modifiers
from ..core.attributed_string   import lower_bound
from ..core.responder           import Responder
from .interactive               import interactive
from ..buffers                  import Cursor

import unicodedata

def isprint(ch):
    try:
        return not unicodedata.category(ch).startswith('C')
    except TypeError:
        return False


class CUAInteractionMode(Responder):
    def make_cursor_move(self, fn):
        def result(evt):
            if evt.key.modifiers & Modifiers.Shift:
                if self.controller.anchor_cursor is None:
                    self.controller.anchor_cursor = self.curs.clone()
            else:
                self.controller.anchor_cursor = None
            fn()
        return result

    def make_remove(self, n):
        def result(evt):
            if self.controller.anchor_cursor is not None:
                self.curs.remove_to(self.controller.anchor_cursor)
                self.controller.anchor_cursor = None
            else:
                self.curs.delete(n)

        return result

    
    def make_page_move(self, n):
        def result():
            height, width = self.view.plane_size
            self.curs.down(n * height - 1)
        return result


    def select_all(self, evt):
        c = self.curs
        c.move(0, 0)
        other = c.clone()
        other.move(*self.controller.buffer.end_pos)
        self.controller.anchor_cursor = other


    def make_advance_word(self, n):
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

    
    
    def make_delete_word(self, n):
        advance = self.make_advance_word(n)
        def result(evt):
            if self.controller.anchor_cursor is None:
                self.controller.anchor_cursor = self.curs.clone()
                advance()
            self.curs.remove_to(self.controller.anchor_cursor)
            self.controller.anchor_cursor = None
        return result

    def __init__(self, controller):
        super().__init__()

        self.controller = controller
        self.controller.add_next_responders(self)

        self.view = controller.view

        self.modeline = AttributedString()
        self.view.modelines.append(self.modeline)
        
        cursor_move = self.make_cursor_move
        remove = self.make_remove
        page_move = self.make_page_move
        select_all = self.select_all
        advance_word = self.make_advance_word
        delete_word = self.make_delete_word

        manip = self.curs.manip

        
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
            (Keys.enter     .optional(Shift),   lambda evt: self.curs.insert('\n')),
            (Ctrl.a,                            select_all),
            (Ctrl.z,                            lambda evt: manip.history.undo()),
            (Ctrl.shift.z,                      lambda evt: manip.history.redo()),
            (Meta.space,                        lambda evt: controller.completion_requested()),
            (Keys.f1,                           lambda evt: controller.user_requested_help()),
            (Keys.tab,                          lambda evt: self.curs.insert('    ')),
        )



        kb = self.keybindings

        kb[Keys.return_.optional(Shift)] = kb[Keys.enter]

        # mainly for Mac users (though Home and End are mapped too)
        kb[Ctrl.left.optional(Shift)]   = kb[Keys.home]
        kb[Ctrl.right.optional(Shift)]  = kb[Keys.end]


        self.controller.view.key_press.connect(self._on_key_press)
        self.controller.view.scrolled.connect(self._on_view_scrolled)
        self.controller.view.mouse_down_char.connect(self._on_mouse_down)
        self.controller.view.mouse_move_char.connect(self._on_mouse_move)

        self._show_default_modeline()
        self.controller.refresh_view(full=True)

    def detach(self):
        self.controller.remove_next_responders(self)
        self.controller.view.key_press.disconnect(self._on_key_press)
        self.controller.view.scrolled.disconnect(self._on_view_scrolled)
        self.controller.view.mouse_down_char.disconnect(self._on_mouse_down)
        self.controller.view.mouse_move_char.disconnect(self._on_mouse_move)
        self.view.modelines.remove(self.modeline)


    def _on_view_scrolled(self, start_line):
        pass

    def _on_mouse_down(self, line, col):
        self.controller.anchor_cursor = None
        self.curs.move(0,0).down(line).right(col)
        self._show_default_modeline()
        self.controller.refresh_view()

    def _on_mouse_move(self, buttons, line, col):
        if buttons & self.controller.view.MouseButtons.Left:
            if self.controller.anchor_cursor is None:
                self.controller.anchor_cursor = self.curs.clone()
            self.curs.move(0,0).down(line).right(col)
            self._show_default_modeline()
            self.controller.refresh_view()



    @property
    def curs(self):
        return self.controller.canonical_cursor


    def show_modeline(self, text):
        self.modeline.remove(0, None)
        self.modeline.append(text)
        if isinstance(text, str):
            self.modeline.set_attribute('color', '#268bd2')


    def _show_default_modeline(self):
        self.modeline.remove(0, None)
        self.modeline.append('{:<20} [{}]'.format(repr(self.curs.pos), type(self).__name__))
        self.modeline.set_attribute('color', '#268bd2')


    def show_error(self, text):
        self.controller.view.beep()
        self.show_modeline(AttributedString(
            text,
            bgcolor='#dc322f',
            color='#fdf6e3'
        ))
        self.controller.refresh_view()

    
    def _on_key_press(self, evt):
        success = True
        with self.curs.manip.history.transaction():
            try:
                binding = self.keybindings[evt.key]
            except KeyError:
                if isprint(evt.text):
                    if self.controller.anchor_cursor is not None:
                        self.curs.remove_to(self.controller.anchor_cursor)
                        self.controller.anchor_cursor = None
                    self.curs.insert(evt.text)
            else:
                try:
                    binding(evt)
                except errors.UserError as exc:
                    logging.exception(exc)

                    self.show_error(str(exc) + ' [' + type(exc).__name__ + ']')
                    
                    #self.controller.view.beep()
                    #self.modeline.remove(0, None)
                    #self.modeline.append(str(exc) + ' [' + type(exc).__name__ + ']')
                    #self.modeline.set_attribute('bgcolor', '#dc322f') #'#800')
                    #self.modeline.set_attribute('color', '#fdf6e3')
                    #self.modeline.set_attribute('color', '#FFF')
                    success = False

            if success:
                self._show_default_modeline()

        plane_height, plane_width = self.controller.view.plane_size

        
        full_redraw_needed = False

        if self.view.start_line > self.curs.pos[0]:
            self.view.scroll_to_line(self.curs.pos[0])
            full_redraw_needed = True
        elif self.view.start_line + self.view.buffer_lines_visible <= self.curs.pos[0]:
            self.view.scroll_to_line(self.curs.pos[0] - self.view.buffer_lines_visible + 1)
            full_redraw_needed = True

        self.controller.refresh_view(full=full_redraw_needed)
        

#@interactive('imode_map', 'mmap')
#def imode_map(imode: CUAInteractionMode, seq, *cmd):
    
