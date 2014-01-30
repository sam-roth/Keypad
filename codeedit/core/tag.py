


from . import signal
from collections import defaultdict
import types
import weakref
import functools

class Tagged(object):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.__tags = {}
        self.extensions = {}

    @signal.Signal
    def needs_init(self):
        pass

    def request_init(self):
        self.tags_added(self, {})
        self.needs_init()

    @signal.ClassSignal
    def tags_added(cls, instance, tags):
        pass
    
    @signal.ClassSignal
    def tags_removed(cls, instance, tags):
        pass
    
    def add_tags(self, **kw):
        self.remove_tags(set(kw.keys()).intersection(self.__tags.keys()))

        self.__tags.update(kw)
        self.tags_added(self, kw)
    
    def remove_tags(self, tags):
        tag_kv = {}
        
        for k in tags:
            try:
                tag_kv[k] = self.__tags.pop(k)
            except KeyError:
                pass

        self.tags_removed(self, tag_kv)



    @property
    def tags(self):
        return types.MappingProxyType(self.__tags)


_dummy = object()

class _WeakPartial(object):

    def __init__(self, func, arg):
        self.func = func
        self.arg = weakref.ref(arg)

    def __call__(self, *args, **kwargs):
        arg = self.arg()
        if arg is not None:
            return self.func(arg, *args, **kwargs)

class Autoconnection(object):
    def __init__(self, sig, pred, func):
        if isinstance(sig, type):
            self.sig = None
            cls = sig
        else:
            self.sig = sig
            cls = sig._owner

        self.pred = pred
        self.func = func
        self._observed = weakref.WeakSet()

        cls.tags_added      += self._on_tags_added
        cls.tags_removed    += self._on_tags_removed

    
    def _on_tags_added(self, inst, tags):
        if inst not in self._observed and self.pred(tags):
            if self.sig is None:
                self.func(inst, True)
            else:
                self.sig.for_instance(inst).connect(self.func, add_sender=True)
            self._observed.add(inst)

    def _on_tags_removed(self, inst, tags):
        if inst in self._observed:
            if not self.pred(inst.tags):
                self._observed.remove(inst)

                if self.sig is None:
                    self.func(inst, False)
                else:
                    self.sig.for_instance(inst).disconnect(self.func)
    
    def __call__(self, *args, **kw):
        return self.func(*args, **kw)


class Autoextension(object):
    def __init__(self, extended_cls, extension_cls, pred):
        self.pred = pred
        self.extended_cls = extended_cls
        self.extension_cls = extension_cls
        
        extended_cls.tags_added += self._on_tags_added

    def _on_tags_added(self, inst, tags):
        if self.extension_cls not in inst.extensions\
            and self.pred(tags):
            
            inst.extensions[self.extension_cls] = self.extension_cls(inst)

    def _on_tags_removed(self, inst, tags):
        if self.extension_cls in inst.extensions\
            and not self.pred(inst.tags):
            del inst.extensions[self.extension_cls]

    

def autoconnect(signal_or_cls, predicate=None):
    if predicate is None:
        predicate = lambda tags: True
    def result(func):
        conn = Autoconnection(signal_or_cls, predicate, func)
        functools.update_wrapper(conn, func)
        return conn
    return result


def autoextend(extended_cls, predicate):
    def result(extension_cls):
        extension_cls._autoextension = Autoextension(extended_cls, extension_cls, predicate)
        return extension_cls
    return result

def main():
    class T1(Tagged):
        
        @signal.Signal
        def foo(self): pass

    class T2(T1): pass
        


    @autoconnect(T1.foo, lambda tags: tags.get('bar') == 'baz')
    def autofunc(sender):
        print('autofunc sender=', sender)

    t1a = T1()
    t1b = T1()
    t2a = T2()

    t1a.foo()
    t1b.foo()
    t2a.foo()
    t1a.add_tags(bar='baz')
    t2a.add_tags(bar='baz')
    t1a.foo()
    t1b.foo()
    t2a.foo()


if __name__ == '__main__':
    main()

