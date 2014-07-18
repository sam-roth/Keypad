
from .signal import Signal
from ..abstract.application import app
import functools


class _Tick(object):
    def __init__(self, tmr):
        self.timer = tmr
        self.cancelled = False
    
    def cancel(self):
        self.cancelled = True
    
    def __call__(self):
        if not self.cancelled:
            self.timer._tick()
        

class Timer(object):
    def __init__(self, interval_sec):
        self.interval = interval_sec
        self._running = False
        self._next_tick = None
        
    @Signal
    def timeout(self):
        pass
    
    def _tick(self):
        self._next_tick = None

        self.timeout()

        if self.running: 
            self._schedule()

    def _schedule(self):
        if self._next_tick is not None:
            self._next_tick.cancel()
            self._next_tick = None
        
        self._next_tick = _Tick(self)
        app().timer(self.interval, self._next_tick)
    
    def reset_countdown(self):
        '''
        Reset the countdown so that the timer goes off after `interval` seconds from
        the time of this function call.
        
        If the timer isn't running, this will cause the timer to run once after 
        `interval` seconds.
        '''
        self._schedule()
        
    @property
    def running(self):
        return self._running
        
    @running.setter
    def running(self, val):
        if val and not self._running:
            self._schedule()
        elif not val and self._next_tick is not None:
            self._next_tick.cancel()
            self._next_tick = None
            
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
        