
import logging
import re

from .                          import syntax
from .cua_interaction           import CUAInteractionMode
from ..                         import util
from ..buffers                  import Cursor, BufferManipulator, Buffer, Span, Region
from ..core                     import AttributedString, errors, Signal
from ..core.tag                 import Tagged, autoconnect
from ..core.attributed_string   import lower_bound
from ..core.key                 import *


class Controller(Tagged):
    def __init__(self, view, buff):
        '''
        :type view: codeedit.qt.view.TextView
        :type buff: codeedit.buffer.Buffer
        '''
        super().__init__()

        self.view               = view
        self.buffer             = buff
        self.view.lines         = self.buffer.lines
        self.view.keep          = self
        self.manipulator        = BufferManipulator(buff)
        self.canonical_cursor   = Cursor(self.manipulator)
        self.anchor_cursor      = None

        self.interaction_mode   = CUAInteractionMode(self)

        self.view.scrolled                  += self._on_view_scrolled
        self.manipulator.executed_change    += self.user_changed_buffer
        self.view.completion_done           += self.completion_done


        self._prev_region = Region()



    @Signal
    def user_changed_buffer(self, change):
        pass

    @Signal
    def buffer_needs_highlight(self):
        pass

    @Signal
    def completion_requested(self):
        pass

    @Signal
    def completion_done(self, index):
        pass

    def _on_view_scrolled(self, start_line):
        self.view.start_line = start_line

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
        
        removed_region.set_attributes(bgcolor=None)
        added_region.set_attributes(bgcolor='#666')


        self._prev_region = selected_region

        
        if full:
            self.view.full_redraw()
        else:
            self.view.partial_redraw()




