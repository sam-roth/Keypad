

from ..abstract.code import AbstractCodeModel, AbstractCompletionResults
from ..core.notification_queue import in_main_thread
from ..buffers import Cursor, Span
from .interactive import interactive
from ..core.responder import Responder
from concurrent.futures import CancelledError

import logging

class CompletionController(Responder):
    
    def __init__(self, bufctl):
        '''
        :type bufctl: stem.control.buffer_controller.BufferController
        '''
        super().__init__()
        
        self.bufctl = bufctl
        bufctl.user_changed_buffer.connect(self.__on_user_changed_buffer)
#         bufctl.selection_moved += self.__on_selection_moved
        bufctl.view.completion_view.done.connect(self.__accept_completion)
        bufctl.view.completion_view.row_changed.connect(self.__show_doc)
        
        self.__view = self.bufctl.view
        self.__future = None    
        self.__completions = None
        self.__row = None
    
    def complete(self):
        end_curs = self.bufctl.selection.insert_cursor.clone()
        start_curs = end_curs.clone()
        start_curs.chirality = Cursor.Chirality.Left
          
        
        if self.__future is not None:
            self.__future.cancel()
            self.__future = None
        self.__code_model.path = self.bufctl.path
        self.__future = future = self.__code_model.completions_async(self.bufctl.selection.pos)
        future.add_done_callback(in_main_thread(self.__completion_done))
        
        
    def show_call_tip(self):
        
        @in_main_thread
        def callback(result):
            try:
                self.__view.call_tip_model = result.result()
            except:
                logging.exception('showing call tip')
                self.__view.call_tip_model = None
            
        f = self.__code_model.call_tip_async(self.bufctl.selection.pos)
        f.add_done_callback(callback)
        

    ######################### PRIVATE ########################### 
    
    @property
    def __code_model(self):
        return self.bufctl.code_model
        
    def __completion_done(self, future):
        self.__future = None
        
        try:
            completions = future.result()
#             self.__view.call_tip_model = None
        except CancelledError:
            return
            
        assert isinstance(completions, AbstractCompletionResults)

        self.__completions = completions
        self.__refilter_typed()
        self.__view.show_completions()
        self.__view.completion_view.raise_()
    
    def __show_doc(self, row):
        if self.__completions is None:
            return
            
        try:
            f = self.__completions.doc_async(row)
        except NotImplementedError:
            return
        else:
            f.add_done_callback(in_main_thread(self.__got_docs))
    
    def __got_docs(self, future):
        try:
            self.__view.completion_view.doc_lines = future.result()
        except CancelledError:
            return
            
    def __refilter(self, pattern=''):
        self.__completions.filter(pattern)
        self.__view.completions = self.__completions.rows
    
    def __finish(self):
        if self.__completions is not None:
            self.__completions.dispose()
            
        self.__completions = None
        self.__view.completion_view.visible = False
    
    @property
    def __span(self):
        if self.__completions is not None:
            ic = self.bufctl.selection.insert_cursor
            if ic.pos < self.__completions.token_start:
                self.__finish()
                return None
            
            return Span(
                Cursor(self.bufctl.buffer).move(self.__completions.token_start),
                ic
            )
        else:
            return None
    
    def __on_user_changed_buffer(self, chg):
        if self.bufctl.code_model is not None and chg.insert:
            icurs = self.bufctl.selection.insert_cursor
            line_text = icurs.line.text[:icurs.x]
            
            for trigger in self.bufctl.code_model.completion_triggers:
                if line_text.endswith(trigger):
                    break
            else:
                trigger = None
            
            if trigger is not None:
                if self.__completions is not None:
                    self.__accept_completion(self.bufctl.view.completion_view.current_row,
                                             icurs.x - len(trigger))
                self.complete()
                
            else:
                
                for trigger in self.bufctl.code_model.call_tip_triggers:
                    if line_text.endswith(trigger):
                        break
                else:
                    trigger = None
                
                if trigger is not None:
                    self.show_call_tip()
        elif self.bufctl.code_model is not None and chg.remove\
            and chg.remove in self.bufctl.code_model.call_tip_triggers:
                self.show_call_tip()
        self.__refilter_typed()
#     
#     def __on_selection_moved(self):                        
#         ic = self.bufctl.selection.insert_cursor
#         text_to_curs = ic.line.text[:ic.x]
#         
# 
    
    def __refilter_typed(self):
        span = self.__span
        if span is not None:
            self.__refilter(span.text)

        
    def __accept_completion(self, index, end=None):
        if not (self.__span is None or index is None or
                index >= len(self.__completions.rows) or index < 0):       
            
            with self.bufctl.history.rec_transaction():
                text = self.__completions.text(index)
                
                c = Cursor(self.bufctl.buffer).move(self.__completions.token_start)
                if end is None:
                    e = self.__span.end_curs
                else:
                    e = c.clone().home().right(end)
                c.remove_to(e)
                c.insert(text)
            
        self.__finish()
        
        
@interactive('complete')
def complete(cc: CompletionController):
    cc.complete()

@interactive('calltip')
def calltip(cc: CompletionController):
    cc.show_call_tip()