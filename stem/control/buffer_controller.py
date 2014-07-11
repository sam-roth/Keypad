
import logging
import re

import pathlib

from .standard_interaction           import StandardInteractionMode
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
from ..util                     import bifilter
from ..core.notification_queue  import in_main_thread
from ..core                     import timer, filetype
from ..core.nconfig             import Config, KeyWarning
from ..options                  import GeneralConfig

from .completion import CompletionController
import configparser
import fnmatch
import ast
import warnings

class SelectionImpl(BacktabMixin, Selection):
    pass


from .interactive import interactive

def _selection_code_completion_hint(s):
    '''
    Hint to Jedi that the object is a Selection (without actually 
    asserting that it is). It's inelegant, but it works and makes
    the API a bit more friendly.

    :rtype: stem.buffers.selection.Selection
    '''
    return s

class BufferController(Tagged, Responder):
    def __init__(self, buffer_set, view, buff, provide_interaction_mode=True, config=None):
        '''
        :type view: stem.abstract.textview.AbstractTextView
        :type buff: stem.buffers.Buffer
        '''

        super().__init__()

        self.last_canonical_cursor_pos = 0,0
        self._view              = view
        self.buffer             = buff
#         self.view.lines         = self.buffer.lines
        self.view.buffer        = buff
        self.view.keep          = self
        self.__file_mtime       = 0

        self.manipulator        = BufferManipulator(buff)
        self.config             = config or Config.root
        self.view.config        = self.config

        gs = GeneralConfig.from_config(self.config)

        self.general_settings = gs

        selection = _selection_code_completion_hint(gs.selection(self.manipulator, self.config))
        self.selection = selection

        self.completion_controller = CompletionController(self)
        self._code_model = None

        self.manipulator.executed_change    += self.user_changed_buffer
        self.manipulator.executed_change    += self.__on_user_changed_buffer
        buff.text_modified                  += self.buffer_was_changed 
        self.history.transaction_committed  += self._after_history_transaction_committed
        self.history.changes_committed      += self._after_history_changes_committed
        self.selection_moved                += self.scroll_to_cursor
        self.selection.moved                += self.selection_moved
        self.loaded_from_path               += self.__path_change
        self.wrote_to_path                  += self.__path_change
        
        self._diagnostics_controller = None
        self.buffer_set = buffer_set
        self._prev_region = Region()
        self._is_modified = False
        self.__filetype = None
        self.__set_filetype(filetype.Filetype.default())        

        view.controller = self

        if provide_interaction_mode:
            self.interaction_mode = StandardInteractionMode(self)
        else:
            self.interaction_mode = None
            

        self._last_path = None

    def __enter__(self):
        return self

    def __exit__(self, *args, **kw):
        self.dispose()

    def dispose(self):
        if self.code_model is not None:
            self.code_model = None
            
    @Signal
    def selection_moved(self):
        pass
        
    def __set_filetype(self, ft):
        if ft != self.__filetype:
            self.__filetype = ft
            self.add_tags(**ft.tags)
            self.code_model = ft.make_code_model(self.buffer, self.config)
            
            
            
    def __path_change(self, path):
        if path != self._last_path:
            self._last_path = path
        else:
            return
        
        if path is None:
            self.__set_filetype(filetype.Filetype.default())
        else:
            self.__set_filetype(filetype.Filetype.by_suffix(pathlib.Path(path).suffix))
        
        if self.code_model is not None:
            self.code_model.path = self.path
        
        
        config_path = next(search_upwards(path, '.stemdir.yaml'), None)
        if config_path is not None:
            with config_path.open('rb') as f:
                self.config.load_yaml_safely(f)
            logging.debug('loaded file config from %r, indent text is %r', config_path, 
                GeneralConfig.from_config(self.config).indent_text)
                
        self.path_changed()
        
    @property
    def code_model(self):
        '''
        Return the code model associated with the buffer

        :rtype: stem.abstract.code.AbstractCodeModel
        '''
        return self._code_model

    @code_model.setter
    def code_model(self, value):
        if self._code_model is not None:
            self.remove_next_responders(self.completion_controller)
            dc = self._diagnostics_controller
            if dc is not None:
                dc.overlays_changed.disconnect(
                    self.__on_diagnostic_overlay_change)
                self.view.set_overlays('diagnostics', [])

            self._diagnostics_controller = None
            self._code_model.dispose()

        self._code_model = value
        self.buffer.code_model = value
        
        
        if self._code_model is not None:
            self._code_model.path = self.path
            self.add_next_responders(self.completion_controller)
            if self._code_model.can_provide_diagnostics:
                dc = DiagnosticsController(self.config, self._code_model, self.buffer)
                dc.overlays_changed.connect(self.__on_diagnostic_overlay_change)
                self._diagnostics_controller = dc
                
    def __on_diagnostic_overlay_change(self):
        self.view.set_overlays('diagnostics', self._diagnostics_controller.overlays)
        
    def __on_user_changed_buffer(self, chg):
        if self.code_model is None:
            return

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

    def _after_history_transaction_committed(self):
        self.refresh_view()

    def _after_history_changes_committed(self):
        self.is_modified = True


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


    @path.setter
    def path(self, value):
        self.add_tags(path=value)
        self.loaded_from_path(value)

    def clear(self):
        '''
        Remove all text from `self.buffer`.

        Requires an active history transaction.
        '''
        start = Cursor(self.buffer)
        end = Cursor(self.buffer).move(*self.buffer.end_pos)
        start.remove_to(end)

    def append_from_path(self, path, *, codec_errors='strict'):
        '''
        Append the contents of `self.buffer` with the contents of the file
        located at `path` decoded using UTF-8.

        Requires an active history transaction.
        '''
        with path.open('rb') as f:
            (Cursor(self.buffer)
             .move(*self.buffer.end_pos)
             .insert(f.read().decode(errors=codec_errors)))

    def replace_from_path(self, path, create_new=False, *, codec_errors='strict'):
        '''
        Replace the contents of `self.buffer` with the contents of the
        file located at `path` decoded using UTF-8. 

        Requires an active history transaction.
        '''

        self.clear()
        try:
            self.append_from_path(path, codec_errors=codec_errors)
        except FileNotFoundError:
            if not create_new:
                raise

        self.add_tags(path=path)
        self.is_modified = True

        self.canonical_cursor.move(0,0)

        self.loaded_from_path(path)

    def write_to_path(self, path, *, codec_errors='strict'):
        '''
        Atomically write the contents of `self.buffer` to the file located
        at `path` encoded with UTF-8.
        '''
        # save the selection position, since it will be moved if it's on top of a scratchpad
        # change
        # TODO: disable screen updates when suppressing the scratchpad
        sel = self.selection.pos
        try:
            self.will_write_to_path(path)
            with write_atomically(path) as f:
                with self.history.suppress_scratchpad():
                    f.write(self.buffer.text.encode(errors=codec_errors))

        finally:
            self.selection.pos = sel
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
    def path_changed(self):
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
        
        # update selection
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


        self.view.set_overlays('selection', overlay_spans)
        self.view.set_overlays('matched_brace', [])



        # update matched braces
        if self.code_model is not None:
            timeout = self.general_settings.brace_match_timeout_ms
            try:
                lchar = curs.lchar
                rchar = curs.rchar
                open_cursor, close_cursor = None, None
                if rchar in self.code_model.close_braces:
                    close_cursor = curs.clone()
                    open_cursor = curs.clone().opening_brace(timeout_ms=timeout)
                elif lchar in self.code_model.close_braces:
                    close_cursor = curs.clone().left()
                    open_cursor = close_cursor.clone().opening_brace(timeout_ms=timeout)
                elif rchar in self.code_model.open_braces:
                    open_cursor = curs.clone()
                    close_cursor = curs.clone().closing_brace(timeout_ms=timeout)
                elif lchar in self.code_model.open_braces:
                    open_cursor = curs.clone().left()
                    close_cursor = open_cursor.clone().closing_brace(timeout_ms=timeout)
                if open_cursor is not None:
                    spans = []
                    spans.append(Span(open_cursor.clone(), open_cursor.clone().right()))
                    spans.append(Span(close_cursor.clone(), close_cursor.clone().right()))
                    overlays = []
                    for span in spans:
                        overlays += [
                            (span, 'sel_color', 'auto'),
                            (span, 'sel_bgcolor', 'auto')
                        ]

                    self.view.set_overlays('matched_brace', overlays)
            except (RuntimeError, IndexError):
                pass
        
