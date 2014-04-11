
import multiprocessing as mp
import multiprocessing.managers as mpmanagers
import threading
import sys


class SingleThreadServer(mpmanagers.Server):
    
    def serve_forever(self):
        self.stop_event = threading.Event()
        mpmanagers.current_process()._manager_server = self
        try:
            self.accepter()
            try:
                while not self.stop_event.is_set():
                    self.stop_event.wait(1)
            except (KeyboardInterrupt, SystemExit):
                pass
        finally:
            if sys.stdout != sys.__stdout__:
                util.debug('resetting stdout, stderr')
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
            sys.exit(0)

    def accepter(self):
        while True:
            try:
                c = self.listener.accept()
            except (OSError, IOError):
                continue
            self.handle_request(c)

class Manager(mpmanagers.BaseManager):
    _Server = SingleThreadServer

class AbstractTask(object):
    def __call__(self, worker):
        raise NotImplementedError

class Worker(object):
    def execute(self, task):
        return task(self)

Manager.register('Worker', Worker)


import concurrent.futures
import threading


class Runner(object):
    def __init__(self):
        print('creating manager')
        self.manager = Manager()
        print('starting manager')
        self.manager.start()
        print('creating worker')
        self.proxy = self.manager.Worker()
        print('creating executor')
        self.executor = concurrent.futures.ThreadPoolExecutor(1)
        print('creating lock')
        self.lock = threading.Lock()
        print('done')

    def dispose(self):
        with self.lock:
            self.executor.shutdown()
            self.manager.shutdown()

    def execute(self, task):
        with self.lock:
            return self.proxy.execute(task)

    def submit(self, task):
        return self.executor.submit(self.execute, task)

        
    