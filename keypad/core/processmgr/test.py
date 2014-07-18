
import unittest
from .client import AsyncServerProxy, UnexpectedWorkerTerminationError
import logging
from . import testfunc

class TestAsyncServerProxyRestart(unittest.TestCase):

    def setUp(self):
        self.runner = AsyncServerProxy(testfunc.InitServer())
        self.runner.start()
    
    def tearDown(self):
        self.runner.shutdown()
        
    def test_that_server_is_initialized_initially(self):
        assert self.runner.submit(testfunc.TestServerInitialized()).result()
    
    def test_that_server_is_initialized_after_crash(self):
        try:
            self.runner.submit(testfunc.CrashServer()).result()
        except UnexpectedWorkerTerminationError:
            pass
        assert self.runner.submit(testfunc.TestServerInitialized()).result()
    
    

def test_that_fourth_error_is_fatal():
    try:
        prox = AsyncServerProxy(testfunc.CrashServer())
        prox.start()
        prox.submit(testfunc.InitServer()).result()
    except UnexpectedWorkerTerminationError:
        pass
    else:
        assert False, 'expected error'
        
    
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()