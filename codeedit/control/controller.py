
import logging
import re

import pathlib

from .                          import syntax
from .cua_interaction           import CUAInteractionMode
from ..                         import util
from ..buffers                  import Cursor, BufferManipulator, Buffer, Span, Region
from ..core                     import AttributedString, errors, Signal, write_atomically, command
from ..core.tag                 import Tagged, autoconnect
from ..core.attributed_string   import lower_bound
from ..core.key                 import *
from ..core.responder           import Responder, responds



class Controller(Tagged, Responder):
    def __init__(self, view, buff, provide_interaction_mode=True):
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
        #self.view.completion_row_changed    += self.completion_row_changed
        self.buffer_set = None

        self._prev_region = Region()
        self._is_modified = False

        view.controller = self

    
    @responds(command.save_cmd)
    def save(self):
        if self.path is not None:
            self.write_to_path(self.path)


    @property
    def view(self): 
        return self._view

    def _after_buffer_modification(self, chg):
        self.is_modified = True
        
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




