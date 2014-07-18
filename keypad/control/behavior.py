

import weakref, types, re

from .buffer_controller         import BufferController
from ..core.tag                 import autoconnect, autoextend
from ..core                     import notification_queue, AttributedString
from ..core.attributed_string   import upper_bound
from ..buffers                  import Cursor, Span
from .interactive               import interactive, run, dispatcher
from ..abstract.application     import app

import logging

@interactive('defer')
def defer(_: object, *args):
    @notification_queue.in_main_thread
    def action():
        run(*args)

    action()


@interactive('idecl', 'which')
def find_interactive_declaration(_: object, interactive_name: 'Interactive'):
    '''
    idecl <interactive_name>

    Show the file and line where the interactive command is located.

    Example
    =======

    : idecl idecl
    idecl(object, ...)
      .../keypad/control/behavior.py:24
    '''

    from .command_line_interaction import writer

    for ty, handler in dispatcher.find_all(interactive_name):
        code = handler.__code__


        filename = code.co_filename
        linenum = code.co_firstlineno

        tyname = ty.__name__

        writer.write('{interactive_name}({tyname}, ...)\n  {filename}:{linenum}'.format(**locals()))

@interactive('iedit')
def open_interactive_declaration(_: object, interactive_name: 'Interactive'):
    '''
    Open the first declaration for the given interactive command.
    '''
    from .command_line_interaction import writer
    result = next(iter(dispatcher.find_all(interactive_name)), None)
    if result is None:
        writer.write('No command found: %r' % interactive_name)
    else:
        ty, handler = result
        code = handler.__code__
        interactive.run('edit', code.co_filename, code.co_firstlineno)

@interactive('help', 'ihelp', 'ih')
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


from keypad.core.nconfig import Config
@autoconnect(BufferController.path_changed)
def setup_buffer(controller):
    
    path = controller.path
    
    if '/c++/' in str(path):
        from ..core.filetype import Filetype
        cpp = Filetype.by_suffix('.cpp')
        
        controller.code_model = cpp.make_code_model(controller.buffer, controller.config)
        
