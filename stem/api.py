

from .control import keybinding, BufferController
from .control.interactive import interactive, menu
from .core import Keys, errors, AttributedString
from .core.tag import autoextend, autoconnect
from .core.nconfig import Config, Settings
from .abstract.application import app
from .core.plugin import Plugin, register_plugin, command
from .core.filetype import Filetype
from .buffers import Span, Region, Buffer, Cursor
from .core.notification_queue import run_in_main_thread, in_main_thread

def bind(key, interactive_command_name):
    keybinding.controller.add_binding(key, interactive_command_name)

def unbind(key):
    keybinding.controller.remove_binding(key)

# Strengthen refs to imported plugins so they aren't GCed.
_pkg_refs = []

def load_plugins(path, prefix):
    import logging
    import pkgutil
    import importlib

    def errh(name):
        logging.exception('error loading %r', name)
    for finder, name, is_pkg in pkgutil.walk_packages(path, prefix, errh):
        logging.info('importing plugin %r', name)
        _pkg_refs.append(importlib.import_module(name))


__all__ = '''
    in_main_thread
    run_in_main_thread
    app
    bind
    command
    errors
    unbind
    interactive
    menu
    Keys
    autoextend
    autoconnect
    load_plugins
    Plugin
    register_plugin
    Filetype
    Config
    Settings
    Span
    Region
    Buffer
    Cursor
'''.split()


