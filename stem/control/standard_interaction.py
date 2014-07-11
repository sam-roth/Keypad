
import re
import logging

from ..core                     import AttributedString, errors
from ..core.key                 import KeySequenceDict, Keys, Ctrl, Alt, Shift, Meta, Modifiers
from ..core.attributed_string   import lower_bound
from ..core.responder           import Responder
from .interactive               import interactive
from ..buffers                  import Cursor, Span
from ..options                  import GeneralSettings


from ..abstract.application import app
from ..abstract.textview import MouseButton, MouseEvent, MouseEventKind

import unicodedata

def isprint(ch):
    try:
        return not unicodedata.category(ch).startswith('C')
    except TypeError:
        return False


class StandardInteractionMode(Responder):
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

    def make_advance_para(self, n):
        def result():
            skip = True
            c = self.curs
            for _ in c.walklines(n):
                if c.searchline(r'^\s*$'):
                    if not skip:
                        break       
                else:
                    skip = False
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

        self.settings = GeneralSettings.from_config(controller.config)

        self.controller = controller
        self.controller.add_next_responders(self)

        self.view = controller.view

        self.modeline = AttributedString()
        self.view.modelines = (self.modeline,)

        self._last_mouse_move = None

        def mov(func, *args, ignore_shift=False):
            def result(evt):
                if not ignore_shift and evt.key.modifiers & Modifiers.Shift:
                    with self.controller.selection.select():
                        func(self.controller.selection, *args)
                else:
                    func(self.controller.selection, *args)
            return result

        def method(name):
            def result(instance, *args, **kw):
                return getattr(instance, name)(*args, **kw)
            return result

        def movm(func, *args, ignore_shift=False):
            return mov(method(func), *args, ignore_shift=ignore_shift)


        def select_all(evt):
            sel = self.controller.selection
            sel.move(0,0)
            with sel.select():
                sel.last_line().end()


        def delete_word(n, evt):
            sel =  self.controller.selection
            sel.clear_selection()
            with sel.select():
                sel.advance_word(n)
            sel.text = ''


        def page_down(sel, n):
            height, width = self.view.plane_size
            sel.down(height * n)            

        def copy():
            interactive.run('clipboard_copy')
        def paste():
            interactive.run('clipboard_paste')
        def cut():
            interactive.run('clipboard_cut')
        def delete():
            self.controller.selection.backspace()

        self._context_menu_items = [('Cut', cut),
                                    ('Copy', copy),
                                    ('Paste', paste)]
                                    


        manip = self.curs.manip


        self.keybindings = KeySequenceDict(
            (Keys.left      .optional(Shift),   movm('right', -1)),
            (Keys.right     .optional(Shift),   movm('right', 1)),
            (Keys.up        .optional(Shift),   movm('down', -1)),
            (Keys.down      .optional(Shift),   movm('down', 1)),
            (Keys.backspace .optional(Shift),   movm('backspace', ignore_shift=True)),
            (Keys.delete    .optional(Shift),   movm('delete', 1, ignore_shift=True)),
            (Keys.home      .optional(Shift),   movm('home')),
            (Keys.end       .optional(Shift),   movm('end')),
            (Keys.ctrl.a,                       select_all),
            (Keys.enter,                        movm('replace', '\n', ignore_shift=True)),
            (Keys.alt.right .optional(Shift),   movm('advance_word', 1)),
            (Keys.alt.left  .optional(Shift),   movm('advance_word', -1)),
            (Keys.alt.backspace.optional(Shift),lambda evt: delete_word(-1, evt)),
            (Keys.alt.delete.optional(Shift),   lambda evt: delete_word(1, evt)),
            (Keys.alt.down  .optional(Shift),   movm('advance_para', 1)),
            (Keys.alt.up    .optional(Shift),   movm('advance_para', -1)),
            (Keys.tab,                          movm('tab')),
            (Keys.backtab   .optional(Shift),   movm('tab', -1, ignore_shift=True)),
            (Keys.pagedown  .optional(Shift),   mov(page_down, 1)),
            (Keys.pageup    .optional(Shift),   mov(page_down, -1)),
        )



        kb = self.keybindings

        kb[Keys.return_.optional(Shift)] = kb[Keys.enter]

        # mainly for Mac users (though Home and End are mapped too)
        kb[Ctrl.left.optional(Shift)]   = kb[Keys.home]
        kb[Ctrl.right.optional(Shift)]  = kb[Keys.end]


        self.controller.view.key_press.connect(self._on_key_press)
        self.controller.view.mouse_down_char.connect(self._on_mouse_down)
        self.controller.view.mouse_move_char.connect(self._on_mouse_move)
        self.controller.view.input_method_preedit.connect(self._on_input_method_preedit)
        self.controller.view.input_method_commit.connect(self._on_input_method_commit)
        self.controller.view.mouse_event.connect(self._on_mouse_event)


        self._show_default_modeline()
        self.controller.refresh_view(full=True)


        self._preedit_span = None

    def detach(self):
        self.controller.remove_next_responders(self)
        self.controller.view.key_press.disconnect(self._on_key_press)
        self.controller.view.mouse_event.disconnect(self._on_mouse_event)
