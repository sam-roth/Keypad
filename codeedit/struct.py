

import types

from collections import OrderedDict, namedtuple
from itertools import chain
class DiscoveryDict(OrderedDict):
    
    DiscoveredObject = object()

    def __init__(self):
        super().__init__()
        self.discovered = []
        self.defaults = {}

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            if key in ('__name__', 'property', 'classmethod', 'staticmethod'): # python will try to read this before writing it
                raise

            self.discovered.append(key)
            self[key] = DiscoveryDict.DiscoveredObject
            return DiscoveryDict.DiscoveredObject

    def __setitem__(self, key, value):
        if isinstance(value, _Default):
            self.discovered.append(key)
            self.defaults[key] = value.value
            super().__setitem__(key, DiscoveryDict.DiscoveredObject)
        elif value == ():
            self.discovered.append(key)
        else:
            super().__setitem__(key, value)



_dummy = object()

def _make_constructor(fields, kwfields):

    proto_fields = fields
    proto_kwfields = ['{0}=kwfields[{0!r}]'.format(field) for field in kwfields]
    proto_args = ['self'] + proto_fields + proto_kwfields 

    proto_str = 'def __init__(' + ', '.join(proto_args) + '):\n    pass\n'

    inits = ['    self.{0} = {0}\n'.format(name) for name in chain(fields, kwfields)]
    
    inits_str = ''.join(inits)

    cons_str = proto_str + inits_str
    

    ns = {
        'kwfields': kwfields
    }

    exec(cons_str, ns)
    
    return ns['__init__']
    


class _Default(object):
    def __init__(self, value):
        self.value = value


class StructMeta(type):

    @classmethod
    def __prepare__(metacls, name, bases, **kw):
        result = DiscoveryDict()
        result['default'] = _Default
        return result


    def __new__(cls, name, bases, namespace, **kw):

        discovered = namespace.discovered 
        
        del namespace['default']

        for x in discovered:
            try:
                del namespace[x]
            except KeyError: pass

        namespace['__slots__'] = tuple(discovered)

        fields = [x for x in discovered[:] if x not in namespace.defaults]

        namespace['__init__'] = _make_constructor(fields, namespace.defaults)
        result = type.__new__(cls, name, bases, dict(namespace))

        return result

    


class Struct(metaclass=StructMeta):

    def __init__(self, *args, **kw):
        super().__init__()

        if len(args) > len(self.__slots__):
            raise TypeError('__init__ expected up to {} arguments and received {}.'.format(
                len(self.__slots__), len(args)))

        init_count = -1

        for i, (member, arg) in enumerate(zip(self.__slots__, args)):
            setattr(self, member, arg)
            init_count = i
            
        uninit = list(self.__slots__[init_count+1:])


        for k, v in kw.items():
            try:
                uninit.remove(k)
            except ValueError:
                raise TypeError('Redundant initialization of {}'.format(k)) from None
            
            setattr(self, k, v)


        if uninit:
            raise TypeError('The following fields were not initialized: {}'.format(
                ', '.join(uninit)))


    def __repr__(self):
        return type(self).__name__ + \
                '(' + \
                ', '.join('{}={!r}'.format(slot, getattr(self, slot)) 
                          for slot in self.__slots__) +\
                ')'





class Point(Struct):
    x = ()
    y = ()

    def magnitude(self):
        import math
        return math.sqrt(self.x**2 + self.y**2)




