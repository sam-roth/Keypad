
from stem.core.tag import autoextend
from stem.control import BufferController
from stem.abstract.completion import AbstractCompletionView
from stem.api import interactive
from stem.core.responder import Responder
from stem.core import notification_queue, AttributedString
from stem.control.interactive import dispatcher as interactive_dispatcher
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


from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

from . import mp_helpers, worker, options as cpp_options

try:
    options.LibClangDir
except AttributeError:
    options.LibClangDir = None


in_main_thread = notification_queue.in_main_thread

def _as_posix_or_none(x):
    if x is None:
        return None
    else:
        return x.as_posix()


def find_compilation_db(buffer_file):
    from stem.util.path import search_upwards
    return next(search_upwards(buffer_file, 'compile_commands.json'), None)



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
class CXXCompleter(AbstractCompleter):

    TriggerPattern = re.compile(r'\.|::|->')
    WordChar       = re.compile(r'[\w\d]')

    def __init__(self, buf_ctl):
        super().__init__(buf_ctl)
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
        

    def _start_worker(self):
        self.worker = worker.WorkerManager()
        self.worker.start()

        self.engine = self.worker.SemanticEngine()        

    def __del__(self):
        self.reparse_timer.cancel()
        self.worker.shutdown()

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
            results.append([' '.join(chunks)])
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
        
        bufpath = str(self.buf_ctl.path) if self.buf_ctl.path else 'foo.cpp'

        
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

