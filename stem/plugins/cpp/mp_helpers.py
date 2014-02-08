'''
Multiprocessing helpers
'''

import threading

def call_async(callback, func, *args, **kw):
	threading.Thread(target=lambda: callback(func(*args, **kw)), daemon=True).start()

