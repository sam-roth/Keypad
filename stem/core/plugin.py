
import weakref
import abc

_plugins = weakref.WeakSet()

class Plugin(metaclass=abc.ABCMeta):
    name = 'Unknown Plugin'
    author = 'Anonymous'
    version = '0'


    def __repr__(self):
        return '{}({!r}, {!r}, {!r})'.format(type(self).__name__,
                                             self.name,
                                             self.author,
                                             self.version)
    def __init__(self, app):
        '''
        :type app: stem.abstract.application.AbstractApplication
        '''
        self.app = app

    @abc.abstractmethod
    def attach(self):
        pass

    @abc.abstractmethod
    def detach(self):
        pass


    @staticmethod
    def plugins():
        '''
        Returns an iterator over all registered plugins.
        '''

        yield from _plugins

def register_plugin(P):
    _plugins.add(P)
    return P

    