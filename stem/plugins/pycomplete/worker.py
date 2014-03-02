
import multiprocessing
import threading
import logging

from stem.core import AttributedString
from stem.util import dump_object

class Worker(object):
    def __init__(self):
        import jedi
        self.jedi = jedi
        self.completions = []
        logging.debug('worker started')

    def complete(self, source, line, col, path):
        try:
            script = self.jedi.Script(source, line=line+1, column=col, path=path)
            self.completions = script.completions()

            return self._marshal_completions()
        except:
            logging.exception('error in completion')
            return []

    def _marshal_completions(self):
        return [
            (c.name, AttributedString(c.type, italic=True))
            for c in self.completions
        ]
    
    def follow_definition(self, index):
        try:
            defns = self.completions[index].follow_definition()
        except:
            return []
        else:
            return [defn.doc for defn in defns]

    def find_definition(self, source, line, col, path, mode='def'):
        script = self.jedi.Script(source, line=line+1, column=col, path=path)
        if mode == 'decl':
            defn = next(iter(script.goto_definitions()), None)
        elif mode == 'def':
            defn = next(iter(script.goto_assignments()), None)
        else:
            raise TypeError('mode must be def or decl')
        
        if defn:
            return dict(path=str(defn.module_path), pos=(defn.line - 1, defn.column))
        else:
            return None
            
def init_worker():
    global worker
    worker = Worker()

def complete(source, line, col, path):
    return worker.complete(source, line, col, path)

def follow_definition(index):
    return worker.follow_definition(index)


def find_definition(source, line, col, path,mode='def'):
    return worker.find_definition(source,line,col,path,mode)