#         if full:
#             self.view.full_redraw()
#         else:
#             self.view.partial_redraw()


    @in_main_thread
    # defer this until later in the event loop, since final scroll position
    # position is hysteretic (path dependent)
    def scroll_to_cursor(self, *, center=False):
        curs = self.selection.insert_cursor

        if self.view.scroll_to_line(curs.pos[0], center=center):
            self.refresh_view()

#
#         curs = self.selection.insert_cursor
#         if self.view.start_line > curs.pos[0]:
#             self.view.scroll_to_line(curs.pos[0])
#         elif self.view.start_line + self.view.buffer_lines_visible <= curs.pos[0]:
#             self.view.scroll_to_line(curs.pos[0] - self.view.buffer_lines_visible + 1)
#             
        
from ..abstract.application import app


@interactive('previous_cursor_position')
def previous_cursor_position(bc: BufferController):
    bc.selection.to_previous_position()
    bc.refresh_view()

@interactive('next_cursor_position')
def next_cursor_position(bc: BufferController):
    bc.selection.to_next_position()
    bc.refresh_view()
    
@interactive('line')
def goto_line(bc: BufferController, line):
    bc.selection.move(line=int(line))
    bc.view.scroll_to_line(int(line), center=True)
    bc.refresh_view()

@interactive('open_brace')
def open_brace(bctl: BufferController):
    with bctl.selection.moving():
        bctl.selection.insert_cursor.opening_brace(timeout_ms=1000)
    bctl.refresh_view()

