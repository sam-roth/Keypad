
from stem.core.tag import autoextend
from stem.control import BufferController
from stem.abstract.completion import AbstractCompletionView
from stem.api import interactive
from stem.core.responder import Responder
from stem.core import notification_queue, AttributedString

from stem.buffers import Span, Cursor
from stem.plugins.semantics.completer import AbstractCompleter

from . import worker
import multiprocessing
import re
import textwrap


def _as_posix_or_none(x):
    if x is None:
        return None
    else:
        return x.as_posix()


@autoextend(BufferController,
            lambda tags: tags.get('syntax') == 'python')
class PythonCompleter(AbstractCompleter):

    TriggerPattern = re.compile(r'\.$')
    WordChar       = re.compile(r'[\w\d]')


    def __init__(self, buf_ctl):
        super().__init__(buf_ctl)

        self.pool = multiprocessing.Pool(processes=1,
                                         initializer=worker.init_worker)

    
    def _request_docs(self, index):
        @notification_queue.in_main_thread
        def callback(result):
            self.show_documentation(result)

        self.pool.apply_async(
            worker.follow_definition,
            [index],
            callback=callback
        )


    def _request_completions(self):
        line, col = self._start_pos
        source = self.buf_ctl.buffer.text

        @notification_queue.in_main_thread
        def callback(result):
            self.show_completions(result)

        self.pool.apply_async(
            worker.complete, 
            [
                source,
                line,
                col,
                _as_posix_or_none(self.buf_ctl.path)
            ],
            callback=callback
        )





