
import logging
import re

import pathlib

from .                          import syntax
from .cua_interaction           import CUAInteractionMode
from ..                         import util
from ..buffers                  import Cursor, BufferManipulator, Buffer, Span, Region
from ..core                     import AttributedString, errors, Signal, write_atomically, commands
from ..core.tag                 import Tagged, autoconnect
from ..core.attributed_string   import lower_bound
from ..core.key                 import *
from ..core.responder           import Responder, responds


from .interactive import interactive

class BufferController(Tagged, Responder):
    def __init__(self, buffer_set, view, buff, provide_interaction_mode=True):
        '''
        :type view: codeedit.qt.view.TextView
        :type buff: codeedit.buffers.Buffer
        '''
        super().__init__()

        self._view              = view
        self.buffer             = buff
        self.view.lines         = self.buffer.lines
        self.view.keep          = self
        self.manipulator        = BufferManipulator(buff)
        self.canonical_cursor   = Cursor(self.manipulator)
        self.anchor_cursor      = None

        if provide_interaction_mode:
            self.interaction_mode = CUAInteractionMode(self)
        else:
            self.interaction_mode = None

        self.view.scrolled                  += self._on_view_scrolled
        self.manipulator.executed_change    += self.user_changed_buffer
        #self.view.completion_done           += self.completion_done
        buff.text_modified                  += self.buffer_was_changed 
        buff.text_modified                  += self._after_buffer_modification

        self.history.transaction_committed  += self._after_history_transaction_committed
        #self.view.completion_row_changed    += self.completion_row_changed
        self.buffer_set = buffer_set

        self._prev_region = Region()
        self._is_modified = False

        view.controller = self

    
    @responds(commands.save_cmd)
    def save(self):
        if self.path is not None:
            self.write_to_path(self.path)


    @property
    def view(self): 
        return self._view

    def _after_buffer_modification(self, chg):
        self.is_modified = True

    def _after_history_transaction_committed(self):
        self.refresh_view()
        
    @property
    def is_modified(self):
        return self._is_modified

    @is_modified.setter
    def is_modified(self, val):
        if val != self._is_modified:
            self._is_modified = val
            self.modified_was_changed(val)
            print('modified changed:', val)

    
    @Signal
    def modified_was_changed(self, val):
        pass


    @property
    def history(self):
        return self.manipulator.history

    @property
    def path(self):
        return self.tags.get('path')
    
    def clear(self):
        '''
        Remove all text from `self.buffer`.

        Requires an active history transaction.
        '''
        start = Cursor(self.buffer)
        end = Cursor(self.buffer).move(*self.buffer.end_pos)
        start.remove_to(end)

    def append_from_path(self, path):
        '''
        Append the contents of `self.buffer` with the contents of the file
        located at `path` decoded using UTF-8.

        Requires an active history transaction.
        '''
        with path.open('rb') as f:
            Cursor(self.buffer).move(*self.buffer.end_pos).insert(f.read().decode())

    def replace_from_path(self, path):
        '''
        Replace the contents of `self.buffer` with the contents of the
        file located at `path` decoded using UTF-8. 

        Requires an active history transaction.
        '''

        self.clear()
        self.append_from_path(path)
        self.add_tags(path=path)
        self.is_modified = True

        self.canonical_cursor.move(0,0)

        self.loaded_from_path(path)

    def write_to_path(self, path):
        '''
        Atomically write the contents of `self.buffer` to the file located
        at `path` encoded with UTF-8.
        '''
        
        self.will_write_to_path(path)
        with write_atomically(path) as f:
            f.write(self.buffer.text.encode())
        self.wrote_to_path(path)
        self.is_modified = False
    
    
    @Signal
    def will_write_to_path(self, path):
        pass

    @Signal
    def wrote_to_path(self, path):
        pass

    @Signal
    def loaded_from_path(self, path):
        pass


    @Signal
    def user_changed_buffer(self, change):
        pass

    @Signal
    def buffer_was_changed(self, change):
        pass

    @Signal
    def buffer_needs_highlight(self):
        pass

    @Signal
    def completion_requested(self):
        pass
    
    @Signal
    def user_requested_help(self):
        pass

    def _on_view_scrolled(self, start_line):
        self.view.start_line = start_line
        self.refresh_view(full=True)

    def refresh_view(self, full=False):
        self.view.lines = self.buffer.lines

        
        self.buffer_needs_highlight()

        curs = self.canonical_cursor
        if curs is not None:
            curs_line = curs.line
            self.view.cursor_pos = curs.pos

        anchor = self.anchor_cursor
        
        # draw selection
        if anchor is not None:
            selected_region = Span(curs, anchor)
        else:
            selected_region = Region()

        previous_region = self._prev_region

        # areas in the currently selected region not in the previously
        # selected region
        added_region    = selected_region - previous_region

        # areas in the previously selected region not in the currently selected
        # region
        removed_region  = previous_region - selected_region
        
        removed_region.set_attributes(sel_bgcolor=None)
        added_region.set_attributes(sel_bgcolor='#666')


        self._prev_region = selected_region

        
        if full:
            self.view.full_redraw()
        else:
            self.view.partial_redraw()