@interactive('close_brace')
def close_brace(bctl: BufferController):
    with bctl.selection.moving():
        bctl.selection.insert_cursor.closing_brace(timeout_ms=1000)
    bctl.refresh_view()
    
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
    cs = buff.history.undo()
    if cs:
        y, x = cs[-1].pos
        try:
            buff.selection.move(line=y)
            buff.selection.home().right(x)
        except IndexError:
            pass
        buff.refresh_view()


@interactive('redo')
def redo(buff: BufferController):
    cs = buff.history.redo()
    if cs:
        buff.selection.move(cs[-1].pos)
        buff.refresh_view()



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


def set_specific_config(target, key, value):
    from stem.util import dotted_pairs_to_dict
    d = dotted_pairs_to_dict([(key, ast.literal_eval(value))])
    with warnings.catch_warnings(record=True) as warns:
        target.update(d, safe=False)

    key_warnings, other_warnings = bifilter(lambda x: isinstance(x.message, KeyWarning), warns)

    for warn in other_warnings:
        warnings.warn(w.message)

    if key_warnings:
        raise errors.UserError('The following config keys were not found: ' +
                               ', '.join(str(w.message.args[0]) for w in key_warnings))
        

@interactive('setg')
def setg_config(_: object, key, *val):
    set_specific_config(Config.root, key, ' '.join(val))


@interactive('set')
def set_config(bufctl: BufferController, key, *val):
    set_specific_config(bufctl.config, key, ' '.join(val))

@interactive('get')
def get_config(bufctl: BufferController, namespace, key):
    import pprint
    fmt = pprint.pformat(bufctl.config.get(namespace, key))
    
    from .command_line_interaction import writer
    
    writer.write(fmt)

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
            fallback = None
            for result in results:
                if result.path is not None:
                    fallback = result
                    if result.type & ty:
                        break
            else:
                if fallback is not None:
                    result = fallback
                elif results:
                    result = results[0]
                else:
                    raise errors.NameNotFoundError('Could not find name.')
            
            assert isinstance(result, RelatedName)
            y, x = result.pos
            interactive.run('edit', str(result.path), y + 1)
            bc.refresh_view(full=True)
            
        f.add_done_callback(callback)




from stem.abstract.code import Diagnostic, AbstractCallTip


class SimpleCallTip(AbstractCallTip):
    def __init__(self, tip):
        super().__init__()
        self.tip = tip
        
    def to_astring(self, _=None):
        return self.tip


@interactive('show_diagnostics')
def show_diagnostics(bc: BufferController):
    assert isinstance(bc, BufferController)

    
    if bc._diagnostics_controller is None:
        return interactive.call_next
    
    for diag in bc._diagnostics_controller.diagnostics:
        assert isinstance(diag, Diagnostic)
        for f, p1, p2 in diag.ranges:
            if p1 is not None and p1[0] == bc.selection.pos[0]:
                bc.view.call_tip_model = SimpleCallTip(AttributedString(diag.text))
    
#     bc._diagnostics_controller.update()
    
    
#     diags = bc.code_model.diagnostics_async().result()
    
#     for diag in diags:
#         print(diag)


