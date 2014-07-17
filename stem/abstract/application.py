

import abc
from ..core.responder import Responder
from ..core.signal import Signal, ClassSignal
from ..core.plugin import Plugin, attach_plugin, detach_plugin
import weakref
import logging
import enum
import os.path

class SaveResult(enum.IntEnum):
    cancel = 0
    discard = 1
    save = 2

class MessageBoxKind(enum.IntEnum):
    question = 1
    warning = 2
    error = 3

def _fullpathnorm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))

def _same_file(path1, path2):
    try:
        return os.path.samefile(path1, path2)
    except OSError as exc:
        # For "Incorrect function" error when working on Windows shares.
        if exc.args and exc.args[0] == 22:
            return _fullpathnorm(path1) == _fullpathnorm(path2)
        else:
            raise


class AbstractApplication(Responder, metaclass=abc.ABCMeta):
    MessageBoxKind = MessageBoxKind
    
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._editors = weakref.WeakSet()
        self._windows = weakref.WeakSet()
        try:
            AbstractApplication._instance
        except AttributeError:
            AbstractApplication._instance = self

        AbstractApplication.application_created(self)


        self.plugins = [P(self) for P in Plugin.plugins()]

        for p in self.plugins:
            logging.debug('attaching plugin: %r', p)
            attach_plugin(p)

    def remove_plugin(self, cls):
        logging.debug('detaching plugin: %r', cls)
        to_remove = [p for p in self.plugins
                     if isinstance(p, cls)]

        for plugin in to_remove:
            detach_plugin(plugin)
            self.plugins.remove(plugin)

    def update_plugins(self):
        all_plugins = frozenset(Plugin.plugins())
        cur_plugins = frozenset(type(p) for p in self.plugins)
        new_plugins = all_plugins - cur_plugins

        for plugin in new_plugins:
            logging.debug('attaching plugin: %r', plugin)
            p = plugin(self)
            self.plugins.append(p)
            attach_plugin(p)


    @ClassSignal
    def application_created(cls, self):
        pass

    @Signal
    def window_created(self, window):
        pass

    @Signal
    def editor_created(self, editor):
        pass

    def message_box(self, parent, 
                     text, choices,
                     accept=0, reject=-1, kind=None):
    
        return self._message_box(parent,
                                 text,
                                 choices,
                                 accept=accept,
                                 reject=reject,
                                 kind=kind)
    @abc.abstractmethod
    def _message_box(self, parent, 
                     text, choices,
                     accept=0, reject=-1, kind=None):
        pass

    @abc.abstractmethod
    def beep(self):
        pass

    @staticmethod
    def instance():
        '''
        Get the shared Application instance.

        :rtype: AbstractApplication
        '''

        return AbstractApplication._instance        

    @property
    def clipboard_value(self):
        '''
        The current system clipboard value, or an internal clipboard's
        value if there is no access to the system clipboard, or it does not
        exist.
        '''

        try:
            value = self.__clipboard_value
        except AttributeError:
            value = None

        return value

    @clipboard_value.setter
    def clipboard_value(self, value):
        self.__clipboard_value = value


    @abc.abstractmethod
    def timer(self, time_s, callback):
        pass

    def new_window(self):
        '''
        Create and return a new window.

        :rtype: AbstractWindow
        '''
        w = self._new_window()
        self._windows.add(w)
        self.window_created(w)

        return w

    @abc.abstractmethod
    def _new_window(self):
        '''
        Implementation for new_window.

        :rtype: AbstractWindow
        '''

    @abc.abstractmethod
    def _new_editor(self):
        '''
        Implementation for new_editor.
        
        :rtype: stem.abstract.editor.AbstractEditor
        '''

    def _unregister_editor(self, editor):
        '''
        Remove the editor from the set of editors.
        '''

        try:
            self._editors.remove(editor)
        except KeyError:
            pass

    def new_editor(self):
        '''
        Create and return a new editor.

        :rtype: stem.abstract.editor.AbstractEditor
        '''
        e = self._new_editor()
        self._editors.add(e)
        self.editor_created(e)
        return e

    @abc.abstractmethod
    def save_prompt(self, editor):
        pass

    @abc.abstractmethod
    def get_open_path(self, parent):
        pass

    @abc.abstractmethod
    def get_save_path(self, editor):
        pass

    def close(self, editor):
        '''
        Close an editor, prompting the user to save if the contents are modified.

        :type editor: stem.abstract.editor.AbstractEditor
        '''
        if editor.is_modified:
            r = self.save_prompt(editor)
            if r == SaveResult.save:
                if editor.path is None:
                    sp = self.get_save_path(editor)
                else:
                    sp = editor.path
                if sp is not None:
                    editor.save(sp)
                    editor.kill()
                    return True
                else:
                    return False
            elif r == SaveResult.discard:
                editor.kill()
                return True
        else:
            editor.kill()
            return True

    def save(self, editor):
        if editor.path is None:
            sp = self.get_save_path(editor)
        else:
            sp = editor.path

        if sp is not None:
            editor.save(sp)

    def find_editor(self, path):
        import os.path
        path = str(path)

        for editor in self._editors:
            if editor.path is not None and _same_file(path, str(editor.path)):
                return editor


    @property
    def editors(self):
        return tuple(self._editors)
        
    @property
    def windows(self):
        return tuple(self._windows)


    def find_object(self, ty):
        '''
        Find the active object of type `ty`.

        .. example::

            To kill the active editor, use::

                app().find_object(AbstractEditor).kill()

        '''
        result = self.next_responder.find_responder(ty)
        assert isinstance(result, (NoneType, ty))
        return result

def app():
    return AbstractApplication.instance()




class AbstractWindow(Responder, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def add_editor(self, editor):
        '''
        Add an editor to this window.
        '''
    @abc.abstractmethod
    def close(self):
        '''
        Close the window, prompting the user to save changes.
        '''

    @abc.abstractproperty
    def active_editor(self):
        pass


    @Signal
    def editor_activated(self, editor):
        pass
        
