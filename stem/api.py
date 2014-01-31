

from .control import keybinding, BufferController
from .control.buffer_set import BufferSetController
from .control.interactive import interactive, menu, submenu
from .core import Keys
from .core.tag import autoextend, autoconnect



def bind(key, interactive_command_name):
    keybinding.controller.add_binding(key, interactive_command_name)

def unbind(key):
    keybinding.controller.remove_binding(key)


__all__ = '''
    bind
    unbind
    interactive
    menu
    submenu
    Keys
    autoextend
    autoconnect
'''.split()


