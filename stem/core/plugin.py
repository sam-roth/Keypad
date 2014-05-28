
import weakref
import abc
import inspect
import types
import functools

_plugins = weakref.WeakSet()

class command:
    def __init__(self, *names):
        self.names = names

    def __call__(self, func):
        self.func = func
        return self

class PluginMeta(abc.ABCMeta):
    def __new__(meta, name, bases, classdict):
        cmds = []
        for k, v in list(classdict.items()):
            if isinstance(v, command):
                cmds.append(v)
                classdict[k] = v.func

        classdict['_Plugin_commands'] = tuple(cmds)

        return abc.ABCMeta.__new__(meta, name, bases, classdict)

        
class Plugin(metaclass=PluginMeta):
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

def attach_plugin(p):
    from ..control.interactive import dispatcher
    import types
    p.attach()
    for c in p._Plugin_commands:
        for name in c.names:
            m = types.MethodType(c.func, p)
            dispatcher.register(name, m)

def detach_plugin(p):
    from ..control.interactive import dispatcher
    import types
    p.detach()
    for c in p._Plugin_commands:
        for name in c.names:
            dispatcher.unregister(name, types.MethodType(c.func, p))

def register_plugin(P):
    _plugins.add(P)
    return P

    