
import multiprocessing
import threading
import logging

from codeedit.core import AttributedString

class Worker(object):
    def __init__(self):
        import jedi
        self.jedi = jedi
        self.completions = []
        logging.debug('worker started')

    def complete(self, source, line, col, path):
        logging.debug('completing')
        try:
            script = self.jedi.Script(source, line=line+1, column=col, path=path)
            self.completions = script.completions()

            return self._marshal_completions()
        except:
            logging.exception('error in completion')
            return []

    def _marshal_completions(self):
        logging.debug('marshalling')
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


def init_worker():
    global worker
    worker = Worker()

def complete(source, line, col, path):
    return worker.complete(source, line, col, path)

def follow_definition(index):
    return worker.follow_definition(index)


