

from .control import keybinding, BufferController
from .control.buffer_set import BufferSetController
from .control.interactive import interactive, menu, submenu
from .core import Keys
from .core.tag import autoextend, autoconnect



def bind(key, interactive_command_name):
    keybinding.controller.add_binding(key, interactive_command_name)

def unbind(key):
    keybinding.controller.remove_binding(key)


def load_plugins(path, prefix):
    import logging
    import pkgutil

    def errh(name):
        logging.exception('error loading %r', name)
    for finder, name, is_pkg in pkgutil.walk_packages(path, prefix, errh):
        logging.info('loading plugin %r', name)




__all__ = '''
    bind
    unbind
    interactive
    menu
    submenu
    Keys
    autoextend
    autoconnect
    load_plugins
'''.split()