#         self.controller.view.scrolled.disconnect(self._on_view_scrolled)
        self.controller.view.mouse_down_char.disconnect(self._on_mouse_down)
        self.controller.view.mouse_move_char.disconnect(self._on_mouse_move)
        self.view.modelines = ()

    def _on_mouse_event(self, event):
        assert isinstance(event, MouseEvent)

        if (event.kind == MouseEventKind.mouse_down
                and event.buttons & MouseButton.right_button):
            self.controller.view.show_context_menu(event.pos,
                                                   self._context_menu_items)

    def _on_view_scrolled(self, start_line):
        pass

    def _on_mouse_down(self, line, col):
        self._last_mouse_move = None
        sel = self.controller.selection
        sel.move(0,0).down(line).right(col)
        self._show_default_modeline()
        self.controller.refresh_view()

    def _on_mouse_move(self, buttons, line, col):
        mouse_move = buttons, line, col
        if self._last_mouse_move == mouse_move:
            return

        if buttons & MouseButton.left_button:
            sel = self.controller.selection
            with sel.select():
                sel.move(0,0).down(line).right(col)

            self._show_default_modeline()
            self.controller.refresh_view()

        self._last_mouse_move = mouse_move



    @property
    def curs(self):
        return self.controller.canonical_cursor


    def show_modeline(self, text):
        self.modeline.remove(0, None)
        self.modeline.append(text)
        if isinstance(text, str):
            self.modeline.set_attributes(**dict(self.settings.modeline_attrs))
#             self.modeline.set_attribute('color', '#268bd2')

        self.view.modelines = [self.modeline]


    def _show_default_modeline(self):
        self.modeline.remove(0, None)
        path = self.controller.path
        if path is None:
            path = '<unsaved>'
        else:
            path = str(path)
            if len(path) > 20:
                path = '…' + path[-19:]

        loc_hint = '{0}:{1}:{2}'.format(path, self.curs.y+1, self.curs.x+1)
        self.modeline.append('{:<50} [{}]'.format(loc_hint, type(self).__name__))
        self.modeline.set_attributes(**dict(self.settings.modeline_attrs))

        self.view.modelines = [self.modeline]


    def show_error(self, text):
        app().beep()
        self.show_modeline(AttributedString(
            text,
            bgcolor='#dc322f',
            color='#fdf6e3'
        ))
        self.controller.refresh_view()


    def _on_input_method_preedit(self, text):

        c = self.curs
        with c.manip.history.scratchpad():
            sc = self.curs.clone()
            sc.chirality = Cursor.Chirality.Left
            c.insert(text)
            self._preedit_span = Span(sc, c)
            self._preedit_span.set_attributes(lexcat='search')


    def _on_input_method_commit(self, 
                                preedit_text,
                                replace_start, replace_stop,
                                replace_text):

        with self.curs.manip.history.transaction():
            if self._preedit_span is not None:
                self._preedit_span.text = replace_text
                self._preedit_span.set_attributes(lexcat=None)
                self._preedit_span = None
            else:
                self.curs.insert(replace_text)


    def _on_key_press(self, evt):
        success = True
        with self.curs.manip.history.transaction():
            try:
                binding = self.keybindings[evt.key]
            except KeyError:
                if isprint(evt.text):
                    self.controller.selection.text = evt.text
            else:
                try:
                    binding(evt)
                except errors.UserError as exc:
                    logging.exception(exc)
                    self.show_error(str(exc) + ' [' + type(exc).__name__ + ']')
                    success = False

            if success:
                self._show_default_modeline()

