import time
import os

import signal
class InitServer(object):
    def __call__(self, worker):
        worker.initialized = True

class CrashServer(object):
    def __call__(self, worker):
        print('will crash server')
        os.kill(os.getpid(), signal.SIGSEGV)

class TestServerInitialized(object):
    def __call__(self, worker):
        return getattr(worker, 'initialized', False)




def say_hello(s):
    print('Hello, world!')
    
    return 'ok'

    
def raise_exc(s):
    raise RuntimeError('error')
    

def make_qcoreapp(s):
    from PyQt4 import Qt
    import sys
    
    app = Qt.QCoreApplication(sys.argv)
    s.app = app
    
    return app.applicationPid()
