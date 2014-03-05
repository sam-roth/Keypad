
from .signal import Signal
from ..abstract.application import app
import functools


class Timer(object):
    def __init__(self, interval_sec):
        self.interval = interval_sec
        self._running = False
        
    @Signal
    def timeout(self):
        pass
    
    def _tick(self):
        if self.running:
            self.timeout()

        if self.running: # field might be changed by signal handler
            self._schedule()

    def _schedule(self):
        app().timer(self.interval, self._tick)      
        
    @property
    def running(self):
        return self._running
        
    @running.setter
    def running(self, val):
        if val and not self._running:
            self._schedule()
        self._running = val
            
    
#                    
# def timer(sec):
#     def result(func):
#         t = Timer(sec)
#         t.func = func
#         t.timeout.connect(func)
#         return t
#     return result
#         
        