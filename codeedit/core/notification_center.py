

import queue
import logging
import threading

_notification_queue = queue.Queue()
_post_handlers = set()
_lock = threading.Lock()


def process_events():
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
                logging.exception(exc)


def register_post_handler(h):
    with _lock:
        _post_handlers.add(h)

    return h

def post(n):
    _notification_queue.put(n)
    with _lock:
        for h in _post_handlers:
            h()
