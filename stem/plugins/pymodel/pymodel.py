import os
import re
import logging
import string

import jedi



from stem.abstract.code import (AbstractCodeModel, 
                                AbstractCompletionResults, 
                                RelatedName,
                                IndentRetainingCodeModel,
                                AbstractCallTip)
 
from stem.buffers import Cursor
from stem.plugins.pycomplete import syntax
from stem.core.processmgr.client import AsyncServerProxy
from stem.core import AttributedString
from stem.util import dump_object

class PythonCompletionResults(AbstractCompletionResults):
    def __init__(self, token_start, results, runner):
        super().__init__(token_start)
               
        self._rows = []
        for res in results:
            self._rows.append((AttributedString(res), ))
        
        self._filt_rows = self._rows
        self._filt_indices = list(range(len(self._rows)))
        self._runner = runner

    @property
    def rows(self):
        return self._filt_rows
    
    def text(self, index):
        return self.rows[index][0].text
    
    def filter(self, pattern):
        self._filt_rows = []
        rgx = re.compile('.*?' + '.*?'.join(map(re.escape, pattern.lower())))
        
        filt_rows = []
        for i, row in enumerate(self._rows):
            if rgx.match(row[0].text.lower()):
                filt_rows.append((i, row))
                
        filt_rows.sort(key=lambda key: len(key[1][0]))
        
        self._filt_rows = [r[1] for r in filt_rows]
        self._filt_indices = [r[0] for r in filt_rows]
        
    def doc_async(self, index):
        real_index = self._filt_indices[index]
        return self._runner.submit(GetDocs(real_index))
        
    def dispose(self):
        pass # TODO
        
class WorkerStart(object):
    def __call__(self, worker):
        worker.refs = [
            Cursor, syntax, AsyncServerProxy,
            AttributedString,
            dump_object,
            RelatedName,
            WorkerTask,
            Complete,
            GetDocs,
            FindRelated
        ]

class WorkerTask(object):
    def __init__(self, filename, pos, unsaved):
        self.filename = filename
        self.pos = pos
        self.unsaved = unsaved
        
    def __call__(self, worker):
        line, col = self.pos
        script = jedi.Script(self.unsaved, line+1, col, self.filename)
        self.worker = worker
        return self.process(script)
    
class Complete(WorkerTask):
    def process(self, script):
        compls = script.completions()
        result = [c.name for c in compls]
        self.worker.last_result = compls
        
        return result
        
class PythonCallTip(AbstractCallTip):
    def __init__(self, text):
        self.text = text
        
    def to_astring(self, index):
        return AttributedString(self.text)
    
class GetCallTip(WorkerTask):
    def process(self, script):
        assert isinstance(script, jedi.Script)
        
        signature = next(iter(script.call_signatures()))
        param_names = [p.name for p in signature.params]
        
        return PythonCallTip(signature.name + '(' + ', '.join(param_names) + ')')

class GetDocs(object):
    def __init__(self, index):
        self.index = index

    def __call__(self, worker):
        try:
            defn = next(iter(worker.last_result[self.index].follow_definition()), None)
            if defn is None:
                return []
            else:
                lines = str(defn.doc).splitlines()
                return [AttributedString(line) for line in lines]
                
        except Exception as exc:
            # workaround for Jedi bug
            if "has no attribute 'isinstance'" not in str(exc):
                logging.exception('Error getting documentation')
            return []
        

class FindRelated(WorkerTask):
    def __init__(self, types, *args, **kw):
        super().__init__(*args, **kw)
        self.types = types

    @staticmethod
    def __convert_related(rel, ty):
        if rel.line is not None and rel.column is not None:
            pos = rel.line - 1, rel.column
        else:
            pos = None

        return RelatedName(
            ty,
            rel.module_path,
            pos,
            rel.full_name
        )

    def process(self, script):
        results = []        
        if self.types & RelatedName.Type.defn:
            for rel in script.goto_definitions():
                results.append(self.__convert_related(rel, RelatedName.Type.defn))
        
        if self.types & RelatedName.Type.assign or self.types & RelatedName.Type.decl:
            for rel in script.goto_assignments():
                results.append(self.__convert_related(rel, RelatedName.Type.assign | RelatedName.Type.decl))
            
        return results
            



class PythonCodeModel(IndentRetainingCodeModel):
    def __init__(self, *args, **kw):

        super().__init__(*args, **kw)
        self.highlighter = syntax.SyntaxHighlighter(
            'stem.plugins.pycomplete.syntax', 
            syntax.pylexer(), 
            dict(lexcat=None)
        )
        self.runner = AsyncServerProxy(WorkerStart())
        self.runner.start()
        self.disposed = False


    def call_tip_async(self, pos):
        return self.runner.submit(
            GetCallTip(
                str(self.path) if self.path else None,
                pos, 
                self.buffer.text
            )
        )

    def highlight(self):
        self.highlighter.highlight_buffer(self.buffer)

    def _transform_results(self, tok_start, results):
        return PythonCompletionResults(tok_start, results, self.runner)

    def _find_token_start(self, pos):
        c = Cursor(self.buffer).move(pos)

        wordchars = string.ascii_letters + string.digits + '_$'
        for i, ch in reversed(list(enumerate(c.line[:c.x]))):
            if ch not in wordchars:
                break
        else:
            i = -1
            

        return c.y, i + 1
            
    
    def completions_async(self, pos):
        tok_start = self._find_token_start(pos)
        return self.runner.submit(
            Complete(
                str(self.path) if self.path else None,
                tok_start,
                self.buffer.text
            ),
            transform=lambda res: self._transform_results(tok_start, res)
        )

    def find_related_async(self, pos, types):
        tok_start = self._find_token_start(pos)
        return self.runner.submit(
            FindRelated(
                types,
                str(self.path) if self.path else None,
                tok_start,
                self.buffer.text
            ),
        )
        
    def dispose(self):
        try:
            self.runner.shutdown()
        finally:
            self.disposed = True

