
from keypad.core.notification_queue import in_main_thread
from keypad.buffers import Cursor, Span
from keypad.core import Signal
from keypad.core.nconfig import ConfigGroup, Field
from keypad.core.timer import Timer

class DiagnosticsConfig(ConfigGroup):
    _ns_ = 'diagnostics'
    
    enabled = Field(bool, True, safe=True)
    update_period_s = Field(float, 1)

import logging
class DiagnosticsController(object):
    
    def __init__(self, config, code_model, buffer):
        '''
        :type code_model: keypad.abstract.code.AbstractCodeModel
        :type buffer: keypad.buffers.Buffer
        '''
        self.code_model = code_model
        self.buffer = buffer
        self.config = DiagnosticsConfig.from_config(config)
        
        buffer.text_modified.connect(self.__on_buffer_change)
        
        self.clear_attrs = dict(error=None)
        self.default_diag_attrs = dict(error=True)
        self.diagnostics = []
        
        self._overlays = ()
        
        self.__timer = Timer(self.config.update_period_s)
        self.__timer.timeout.connect(self.__tick)
        self.__timer.reset_countdown()
        
#         self.__timer.running = True
#         self.__buffer_modified_yet = False
    
    def __on_buffer_change(self, chg):
#         self.__buffer_modified_yet = True
        self.__timer.reset_countdown()
        
    def __tick(self):
        if self.config.enabled: # and self.__buffer_modified_yet:
            self.update()
            self.__buffer_modified_yet = False
            # suspend timer while performing updates
#             self.__timer.running = False
    
    def update(self):
        try:
            f = self.code_model.diagnostics_async()
        except NotImplementedError:
            pass
        else:
            f.add_done_callback(in_main_thread(self.__update_callback))

    @Signal
    def overlays_changed(self):
        pass

    @property
    def overlays(self):
        return self._overlays

    @staticmethod
    def __make_spans(span, attrs):
        for k, v in attrs.items():
            yield span, k, v
            
    def __update_callback(self, future):
        try:
            result = future.result()
            self.diagnostics = result
            spans = []
            for diag in result:
                for filename, p1, p2 in diag.ranges:
                    if filename == str(self.code_model.path):
                        try:
                            sc = Cursor(self.buffer).move(p1)
                            ec = Cursor(self.buffer).move(p2)
                            spans.extend(self.__make_spans(Span(sc, ec), self.default_diag_attrs))
                        except IndexError:
                            pass
    
            self.__set_overlays(spans)
        except:
            logging.exception('error in __update_callback')
#         finally:
#             self.__timer.running = True
            
    def __set_overlays(self, overlays):
        self._overlays = tuple(overlays)
        self.overlays_changed()
        
        