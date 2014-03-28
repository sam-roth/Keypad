
import sys
import subprocess
import pickle
import concurrent.futures
import threading
import queue
import logging

import os

class RemoteError(RuntimeError): pass

class ServerProxy(object):
    def start(self):
        from . import servermain
        smod = servermain.__name__
        
        lr, rw = os.pipe()
        rr, lw = os.pipe()
        
        self.fin = open(lr, 'rb')
        self.fout = open(lw, 'wb')
    
        child_env = dict(os.environ)
        child_env['PYTHONPATH'] = os.pathsep.join(sys.path)
        
        self.proc = subprocess.Popen([
            sys.executable,
            '-m',
            smod,
            str(rr),
            str(rw)
        ], pass_fds=(rr, rw), env=child_env)
    
    def send(self, msg):
        try:
            pickle.dump(msg, self.fout)
            self.fout.flush()
            res = pickle.load(self.fin)
        except OSError:
            retcode = self.proc.poll()
            if retcode is not None:
                logging.error('Worker process terminated unexpectedly. Return code: %d.', retcode)
            raise
                           
                
        if res.error is not None:
            raise RemoteError('Failed to execute task on server.') from res.error
        else:
            return res.result

    def shutdown(self):
        from .server import ShutdownMessage
        try:
            return self.send(ShutdownMessage())
        finally:
            self.fout.close()
            self.fin.close()
            
    
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, *args):
        self.shutdown()
        return False
        
def server_proxy_thread(q):
    with ServerProxy() as sp:
        while True:
            keep_running, task, future, transform = q.get()
            if not keep_running:
                return
            try:
                result = sp.send(task)
            except RemoteError as exc:
                future.set_exception(exc)
            else:
                if transform is not None:
                    try:
                        result = transform(result)
                    except Exception as exc:
                        future.set_exception(exc)
                    else:
                        future.set_result(result)
                else:
                    future.set_result(result)
        
class AsyncServerProxy(object):
    running_instances = set()
    def __init__(self):
        self.q = queue.Queue()
        self.thread = threading.Thread(target=server_proxy_thread, args=(self.q,))
        self.thread.daemon = True
        
    @classmethod
    def shutdown_all(cls):
        for p in list(cls.running_instances):
            p.shutdown()
        
    def start(self):
        self.thread.start()
        self.running_instances.add(self)        
        
    def shutdown(self):
        self.q.put((False, None, None, None))
        self.thread.join()
        self.running_instances.remove(self)
        
    def __enter__(self):
        if not self.thread.is_alive():
            self.start()
        return self
        
    def __exit__(self, *args):
        self.shutdown()
        
    def submit(self, task, transform=None):
        future = concurrent.futures.Future()
        self.q.put((True, task, future, transform))
        return future    
        
if __name__ == "__main__":
    sp = ServerProxy()
        
        