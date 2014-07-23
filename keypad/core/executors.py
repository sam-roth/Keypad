
import functools
from concurrent import futures


from ..util.core import singleton

import logging
def set_future_result(future, func, *args, **kw):
    if not future.set_running_or_notify_cancel():
        return
    try:
        result = func(*args, **kw)
    except Exception as exc:
        logging.exception('exception')
        future.set_exception(exc)
    else:
        future.set_result(result)
    
    

@singleton
class SynchronousExecutor(futures.Executor):
    '''
    `Executor` that executes a function in the same thread and
    returns a future to its result after the function has completed.
    
    Use the `SynchronousExecutor` to wrap the result of a function that 
    does not need to execute asynchronously, but whose contract 
    requires it to return a `Future`.
    '''
    def submit(self, fn, *args, **kw):
        future = futures.Future()
        set_future_result(future, fn, *args, **kw)
        return future

class DeferredExecutor(futures.Executor):
    def __init__(self):
        super().__init__()
        self._ops = []
    
    def submit(self, fn, *args, **kw):
        future = futures.Future()
        self._ops.append((future, fn, args, kw))
        return future
    
    def execute(self):
        ops = self._ops
        self._ops = []
        
        for future, fn, args, kw in self._ops:
            set_future_result(future, fn, *args, **kw)


def future_wrap(func):
    @functools.wraps(func)
    def result(*args, **kw):
        return SynchronousExecutor.submit(func, *args, **kw)
    return result

def future_bind(func, future):
    ex = DeferredExecutor()
    future_out = ex.submit(func, future)
    future.add_done_callback(ex.execute)
    
    return future_out
