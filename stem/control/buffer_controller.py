
import logging
import re

import pathlib

from .cua_interaction           import CUAInteractionMode
from .diagnostics               import DiagnosticsController
from ..                         import util
from ..buffers                  import ModifiedCursor, Cursor, BufferManipulator, Buffer, Span, Region
from ..buffers.selection        import Selection, BacktabMixin
from ..core                     import AttributedString, errors, Signal, write_atomically, color, conftree
from ..core.tag                 import Tagged, autoconnect
from ..core.attributed_string   import lower_bound
from ..core.key                 import *
from ..core.responder           import Responder
from ..util.path                import search_upwards
from ..core.notification_queue  import in_main_thread
from ..core                     import timer
from ..core.nconfig             import Config
from ..options                  import GeneralConfig

from .completion import CompletionController
import configparser
import fnmatch
import ast

class SelectionImpl(BacktabMixin, Selection):
    pass


from .interactive import interactive

class BufferController(Tagged, Responder):
    def __init__(self, buffer_set, view, buff, provide_interaction_mode=True, config=None):
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
        self.__file_mtime       = 0

        self.manipulator        = BufferManipulator(buff)
        self.config             = config or Config.root
        self.view.config        = self.config
        
        self.selection          = SelectionImpl(self.manipulator)        
        self._code_model = None
        
        self.view.scrolled                  += self._on_view_scrolled      
        self.manipulator.executed_change    += self.user_changed_buffer
        self.manipulator.executed_change    += self.__on_user_changed_buffer
        buff.text_modified                  += self.buffer_was_changed 
        buff.text_modified                  += self._after_buffer_modification
        self.history.transaction_committed  += self._after_history_transaction_committed
        self.view.closing                   += self.closing
        self.selection.moved                += self.scroll_to_cursor
        self.wrote_to_path                  += self.__update_file_mtime
        self.loaded_from_path               += self.__update_file_mtime
        self.loaded_from_path               += self.__path_change
        self.wrote_to_path                  += self.__path_change
        self.closing                        += self.__on_closing
        
        self._diagnostics_controller = None
        self.buffer_set = buffer_set
        self._prev_region = Region()
        self._is_modified = False

        view.controller = self

        if provide_interaction_mode:
            self.interaction_mode = CUAInteractionMode(self)
        else:
            self.interaction_mode = None
            

        self.instance_tags_added.connect(self.__after_tags_added)
        
        self.__file_change_timer = timer.Timer(5)
        self.__file_change_timer.timeout += self.__check_for_file_change
        self.completion_controller = CompletionController(self)        
    
    def __path_change(self, path):
        if self.code_model is not None:
            self.code_model.path = self.path
    
    @property
    def code_model(self):
        return self._code_model
        
    @code_model.setter
    def code_model(self, value):
        if self._code_model is not None:
            self.remove_next_responders(self.completion_controller)
            dc = self._diagnostics_controller
            if dc is not None:
                dc.overlays_changed.disconnect(
                    self.__on_diagnostic_overlay_change)
                try:
                    del self.view.overlay_spans['diagnostics']
                except KeyError:
                    pass
                    
            self._diagnostics_controller = None
            
        self._code_model = value
        
        if self._code_model is not None:
            self.add_next_responders(self.completion_controller)
            if self._code_model.can_provide_diagnostics:
                dc = DiagnosticsController(self.config, self._code_model, self.buffer)
                dc.overlays_changed.connect(self.__on_diagnostic_overlay_change)
                self._diagnostics_controller = dc
                
    def __on_diagnostic_overlay_change(self):
        self.view.overlay_spans['diagnostics'] = self._diagnostics_controller.overlays
        
    def __on_user_changed_buffer(self, chg):
        if self.code_model is not None and chg.insert.endswith('\n'):
            curs = self.selection.insert_cursor.clone().home()
            m = curs.searchline('^\s*$')
            if m:
                curs.remove_to(curs.clone().end())
                curs.insert(
                    GeneralConfig.from_config(self.config).indent_text
                    * self.code_model.indent_level(curs.y)
                )

                #curs.insert(self.config.TextView.get('IndentText', '    ', str) 
                #    * self.code_model.indent_level(curs.y))
        
    def __check_for_file_change(self):
        if not self.path:
            self.__file_change_timer.running = False
            return
            
        mtime = pathlib.Path(self.path).stat().st_mtime    
        
        if mtime > self.__file_mtime:
            logging.warning('file modified')
            result = self.view.run_modified_warning(self.is_modified)
            
            if result == 'reload':
                with self.history.rec_transaction():
                    self.replace_from_path(self.path)
            
            
        
        self.__file_mtime = mtime
        
    
    
    def __update_file_mtime(self, *dummy):
        if self.path:
            self.__file_change_timer.running = True
            self.__file_mtime = pathlib.Path(self.path).stat().st_mtime
        else:
            self.__file_change_timer.running = False
    
            
    
    def __on_closing(self):
        # remove all extensions from this object to ensure that its refcount goes to zero
        self.extensions.clear()
        self.remove_tags(list(self.tags))
        if self.code_model is not None:
            self.code_model.dispose()
        

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

        if self.code_model is not None:
            self.code_model.highlight()
        else:
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

    
    @in_main_thread
    # defer this until later in the event loop, since final scroll position
    # position is hysteretic (path dependent)
    def scroll_to_cursor(self):
        curs = self.selection.insert_cursor
        if self.view.start_line > curs.pos[0]:
            self.view.scroll_to_line(curs.pos[0])
        elif self.view.start_line + self.view.buffer_lines_visible <= curs.pos[0]:
            self.view.scroll_to_line(curs.pos[0] - self.view.buffer_lines_visible + 1)
            
        
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
            buff.selection.replace('')


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
    os.chdir(os.path.expanduser(str(newdir)))

    getpwd(r)

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


