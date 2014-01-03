

import weakref
import functools
import traceback
import types


def makeInstanceSignal(proto_func):
    class InstanceSignal(object):
        def __init__(self):
            self._observers = weakref.WeakSet()

        def connect(self, observer):
            self._observers.add(observer)
            return observer

        def disconnect(self, observer):
            self._observers.remove(observer)
    
        @functools.wraps(proto_func)
        def __call__(self, *args, **kw):
            for observer in self._observers:
                try:
                    observer(*args, **kw)
                except RuntimeError:
                    traceback.print_exc()
    return InstanceSignal()

class Signal(object):
    def __init__(self, proto_func):
        self._proto_func = proto_func
        self._instances = weakref.WeakKeyDictionary()

    def __get__(self, instance, owner):
        inst = self._instances.get(instance)
        if inst is None:
            method = types.MethodType(self._proto_func,
                                      instance)
            
            inst = makeInstanceSignal(method)

            self._instances[instance] = inst

        return inst



def main():
    class Test(object):
        @Signal
        def foo(self, bar, baz):
            pass

    t = Test()
    t2 = Test()

    def handler(bar, baz):
        print('bar={}, baz={}'.format(bar, baz))

    t.foo.connect(handler)

    t.foo(1, 2)
    t.foo(3, 4)

    t2.foo(5, 6)
    t2.foo(7, 8)

if __name__ == '__main__':
    main()


