import re, textwrap, pathlib, shlex, inspect
import logging, itertools, os.path, collections

from stem.util import time_limited
from stem.control.buffer_controller import BufferController
from stem.abstract.completion import AbstractCompletionView
from stem.api import interactive, app, Span, Cursor
from stem.plugins.semantics.completer import AbstractCompleter
from stem.control.interactive import dispatcher
from stem.core import errors

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
        try:
            for subitem in item.iterdir():
                if subitem.is_dir():
                    queue.appendleft(subitem)
                yield subitem
        except PermissionError:
            pass

    
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
        try:
            self._get_completions()
        except errors.UserError as exc:
            interactive.run('show_error', exc)

    def _get_completions(self):
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
                        if not rootpath.exists() or typed_rootpath.endswith(os.path.sep):
                            raise errors.NoSuchFileError('%s does not exist.' % typed_rootpath)
                        typed_rootpath = os.path.join(*(os.path.split(typed_rootpath)[:-1]))


                    def completion_generator():
                        for p in _get_directory_contents_rec(rootpath):
                            yield (os.path.join(typed_rootpath,
                                                str(p.relative_to(rootpath))),)


                    limited_glob = list(time_limited(completion_generator(), ms=250))
                    self.show_completions(limited_glob)
                elif category == 'Interactive':
                    self.show_completions([(iname, ) for iname in dispatcher.keys()])
