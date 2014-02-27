
import logging
import re

import pathlib

from .cua_interaction           import CUAInteractionMode
from ..                         import util
from ..buffers                  import ModifiedCursor, Cursor, BufferManipulator, Buffer, Span, Region
from ..buffers.selection        import Selection, BacktabMixin
from ..core                     import AttributedString, errors, Signal, write_atomically, color
from ..core.tag                 import Tagged, autoconnect
from ..core.attributed_string   import lower_bound
from ..core.key                 import *
from ..core.responder           import Responder



class SelectionImpl(BacktabMixin, Selection):
    pass


from .interactive import interactive

class BufferController(Tagged, Responder):
    def __init__(self, buffer_set, view, buff, provide_interaction_mode=True):
        '''
        :type view: stem.qt.view.TextView
        :type buff: stem.buffers.Buffer
        '''
        super().__init__()

        self.last_canonical_cursor_pos = 0,0
        self._view              = view
        self.buffer             = buff
        self.view.lines         = self.buffer.lines
        self.view.keep          = self
        self.manipulator        = BufferManipulator(buff)

        self.selection          = SelectionImpl(self.manipulator)

#        self.canonical_cursor   = ModifiedCursor(self.manipulator)
#        self.anchor_cursor      = None


        self.view.scrolled                  += self._on_view_scrolled
        
        self.manipulator.executed_change    += self.user_changed_buffer
        #self.view.completion_done           += self.completion_done
        buff.text_modified                  += self.buffer_was_changed 
        buff.text_modified                  += self._after_buffer_modification

        self.history.transaction_committed  += self._after_history_transaction_committed
        #self.view.completion_row_changed    += self.completion_row_changed
        self.buffer_set = buffer_set
        
        self.view.closing.connect(self.closing)

        self._prev_region = Region()
        self._is_modified = False
        


        view.controller = self

        if provide_interaction_mode:
            self.interaction_mode = CUAInteractionMode(self)
        else:
            self.interaction_mode = None

        self.instance_tags_added.connect(self.__after_tags_added)

    @property
    def canonical_cursor(self):
        return self.selection.insert_cursor
    
    @property
    def anchor_cursor(self):
        return self.selection.anchor_cursor

    @Signal
    def closing(self):
        pass
    
    @Signal
    def canonical_cursor_move(self):
        pass
    
    
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

    def __after_tags_added(self, tags):
        if 'path' in tags:
            self.path_changed()


    @Signal
    def path_changed(self):
        pass

        
    @property
    def is_modified(self):
        return self._is_modified

    @is_modified.setter
    def is_modified(self, val):
        if val != self._is_modified:
            self._is_modified = val
            self.modified_was_changed(val)

    
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

    def replace_from_path(self, path, create_new=False):
        '''
        Replace the contents of `self.buffer` with the contents of the
        file located at `path` decoded using UTF-8. 

        Requires an active history transaction.
        '''

        self.clear()
        try:
            self.append_from_path(path)
        except FileNotFoundError:
            if not create_new:
                raise

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
            if curs.pos != self.last_canonical_cursor_pos:
                self.canonical_cursor_move()
                self.last_canonical_cursor_pos = curs.pos
            self.view.cursor_pos = curs.pos

        anchor = self.anchor_cursor
        
        # draw selection
        if anchor is not None:
            selected_region = Span(curs, anchor).region
        else:
            selected_region = Region()

        
        
        overlay_spans = []
        for span in selected_region.spans:
            overlay_spans.extend([
                (span, 'sel_color', 'auto'),
                (span, 'sel_bgcolor', 'auto')
            ])
        
        self.view.overlay_spans['selection'] = overlay_spans
        
        if full:
            self.view.full_redraw()
        else:
            self.view.partial_redraw()

    
    def scroll_to_cursor(self):
        self.view.scroll_to_line(self.canonical_cursor.y)
        self.refresh_view(full=True)
from ..abstract.application import app

@interactive('show_error')
def show_error(buff: BufferController, error):
    buff.view.beep()
    buff.interaction_mode.show_error(str(error) + ' [' + type(error).__name__ + ']')


