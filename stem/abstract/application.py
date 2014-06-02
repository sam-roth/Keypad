

import abc
from ..core.responder import Responder
from ..core.signal import Signal, ClassSignal
from ..core.plugin import Plugin, attach_plugin
import weakref
import logging
import enum

class SaveResult(enum.IntEnum):
    cancel = 0
    discard = 1
    save = 2

class MessageBoxKind(enum.IntEnum):
    question = 1
    warning = 2
    error = 3


class AbstractApplication(Responder, metaclass=abc.ABCMeta):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._editors = weakref.WeakSet()
        try:
            AbstractApplication._instance
        except AttributeError:
            AbstractApplication._instance = self

        AbstractApplication.application_created(self)


        self.plugins = [P(self) for P in Plugin.plugins()]

        for p in self.plugins:
            logging.debug('attaching plugin: %r', p)
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
            if editor.path is not None and os.path.samefile(path, str(editor.path)):
                return editor


        

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
