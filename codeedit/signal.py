

import weakref
import functools
import traceback
import types
import functools

class WeakMethodProxy(object):
    def __init__(self, bound_method):
        self.instance = weakref.ref(bound_method.__self__)
        self.function = weakref.ref(bound_method.__func__)
 
    def __hash__(self):
        return hash((self.instance, self.function))
    
    def __eq__(self, other):
        self.instance == other.instance
        self.function == other.function
    
    def __call__(self):
        inst = self.instance()
        if inst is not None:
            return functools.partial(self.function(), inst)
        else:
            return None




def makeInstanceSignal(proto_func):
    class InstanceSignal(object):
        def __init__(self):
            self._observers = set()

        def connect(self, observer):
            if isinstance(observer, types.MethodType):
                self._observers.add(WeakMethodProxy(observer))
            else:
                self._observers.add(weakref.ref(observer))

            return observer

        def disconnect(self, observer):
            if isinstance(observer, types.MethodType):
                self._observers.remove(WeakMethodProxy(observer))
            else:
                self._observers.remove(weakref.ref(observer))

    
        @functools.wraps(proto_func)
        def __call__(self, *args, **kw):
            for observer in self._observers:
                try:
                    real_obs = observer()
                    if real_obs is not None:
                        real_obs(*args, **kw)
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


