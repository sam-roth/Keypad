

import weakref, types, re

from .              import syntax
from .controller    import Controller
from ..core.tag     import autoconnect, autoextend
from ..core         import notification_center
from ..buffers      import Cursor


@autoconnect(Controller.needs_init,
             lambda tags: True)
def setup_buffer(controller):
    # TODO: recognize filetypes
    controller.add_tags(
        syntax='python',
        autoindent=True
    )

    controller.refresh_view()


@autoconnect(Controller.buffer_needs_highlight,
             lambda tags: tags.get('syntax') == 'python')
def python_syntax_highlighting(controller):
    syntax.python_syntax(controller.buffer)

@autoconnect(Controller.user_changed_buffer, 
             lambda tags: tags.get('autoindent'))
def autoindent(controller, chg):
    if chg.insert.endswith('\n'):
        beg_curs = Cursor(controller.buffer).move(*chg.pos)
        indent = re.match(r'^\s*', beg_curs.line.text)
        if indent is not None:
            Cursor(controller.buffer)\
                .move(*chg.insert_end_pos)\
                .insert(indent.group(0))



import jedi
import multiprocessing




def call_method(obj, method_name, *args, **kw):
    return getattr(obj, method_name)(*args, **kw)

@autoextend(Controller, lambda tags: tags.get('syntax') == 'python')
class PythonCompleter(object):
    def __init__(self, controller):
        '''
        :type controller: codeedit.control.Controller
        '''
    
        import keyword
        self.words = [(w,) for w in keyword.kwlist]
        self.controller = controller
        self.controller.completion_requested += self._on_completion_requested
        self.controller.user_changed_buffer  += self._on_user_changed_buffer
        self.controller.completion_done      += self._on_completion_done
        self.start_curs = None

    @staticmethod
    def _complete_thd(source, line, col):
        result = [(c.name,) for c in jedi.Script(source, line=line+1, column=col).completions()]
        sorted_result = sorted(result, key=lambda x:len(x[0]))

        return result, sorted_result


    def _refilter(self, pattern):
        expr = '.*?'.join(pattern.lower())
        rgx = re.compile(expr)

        self.controller.view.completions = sorted([
            (w,) for (w,) in self.words
            if rgx.match(w.lower()) is not None
            ], key=lambda x: len(x[0]))
    
    def _on_completion_requested(self):
        self.start_curs = self.controller.canonical_cursor.clone()

        source = self.controller.buffer.text
        line, col = self.start_curs.pos
            
        def callback(args):
            def finish():
                result, sorted_result = args

                self.words = result
                self.controller.view.completions = sorted_result
                self.controller.view.show_completions()

            notification_center.post(finish)

        
        pool.apply_async(call_method, [
            PythonCompleter, 
            '_complete_thd', 
            source, 
            line, 
            col
        ], callback=callback)
        

        

    def _on_user_changed_buffer(self, chg):
        if self.start_curs is not None:
            if self.start_curs.pos == self.controller.canonical_cursor.pos:
                self.start_curs.left()
            text = self.start_curs.text_to(self.controller.canonical_cursor)
            self._refilter(text)

    def _on_completion_done(self, index):
        if index is None:
            self.start_curs = None
        elif self.start_curs is not None:
            with self.controller.manipulator.history.transaction():
                compl = self.controller.view.completions[index][0]
                self.start_curs.remove_to(self.controller.canonical_cursor)
                self.controller.canonical_cursor.insert(compl)

                self.controller.refresh_view()
            
            self.start_curs = None
            
pool = multiprocessing.Pool(processes=1)
