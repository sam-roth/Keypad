

import weakref, types, re

from .              import syntax
from .controller    import Controller
from ..core.tag     import autoconnect, autoextend
from ..core         import notification_center, AttributedString
from ..core.attributed_string import upper_bound
from ..buffers      import Cursor, Span
from . import colors

import logging

@autoconnect(Controller.loaded_from_path)
def setup_buffer(controller, path):
    if path.suffix == '.py':
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




#@autoconnect(Controller.buffer_was_changed,
#             lambda tags: tags.get('softtabstop'))
#def softtabstop(controller, chg):
    


import jedi
import multiprocessing
import textwrap



def call_method(obj, method_name, *args, **kw):
    return getattr(obj, method_name)(*args, **kw)

@autoextend(Controller, lambda tags: tags.get('syntax') == 'python')
class PythonCompleter(object):
    last_completion_info = None
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
        self.controller.user_requested_help  += self._on_user_requested_help
        self.controller.completion_row_changed += self._on_row_changed
        self.start_curs = None
        self._complete_index = None


    def _on_user_requested_help(self):
        source = self.controller.buffer.text
        line, col = self.controller.canonical_cursor.pos

        def callback(result):
            print(result)
        
        pool.apply_async(call_method, [
            PythonCompleter, 
            '_complete_thd', 
            source, 
            line, 
            col,
            self.controller.tags.get('path'),
            'call_signatures',
        ], callback=callback)
        

    @staticmethod
    def _complete_thd(source=None, line=None, col=None, path=None, mode='complete', comp_idx=None):
        try:
            if path is not None:
                path = path.as_posix()
            if mode != 'follow_definition':
                script = jedi.Script(source, line=line+1, column=col, path=path)
            if mode == 'complete':
                print('working')
                comps = script.completions()
                result = [
                    (c.name, AttributedString(c.type, italic=True)) 
                    for c in comps
                ]

                PythonCompleter.last_completion_info = comps
    
                print('finished')
                sorted_result = sorted(result, key=lambda x:len(x[0]))
                    

                return result, sorted_result
            elif mode == 'follow_definition':

                try:
                    defns = PythonCompleter.last_completion_info[comp_idx].follow_definition()
                except:
                    return ['error']
                else:
                    return [defn.doc for defn in defns]

            elif mode == 'call_signatures':
                import pprint
                sigs = script.call_signatures()
                return pprint.pformat(dict(
                    params=sigs[0].params,
                    call_name=sigs[0].call_name
                ))

        except:
            import traceback
            traceback.print_exc()

    def _on_row_changed(self, comp_idx):
        self._complete_index = comp_idx
        def callback(result):
            def msg():
                text = '\n\n'.join(result)
                paras = text.split('\n\n') #textwrap.fill(text, width=30, replace_whitespace=False, subsequent_indent='  ').splitlines()

                height, width = self.controller.completion_doc_plane_size


                lines = '\n'.join(textwrap.fill(para, width=width - 3, fix_sentence_endings=True, subsequent_indent='  ') for para in paras).splitlines()

                self.controller.completion_doc_lines = [AttributedString(r) for r in lines]
            notification_center.post(msg)

        pool.apply_async(
            call_method, 
            [
                PythonCompleter,
                '_complete_thd'
            ], 
            {
                'mode': 'follow_definition',
                'comp_idx': self.completion_indices[comp_idx]
            },
            callback=callback
        )

    def _refilter(self, pattern):
        logging.info('filter pattern: %r', pattern)
        expr = '.*?'.join(map(re.escape, pattern.lower()))
        rgx = re.compile(expr)


        sorted_pairs = sorted(
            [
                (i, t) for (i, t) in enumerate(self.words)
                if rgx.match(t[0].lower()) is not None
            ],
            key=lambda x: len(x[1][0])
        )


        self.completion_indices, self.controller.view.completions = \
            zip(*sorted_pairs) if sorted_pairs \
            else ([], [])

    def _find_start(self):
        logging.debug('_find_start')
        start_curs = self.controller.canonical_cursor.clone()
        
        line, col = start_curs.pos
        for idx, ch in enumerate(reversed(start_curs.line.text[:col])):
            if re.match(r'[\w\d]', ch) is None:
                start_curs.left(idx)
                break
        else:
            start_curs.home()

        return start_curs
    
    def _on_completion_requested(self):
        self.start_curs = self._find_start().pos
        #self.controller.canonical_cursor.clone()

        source = self.controller.buffer.text
        line, col = self.start_curs
            
        def callback(args):
            def finish():
                result, sorted_result = args


                self.words = result
                #self.controller.view.completions = sorted_result
                self._refilter_typed()

                self.controller.view.show_completions()


            notification_center.post(finish)

        
        pool.apply_async(call_method, [
            PythonCompleter, 
            '_complete_thd', 
            source, 
            line, 
            col,
            self.controller.tags.get('path')
        ], callback=callback)

    @property
    def _start_cursor(self):
        return self.controller.canonical_cursor.clone().move(*self.start_curs)

        
    def _refilter_typed(self):
        if self.start_curs is not None:
            try:
                start_curs = self._start_cursor
                span = Span(start_curs, self.controller.canonical_cursor)
                span.set_attributes(
                    sel_bgcolor=colors.scheme.search_bg,
                    sel_color=colors.scheme.bg
                )
            except IndexError:
                self.start_curs = None
            else:
                text = start_curs.text_to(self.controller.canonical_cursor)
                self._refilter(text)

    def _reset_color(self):
        Span(self._start_cursor, self.controller.canonical_cursor).set_attributes(
            sel_bgcolor=None,
            sel_color=None
        )


    @property
    def _edit_cursor(self):
        return Cursor(self.controller.buffer).move(*self.controller.canonical_cursor.pos)
        
    def _on_user_changed_buffer(self, chg):
        if chg.insert.endswith('.'):
            if self.start_curs is not None:
                self._insert_result(self._complete_index)
                ec = self._edit_cursor
                ec.insert('.')
                self.controller.canonical_cursor.move(*ec.pos)

                self._reset_color()
                self.start_curs = None
            self._on_completion_requested()

        self._refilter_typed()

    def _insert_result(self, index):
        start_curs = self._start_cursor
        compl = self.controller.view.completions[index][0]
        start_curs.remove_to(self.controller.canonical_cursor)
        self.controller.canonical_cursor.insert(compl)



    def _on_completion_done(self, index):
        if index is None:
            self._reset_color()
            self.start_curs = None
        elif self.start_curs is not None:
            with self.controller.manipulator.history.transaction():
                self._insert_result(index)
            self.controller.refresh_view()
            self._reset_color()
            self.start_curs = None
            
pool = multiprocessing.Pool(processes=1)
