

import abc
from ..core.responder import Responder

class Application(Responder, metaclass=abc.ABCMeta):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

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


def app():
    return Application.instance()

