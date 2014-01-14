
import logging
import re

from .                          import syntax
from .cua_interaction           import CUAInteractionMode
from ..                         import util
from ..buffers                  import Cursor, BufferManipulator, Buffer
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

    @Signal
    def user_changed_buffer(self, change):
        pass

    @Signal
    def buffer_needs_highlight(self):
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
            curs.set_attribute_to(anchor, 'bgcolor', '#666')
        
        if full:
            self.view.full_redraw()
        else:
            self.view.partial_redraw()


@autoconnect(Controller.buffer_needs_highlight,
             lambda tags: tags.get('syntax') == 'python')
def python_syntax_highlighting(controller):
    syntax.python_syntax(controller.buffer)

@autoconnect(Controller.user_changed_buffer, 
             lambda tags: tags.get('autoindent'))
def autoindent(presenter, chg):
    manip = presenter.manipulator
    if chg.insert.endswith('\n'):
        beg_curs = Cursor(manip.buffer).move(*chg.pos)
        indent = re.match(r'^\s*', beg_curs.line.text)
        if indent is not None:
            Cursor(manip.buffer)\
                .move(*chg.insert_end_pos)\
                .insert(indent.group(0))




