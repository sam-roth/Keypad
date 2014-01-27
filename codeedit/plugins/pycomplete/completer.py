
from codeedit.core.tag import autoextend
from codeedit.control import BufferController
from codeedit.abstract.completion import AbstractCompletionView
from codeedit.api import interactive
from codeedit.core.responder import Responder
from codeedit.core import notification_center, AttributedString

from codeedit.buffers import Span, Cursor
from codeedit.plugins.semantics.completer import AbstractCompleter

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
        @notification_center.via_notification_center
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

        @notification_center.via_notification_center
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





