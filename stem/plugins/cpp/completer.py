
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

from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

from . import mp_helpers, worker

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


def get_path_to_clangserver():
    import pathlib
    return pathlib.Path(__file__).parent / 'clangserver.nonpkg'

def find_compilation_db(buffer_file):
    from stem.util.path import search_upwards
    return next(search_upwards(buffer_file, 'compile_commands.json'), None)

@autoextend(BufferController,
            lambda tags: tags.get('syntax') == 'c++')
class CXXCompleter(AbstractCompleter):

    TriggerPattern = re.compile(r'\.|::|->')
    WordChar       = re.compile(r'[\w\d]')

    def __init__(self, buf_ctl):
        super().__init__(buf_ctl)
        self.worker = worker.WorkerManager()
        self.worker.start()
        self.engine = self.worker.SemanticEngine()        
        
        db = find_compilation_db(buf_ctl.path)
        if db is not None:
            self.engine.enroll_compilation_database(str(db.parent))
        


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

    def _request_completions(self):
        line, col = self._start_pos

        @in_main_thread
        def callback(compls):
            try:
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