@interactive('set')
def set_config(bufctl: BufferController, key, *val):
    bufctl.config.set_property(key, ast.literal_eval(' '.join(val)))

@interactive('pdb')
def runpdb(bufctl: BufferController):
    import pdb
    from PyQt4.QtCore import pyqtRemoveInputHook
    pyqtRemoveInputHook()
    pdb.set_trace()

@interactive('dumpdecl')
def dumpdecl(bc: BufferController):
    cm = bc.code_model
    res = cm.find_related_async(bc.selection.pos, cm.RelatedNameType.all)
    print(res.result())

from ..abstract.code import AbstractCodeModel, RelatedName

@interactive('find_definition')
def find_definition(bc: BufferController):
    return goto_related(bc, RelatedName.Type.defn)
    
@interactive('find_declaration')
def find_definition(bc: BufferController):
    return goto_related(bc, RelatedName.Type.decl)
    
def goto_related(bc: BufferController, ty):
    if bc.code_model is None:
        return interactive.call_next
    else:
        cm = bc.code_model
        assert isinstance(cm, AbstractCodeModel)
        f = cm.find_related_async(bc.selection.pos, RelatedName.Type.all)
        
        @in_main_thread
        def callback(future):
            results = future.result()
            for result in results:
                if result.type == ty:
                    break
            else:
                if results:
                    result = results[0]
                else:
                    raise errors.NameNotFoundError('Could not find name.')
            
            assert isinstance(result, RelatedName)
            y, x = result.pos
            interactive.run('edit', str(result.path), y + 1)
            bc.refresh_view(full=True)
            
        f.add_done_callback(callback)



@interactive('show_diagnostics')
def show_diagnostics(bc: BufferController):
    assert isinstance(bc, BufferController)
    
#     if bc._diagnostics_controller is None:
#         return interactive.call_next
        
    
    bc._diagnostics_controller.update()
    
    
#     diags = bc.code_model.diagnostics_async().result()
    
#     for diag in diags:
#         print(diag)