@interactive('clipboard_cut')
def clipboard_cut(buff: BufferController):
    if buff.anchor_cursor is not None:
        clipboard_copy(buff)
        with buff.history.transaction():
            buff.anchor_cursor.remove_to(buff.canonical_cursor)
        buff.anchor_cursor = None


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
        buff.write_to_path(path)
        buff.add_tags(path=path)
        return True
    else:
        return False

@interactive('gui_save', 'gsave', 'gsv')
def gui_save(buff: BufferController):
    if not buff.path:
        return gui_write(buff)
    else:
        write(buff)

        return True



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

@interactive('cd')
def chdir(r: object, newdir: 'Path'):
    import os
    os.chdir(newdir)

    getpwd(r)


import ast

@interactive('tag', 'set')
def add_tag(buff: BufferController, key, value="True"):
    if buff.tags.get('cmdline', False):
        raise errors.NoBufferActiveError('Can\'t set tag on command line buffer.')
    buff.add_tags(**{key: ast.literal_eval(value)})

@interactive('untag', 'unt', 'unset')
def rem_tag(buff: BufferController, key):
    if buff.tags.get('cmdline', False):
        raise errors.NoBufferActiveError('Can\'t unset tag on command line buffer.')
    buff.remove_tags([key])

@interactive('dumptags')
def dumptags(buff: BufferController):
    import pprint
    from .command_line_interaction import writer

    fmt = pprint.pformat(dict(buff.tags))

    writer.write(fmt)



advance_word_regex = re.compile(
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


def advance_to(curs, rgx, count):

    line, col = curs.pos
    posns = [match.start() for match in 
             rgx.finditer(curs.line.text)]
    idx = lower_bound(posns, col)
    idx += count

    if 0 <= idx < len(posns):
        new_col = posns[idx]
        curs.right(new_col - col)
    elif idx < 0:
        curs.up().end()
    else:
        curs.down().home()


def page_down(bctl, count):
    height, width = bctl.view.plane_size
    self.curs.down(count * height - 1)




@interactive('cursor')
def cursor_motion(bctl: BufferController, move_select, motion, count=1):
    '''
    cursor <motion_type> <motion> <count=1>
    
    <motion>        -- one of left, right, up, down, advance_word, all, home, end, page_down, page_up
    <motion_type>   -- one of move, select, delete


    cursor move right           --> move cursor one position right
    cursor select right         --> select one position right
    
    cursor move right 10        --> move cursor ten positions right

    cursor move advance_word    --> advance by one word

    cursor select all           --> select all
    '''
        
    if move_select not in ('move', 'select', 'delete'):
        raise errors.UserError("Expected either 'move', 'select', or 'delete' for second argument to 'cursor'.")

    
    curs = bctl.canonical_cursor

    
    # hold anchor cursor if selecting
    if move_select in ('select', 'delete'):
        if bctl.anchor_cursor is None:
            bctl.anchor_cursor = curs.clone()
    else:
        bctl.anchor_cursor = None


    if motion == 'left':
        curs.left(count)
    elif motion == 'right':
        curs.right(count)
    elif motion == 'up':
        curs.up(count)
    elif motion == 'down':
        curs.down(count)
    elif motion == 'advance_word':
        advance_to(curs, advance_word_regex, count)
    elif motion == 'all':
        if move_select != 'select':
            raise errors.UserError('motion "all" only available with motion_type "select".')
        
        bctl.anchor_cursor.move(0,0)
        curs.last_line().end()
    elif motion == 'home':
        curs.home()
    elif motion == 'end':
        curs.end()
    elif motion == 'page_down':
        page_down(bctl, count)
    elif motion == 'page_up':
        page_down(bctl, -count)
    else:
        raise errors.UserError('Unknown motion {!r}'.format(motion))
    
    if move_select == 'delete':
        with bctl.history.transaction():
            bctl.anchor_cursor.remove_to(curs)
            bctl.anchor_cursor = None
    
    bctl.refresh_view(full=False)
