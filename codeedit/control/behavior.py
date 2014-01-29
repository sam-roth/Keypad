

import weakref, types, re

from .                          import syntax, colors
from .buffer_controller         import BufferController
from ..core.tag                 import autoconnect, autoextend
from ..core                     import notification_center, AttributedString
from ..core.attributed_string   import upper_bound
from ..buffers                  import Cursor, Span

import logging

@autoconnect(BufferController.loaded_from_path)
def setup_buffer(controller, path):
    if path.suffix == '.py':
        controller.add_tags(
            syntax='python',
            autoindent=True
        )

        controller.refresh_view()
    elif path.suffix in ('.cpp', '.hpp'):
        controller.add_tags(
            syntax='c++',
            autoindent=True
        )
        controller.refresh_view()


#@autoconnect(BufferController.buffer_needs_highlight,
#             lambda tags: tags.get('syntax') == 'python')
def python_syntax_highlighting(controller):
    syntax.python_syntax(controller.buffer)

@autoconnect(BufferController.user_changed_buffer, 
             lambda tags: tags.get('autoindent'))
def autoindent(controller, chg):
    if chg.insert.endswith('\n'):
        beg_curs = Cursor(controller.buffer).move(*chg.pos)
        indent = re.match(r'^\s*', beg_curs.line.text)
        if indent is not None:
            Cursor(controller.buffer)\
                .move(*chg.insert_end_pos)\
                .insert(indent.group(0))



