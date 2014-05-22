

import abc
from ..core.responder import Responder
import weakref

import enum

class SaveResult(enum.IntEnum):
    cancel = 0
    discard = 1
    save = 2


class Application(Responder, metaclass=abc.ABCMeta):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._editors = weakref.WeakSet()
        try:
            Application._instance
        except AttributeError:
            Application._instance = self

    @staticmethod
    def instance():
        '''
        Get the shared Application instance.

        :rtype: Application
        '''

        return Application._instance        

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

    @abc.abstractmethod
    def new_window(self):
        '''
        Create and return a new window.

        :rtype: AbstractWindow
        '''

    @abc.abstractmethod
    def new_editor(self):
        '''
        Create and return a new editor.

        :rtype: stem.abstract.editor.AbstractEditor
        '''

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
    return Application.instance()




class AbstractWindow(Responder, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def add_editor(self, editor):
        '''
        Add an editor to this window.
        '''

