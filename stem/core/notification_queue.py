
import queue
import logging
import threading

_notification_queue = queue.Queue()
_post_handlers = set()
_lock = threading.Lock()


def in_main_thread(func):
    def result(*args, **kw):
        def callback():
            return func(*args, **kw)
        run_in_main_thread(callback)
    return result


def process_events(exc_handler=None):
    size = _notification_queue.qsize()
    
    for _ in range(size):
        try:
            n = _notification_queue.get()
        except queue.Empty:
            break
        else:
            try:
                n()
            except Exception as exc:
                if exc_handler is not None:
                    exc_handler(exc)
                else:
                    logging.exception(exc)


def register_post_handler(h):
    with _lock:
        _post_handlers.add(h)

    # call the post handler to pump messages that have already arrived
    h()
    return h

def run_in_main_thread(n):
    _notification_queue.put(n)
    with _lock:
        for h in _post_handlers:
            h()
