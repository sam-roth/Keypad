from codeedit.core.tag import autoextend
from codeedit.control import BufferController
from codeedit.abstract.completion import AbstractCompletionView
from codeedit.api import interactive
from codeedit.core.responder import Responder
from codeedit.core import notification_center, AttributedString
from codeedit.buffers import Span, Cursor
from codeedit.control import colors

import re
import textwrap

import abc

def make_fuzzy_pattern(pattern):
    expr = '.*?' + '.*?'.join(map(re.escape, pattern.lower()))
    return re.compile(expr)


class AbstractCompleter(Responder, metaclass=abc.ABCMeta):
    '''
    The only private methods subclassers need to care about here are
    
    * :py:meth:`._request_completions()`
    * :py:meth:`._request_docs()`


    .. automethod:: _request_completions
    .. automethod:: _request_docs
    '''

    def __init__(self, buf_ctl):
        super().__init__()
        self._start_pos = None
        cview = self.cview = buf_ctl.view.completion_view
        buf_ctl.add_tags(completer=self)
        self.buf_ctl = buf_ctl

        buf_ctl.add_next_responders(self)

        buf_ctl.user_changed_buffer.connect(self._after_user_changed_buffer)
        cview.row_changed.connect(self._after_row_change)
        cview.done.connect(self._on_completion_done)
        self._selected_index = 0
    

    @abc.abstractmethod
    def _request_completions(self):
        '''
        Called when the subclass should start the completion process.
        
        '''
        ...

    @abc.abstractmethod
    def _request_docs(self, index):
        '''
        Called when documentation is requested for the completion at a given
        index. The index is into the most recently provided completion list.
        '''
        ...

    def _finish_completion(self, index):
        cs = self.completion_span
        cs.set_attributes(sel_bgcolor=None, sel_color=None)
        text = self.cview.completions[index][0]
        cs.start_curs.remove_to(cs.end_curs)
        
        Cursor(self.buf_ctl.buffer)\
            .move(*cs.start_curs.pos)\
            .insert(text)

        self._start_pos = None

    def _after_user_changed_buffer(self, change):
        match = self.TriggerPattern.search(change.insert)
        if match is not None:
            trigger_text = match.group(0)
            if self._start_pos is not None:
                self._finish_completion(self._selected_index)

                # The trigger gets wiped out by the completion, so put it back.
                Cursor(self.buf_ctl.buffer)\
                    .move(*self.buf_ctl.canonical_cursor.pos)\
                    .insert(trigger_text)
                
            self.complete()

        cs = self.completion_span
        if cs is not None:
            self.refilter_typed()
            #cs.set_attributes(
            #    sel_bgcolor=colors.scheme.search_bg,
            #    sel_color=colors.scheme.bg
            #)
        
    def _on_completion_done(self, index):
        cs = self.completion_span
        if index is None:
            self._start_pos = None
        elif cs is not None:
            with self.buf_ctl.history.transaction():
                self._finish_completion(index)

    def _after_row_change(self, comp_idx):
        self._selected_index = comp_idx
        self._request_docs(self._worker_indices[comp_idx])

    def _find_start(self):
        start_curs = self.buf_ctl.canonical_cursor.clone()
        line, col = start_curs.pos

        for idx, ch in enumerate(reversed(start_curs.line.text[:col])):
            if self.WordChar.match(ch) is None:
                start_curs.left(idx)
                break
        else:
            start_curs.home()

        return start_curs


    @staticmethod
    def format_docs(docs, width):
        # Docs is a list of strings. No paragraph in docs is split across
        # strings. Some strings have more than one paragraph. To normalize this
        # input, merge the paragraphs using join, then split them again.

        paragraphed_text = '\n\n'.join(docs)
        paragraphs       = paragraphed_text.split('\n\n')
        
        wrapped = '\n'.join(
            textwrap.fill(
                para,
                width=width - 3,
                fix_sentence_endings=True,
                subsequent_indent='  '
            )
            for para in paragraphs
        )

        return wrapped


    def show_documentation(self, docs):
        _, width = self.cview.doc_view.plane_size
        formatted_docs = self.format_docs(docs, width)
        self.cview.doc_view.lines = [AttributedString(r) for r in formatted_docs.splitlines()]        
        self.cview.doc_view.full_redraw()

    def show_completions(self, completions):
        self.completions = completions
        self.refilter_typed()
        self.buf_ctl.view.show_completions()

    def refilter(self, typed_text):
        pattern = make_fuzzy_pattern(typed_text)
        
        # Sort the completions by length ascending, adding explicit indices to
        # the completions so that they may be referenced later.

        sorted_pairs = sorted(((i,t) for (i,t) in enumerate(self.completions)
                               if pattern.match(t[0].lower()) is not None),
                              key=lambda x: len(x[1][0]))
        
        
        # Split off the indices and keep them as a mapping between completion
        # view index and worker index.
        if sorted_pairs:
            indices, completions = zip(*sorted_pairs)
        else:
            indices, completions = [], []

        
        self._worker_indices = indices
        self.cview.completions = completions
        
    @property
    def completion_span(self):
        if self._start_pos is None:
            return None
        else:
            try:
                # Use a copy of the canonical cursor, because the canonical
                # cursor is associated with the buffer manipulator rather than
                # the buffer. This means that it is technically invalid to use
                # canonical_cursor.text_to(Cursor(buffer).move(12,33)), for
                # instance.

                start_curs = self.buf_ctl.canonical_cursor.clone()\
                        .move(*self._start_pos)
                span = Span(start_curs, self.buf_ctl.canonical_cursor)
            except IndexError:
                self._start_pos = None
                return None
            else:
                return span
                               
    def refilter_typed(self):
        cs = self.completion_span
        if cs is not None:
            self.refilter(cs.text)
                
    def complete(self):
        self._start_pos = self._find_start().pos

        source = self.buf_ctl.buffer.text
        line, col = self._start_pos


        self._request_completions()


            
@interactive('complete')
def run_completion(completer: AbstractCompleter):
    completer.complete()
