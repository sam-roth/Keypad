

import weakref, types, re

from .buffer_controller         import BufferController
from ..core.tag                 import autoconnect, autoextend
from ..core                     import notification_queue, AttributedString
from ..core.attributed_string   import upper_bound
from ..buffers                  import Cursor, Span
from .interactive               import interactive, run, dispatcher
from ..abstract.application     import Application, app

import logging

@interactive('defer')
def defer(_: object, *args):
    @notification_queue.in_main_thread
    def action():
        run(*args)

    action()


@interactive('idecl')
def find_interactive_declaration(_: object, interactive_name: 'Interactive'):
    '''
    idecl <interactive_name>

    Show the file and line where the interactive command is located.

    Example
    =======

    : idecl idecl
    idecl(object, ...)
      .../stem/control/behavior.py:24
    '''

    from .command_line_interaction import writer
    
    for ty, handler in dispatcher.find_all(interactive_name):
        code = handler.__code__
        
        
        filename = code.co_filename
        linenum = code.co_firstlineno
        
        tyname = ty.__name__

        writer.write('{interactive_name}({tyname}, ...)\n  {filename}:{linenum}'.format(**locals()))

@interactive('ihelp', 'ih')
def interactive_command_help(_: object, interactive_name: 'Interactive'):
    '''
    ih[elp] <interactive_name>
    
    Show the docstring for an interactive command.

    Example
    =======

    : ihelp ihelp
    ihelp(object, ...)

      ih[elp] <interactive_name>

      Show the docstring for an interactive command.
    '''
    import textwrap, inspect
    from .command_line_interaction import writer
    for ty, handler in dispatcher.find_all(interactive_name):
        tyname = ty.__name__

        header = '{interactive_name}({tyname}, ...)\n'.format(**locals())
        writer.write(header + '\n' + textwrap.indent(inspect.getdoc(handler), '  '))



@autoconnect(BufferController.path_changed)
def setup_buffer(controller):
    path = controller.path
    if path.suffix == '.py':
        from ..plugins.pymodel.pymodel import PythonCodeModel
        controller.code_model = PythonCodeModel(controller.buffer, controller.config)
        controller.add_tags(
#             syntax='python',
#             autoindent=True,
            parmatch=True
        )
# 
        controller.refresh_view()
    elif path.suffix in ('.cpp', '.hpp', '.cc', '.hh', '.h', '.C'):
        controller.add_tags(
            syntax='c++',
            autoindent=True,
            parmatch=True,
            commentchar='//'
        )
        controller.refresh_view()

@autoconnect(BufferController.user_changed_buffer, 
             lambda tags: tags.get('autoindent'))
def autoindent(controller, chg):
    if chg.insert.endswith('\n'):
        beg_curs = Cursor(controller.buffer).move(*chg.pos)
        for _ in beg_curs.walklines(-1):
            indent = re.match(r'^\s*', beg_curs.line.text)
            if beg_curs.line.text:
                break
                
        if indent is not None:
            curs = Cursor(controller.buffer)\
                .move(*chg.insert_end_pos)

            # check if we're already indented
            if not re.match(r'^\s+', curs.line.text):
                curs.insert(indent.group(0))



