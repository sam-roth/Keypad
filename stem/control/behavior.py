

import weakref, types, re

from .buffer_controller         import BufferController
from ..core.tag                 import autoconnect, autoextend
from ..core                     import notification_queue, AttributedString
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
    elif path.suffix in ('.cpp', '.hpp', '.cc', '.hh', '.h'):
        controller.add_tags(
            syntax='c++',
            autoindent=True
        )
        controller.refresh_view()

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



