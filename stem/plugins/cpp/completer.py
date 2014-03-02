
from stem.core.tag import autoextend
from stem.control import BufferController
from stem.abstract.completion import AbstractCompletionView
from stem.api import interactive
from stem.core.responder import Responder
from stem.core import notification_queue, AttributedString, errors
from stem.control.interactive import dispatcher as interactive_dispatcher, run as run_interactive
from stem import options
from stem.buffers import Span, Cursor
from stem.plugins.semantics.completer import AbstractCompleter

import logging
import multiprocessing.dummy
import subprocess
import re
import textwrap
import time
import threading
import pathlib


from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

from . import mp_helpers, worker, options as cpp_options

_KindNames = {
    'CXX_METHOD': AttributedString('method', lexcat='function'),
    'FUNCTION_DECL': AttributedString('function', lexcat='function'),
    'FUNCTION_TEMPLATE': AttributedString('function template', lexcat='function'),
    'DESTRUCTOR': AttributedString('destructor', lexcat='function'),
    'CONSTRUCTOR': AttributedString('constructor', lexcat='function'),
    'PARM_DECL': AttributedString('argument', lexcat='docstring'),
    'FIELD_DECL': AttributedString('field', lexcat='docstring'),
    'VAR_DECL': AttributedString('variable', lexcat='docstring'),
    'ENUM_CONSTANT_DECL': AttributedString('variable', lexcat='docstring'),
    'CLASS_DECL': AttributedString('class', lexcat='type'),
    'STRUCT_DECL': AttributedString('struct', lexcat='type'),
    'CLASS_TEMPLATE': AttributedString('class template', lexcat='type'),
    'TYPEDEF_DECL': AttributedString('typedef', lexcat='type'),
    'NAMESPACE': AttributedString('namespace', lexcat='preprocessor'),
    'MACRO_DEFINITION': AttributedString('macro', lexcat='preprocessor'),
    'NOT_IMPLEMENTED': AttributedString('not implemented', italic=True, lexcat='comment')
}

def _kind_name(clang_name):
    return _KindNames.get(clang_name, clang_name)

try:
    options.LibClangDir
except AttributeError:
    options.LibClangDir = None

def _common_prefix_len(xs, ys):
    i=0
    for i, (x, y) in enumerate(zip(xs, ys)):
        if x != y:
            return i
    else:
        return i + 1

in_main_thread = notification_queue.in_main_thread

def _as_posix_or_none(x):
    if x is None:
        return None
    else:
        return x.as_posix()


def find_compilation_db(buffer_file):
    from stem.util.path import search_upwards
    return next(search_upwards(pathlib.Path(buffer_file).absolute(), 'compile_commands.json'), None)



class RepeatingTimer(threading.Thread):
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self._cancelled = threading.Event()
        super().__init__(daemon=True)
    
    def cancel(self):
        self._cancelled.set()

    def run(self):
        while True:
            self._cancelled.wait(self.interval)
            if self._cancelled.is_set():
                break
            else:
                self.callback()


@autoextend(BufferController,
            lambda tags: tags.get('syntax') == 'c++')
