
import os
import pickle
import subprocess
import logging
import types

class Result(object):
    def __init__(self, result, error):
        self.result = result
        self.error = error

        
class ShutdownMessage(object):
    pass
    


    
def serve(fd_r, fd_w):
    ns = types.SimpleNamespace()    
    with open(fd_r, 'rb') as fin, open(fd_w, 'wb') as fout:
        while True:
            msg = pickle.load(fin)
            
            if isinstance(msg, ShutdownMessage):
                pickle.dump(Result(result=None, error=None), fout)
                fout.flush()
                return
            
            try:
                res = msg(ns)
            except (Exception, GeneratorExit) as exc:
                logging.exception('Translating error')
                pickle.dump(Result(result=None, error=exc), fout)
            else:
                pickle.dump(Result(result=res, error=None), fout)

            finally:
                fout.flush()
                
                
            
        
def main():
    import sys
    serve(int(sys.argv[1]), int(sys.argv[2]))
    