from ..abstract.application import app

@interactive('show_error')
def show_error(buff: BufferController, error):
    buff.view.beep()
    buff.interaction_mode.show_error(str(error) + ' [' + type(error).__name__ + ']')


@interactive('clipboard_copy')
def clipboard_copy(buff: BufferController):
    if buff.anchor_cursor is not None:
        text = buff.anchor_cursor.text_to(buff.canonical_cursor)
        app().clipboard_value = text

@interactive('clipboard_paste')
def clipboard_paste(buff: BufferController):
    clip_val = app().clipboard_value
    if clip_val is None:
        return

    with buff.history.transaction():
        if buff.anchor_cursor is not None:
            text = buff.anchor_cursor.remove_to(buff.canonical_cursor)
        buff.canonical_cursor.insert(clip_val)

@interactive('undo')
def undo(buff: BufferController):
    buff.history.undo()

@interactive('redo')
def redo(buff: BufferController):
    buff.history.redo()


@interactive('write')
def write(buff: BufferController, path: str=None):
    path = buff.path if path is None else pathlib.Path(path)
    buff.write_to_path(path)
    buff.add_tags(path=path)


@interactive('gui_write', 'gwrite', 'gwr')
def gui_write(buff: BufferController):
    path = buff.buffer_set.run_save_dialog(buff.path)
    if path:
        print('path was', path)
        buff.write_to_path(path)
        buff.add_tags(path=path)
        return True
    else:
        return False

@interactive('gui_save', 'gsave', 'gsv')
def gui_save(buff: BufferController):
    if not buff.path:
        gui_write(buff)
    else:
        write(buff)



@interactive('clear')
def clear(buff: BufferController, path: str=None):
    with buff.history.transaction():
        buff.clear()


@interactive('lorem')
def lorem(buff: BufferController):
    from . import lorem
    with buff.history.transaction():
        buff.canonical_cursor.insert(lorem.text_wrapped)


@interactive('py')
def eval_python(first_responder: object, *python_code):
    code = ' '.join(python_code)
    eval(code)


@interactive('pwd')
def getpwd(first_responder: object):
    from .command_line_interaction import writer
    import os.path
    
    writer.write(str(os.path.abspath(os.path.curdir)))


import ast

@interactive('tag')
def add_tag(buff: BufferController, key, value):
    buff.add_tags(**{key: ast.literal_eval(value)})

@interactive('untag', 'unt')
def rem_tag(buff: BufferController, key):
    buff.remove_tags([key])

@interactive('dumptags')
def dumptags(buff: BufferController):
    import pprint
    from .command_line_interaction import writer

    fmt = pprint.pformat(dict(buff.tags))

    writer.write(fmt)