class CXXCompleter(AbstractCompleter, Responder):

    TriggerPattern = re.compile(r'\.|::|->')
    WordChar       = re.compile(r'[\w\d]')

    def __init__(self, buf_ctl):
        super().__init__(buf_ctl)
        self.config = self.buf_ctl.config
        self._has_shut_down = False
        buf_ctl.add_next_responders(self)
        self._start_worker()
        self._worker_crashes = 0
        
        @in_main_thread
        def reparse_callback():
            self._request_diagnostics()
            self.buf_ctl.refresh_view()

        self.reparse_timer = RepeatingTimer(cpp_options.ReparseEveryXSeconds, reparse_callback)
        self.reparse_timer.start()
        
        db = find_compilation_db(buf_ctl.path)
        if db is not None:
            self.engine.enroll_compilation_database(str(db.parent))
    
        buf_ctl.closing.connect(self._shutdown)
        
    
    
    def _sort_completions(self, key, completions):
        completions = list(completions)
        completions.sort(key=lambda c: -_common_prefix_len(c[1][0], key))
        return completions        
                
        
    
    def _start_worker(self):
        self.worker = worker.WorkerManager()
        self.worker.start()

        self.engine = self.worker.SemanticEngine(self.config)

    def _shutdown(self):
        if not self._has_shut_down:
            self._has_shut_down = True
            logging.debug('Terminating completion worker')
            self.reparse_timer.cancel()
            self.worker.shutdown()
            

    def __del__(self):
        self._shutdown()
        
    @staticmethod
    def __convert_compl_results(completions):
        results = []
        doc = []
        for completion in completions:
            chunks = []
            doc_chunks = []
            for chunk in completion.get('chunks', []):
                if chunk.get('kind') == 'TypedText':
                    chunks.append(chunk.get('spelling', ''))
                
                doc_chunks.append(chunk.get('spelling', ''))

            doc_chunks.append('\n\n')

            if 'brief_comment' in completion:
                doc_chunks.append(str(completion['brief_comment']))
            results.append([' '.join(chunks), 
                _kind_name(completion.get('kind'))])
            doc.append(' '.join(doc_chunks))
        
        return results, doc

    def _show_diagnostics(self, diags):
        
        diag_lines = {}

        for diag in diags:
            filename, (line, col) = diag['location']
            diag_lines[line] = diag

        for i, line in enumerate(self.buf_ctl.buffer.lines):
            diag = diag_lines.get(i + 1)
            if diag is not None:
                line.set_attributes(0, None, error=True, tooltip=diag['spelling'])
            else:
                line.set_attributes(0, None, error=False)
        

    def _request_diagnostics(self):

        @in_main_thread
        def callback(results):
            try:
                self._show_diagnostics(results)
            except:
                logging.exception('exception showing diagnostics')
        
        bufpath = str(self.buf_ctl.path) if self.buf_ctl.path else 'foo.cpp'
    
        try:
            self.engine.check_living()
            mp_helpers.call_async(
                callback,
                self.engine.reparse_and_get_diagnostics,
                bufpath,
                [(bufpath, self.buf_ctl.buffer.text)]
            )
        except IOError:
            from stem.control.interactive import run
            if self._worker_crashes == 0:
                run('show_error', 'Code completion worker crash.')
                self._has_shown_error = True
            
            if self._worker_crashes < 4:
                self._start_worker()
            elif self._worker_crashes == 4:
                run('show_error', 'Too many worker crashes.')
                self.reparse_timer.cancel()
                
            self._worker_crashes += 1

    @property
    def fakepath(self):
        return str(self.buf_ctl.path) if self.buf_ctl.path else '__foo__.cpp'


    def _request_completions(self):
        line, col = self._start_pos

        @in_main_thread
        def callback(results):
            try:
                compls = results
                conv_compls, doc = self.__convert_compl_results(compls)
                self.__doc = doc
                self.show_completions(conv_compls)
            except:
                logging.exception('exception in c++ completion')
        
        bufpath = self.fakepath

        
        mp_helpers.call_async(
            callback,
            self.engine.completions,
            bufpath,
            line+1,
            col+1,
            [(bufpath, self.buf_ctl.buffer.text)]
        )


    def _request_docs(self, index):
        if self.__doc is not None:
            self.show_documentation([self.__doc[index]])


@interactive('restart_completer')
def restart_completer(comp: CXXCompleter):
    if comp._worker_crashes >= 4:
        comp._worker_crashes = 0
        comp._start_worker()


@interactive('find_definition')
def find_definition(comp: CXXCompleter):
    line, col = comp.buf_ctl.canonical_cursor.pos
    path = comp.fakepath
    
    @in_main_thread
    def callback(results):
        try:
            if results:
                file, line, col = results
                if comp.buf_ctl.path != pathlib.Path(file) and file != path:
                    run_interactive('edit', file, line, col)
                else:
                    comp.buf_ctl.selection.move(line-1, col-1)
                    comp.buf_ctl.scroll_to_cursor()
                    comp.buf_ctl.refresh_view()
        except:
            logging.exception('error trying to find definition')
            
    
    mp_helpers.call_async(
        callback,
        comp.engine.find_definition,
        path,
        line+1,
        col+1,
        [(path, comp.buf_ctl.buffer.text)]
    )
    
    
    
    