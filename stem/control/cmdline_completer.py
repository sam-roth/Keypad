from stem.core.tag import autoextend
from stem.control import BufferController
from stem.abstract.completion import AbstractCompletionView
from stem.api import interactive
from stem.core.responder import Responder
from stem.core import notification_queue, AttributedString
from stem.control.interactive import dispatcher

from stem.buffers import Span, Cursor
from stem.plugins.semantics.completer import AbstractCompleter
from stem.abstract.application import app
import multiprocessing
import re
import textwrap

import pathlib
import shlex
import inspect
import logging
import itertools
import os.path
import collections
def _expand_user(p):
    return pathlib.Path(os.path.expanduser(str(p)))

def _as_posix_or_none(x):
    if x is None:
        return None
    else:
        return x.as_posix()


def _get_directory_contents_rec(path):
    queue = collections.deque()
    path = pathlib.Path(path)

    queue.appendleft(path)    
    while queue:
        item = queue.pop()
        for subitem in item.iterdir():
            if subitem.is_dir():
                queue.appendleft(subitem)
            yield subitem

    
class CmdlineCompleter(AbstractCompleter):

    TriggerPattern = re.compile(r'^')
    WordChar       = re.compile(r'\S')


    def __init__(self, buf_ctl):
        super().__init__(buf_ctl)
        self.__compcat = None

    def _request_docs(self, index):
        comp = self.completions[index]
        if self.__compcat == 'Interactive':
            docs = []
            for ty, handler in dispatcher.find_all(comp[0]):
                doc = inspect.getdoc(handler)
                if doc:
                    docs.append(doc)

            self.show_documentation(docs)
        

    def _request_completions(self):
        imode = self.buf_ctl.interaction_mode
        line, col = self._start_pos
        current_cmdline = imode.current_cmdline[:col-imode.cmdline_col]


        tokens = list(shlex.shlex(current_cmdline))
        
        if len(tokens) == 0:
            # complete interactive command name
            self.show_completions([(iname, ) for iname in dispatcher.keys()])
            self.__compcat = 'Interactive'
            
        else:
            # complete argument
            ty, resp, handler = dispatcher.find(app(), tokens[0])
            spec = inspect.getfullargspec(handler)
            annots = [spec.annotations.get(arg) for arg in spec.args]

            if len(tokens) < len(annots):
                category = annots[len(tokens)]
                self.__compcat = category
                if category == 'Path':
                    typed_rootpath = imode.current_cmdline[col-imode.cmdline_col:]
                    rootpath = _expand_user(typed_rootpath)
                    if not rootpath.is_dir():
                        rootpath = rootpath.parent
                        typed_rootpath = os.path.join(*(os.path.split(typed_rootpath)[:-1]))
                    
                    limited_glob = itertools.islice(((os.path.join(typed_rootpath, 
                                                                   str(p.relative_to(rootpath))),)
                                                     for p in _get_directory_contents_rec(rootpath)),
                                                    1024)
                    
                    limited_glob = list(limited_glob)
                    self.show_completions(list(limited_glob))
                elif category == 'Interactive':
                    self.show_completions([(iname, ) for iname in dispatcher.keys()])