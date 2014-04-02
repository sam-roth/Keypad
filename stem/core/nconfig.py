

import yaml
import warnings
import enum
import types



class Conversions:   
    _entries = {}
    
    @classmethod
    def register(cls, ty, converter):
        cls._entries[ty] = converter
        
    @classmethod
    def convert(cls, ty, value):
        if isinstance(value, ty):
            return value
        else:
            try:
                converter = cls._entries[ty]
                return converter(value)
                
            except (KeyError, TypeError, ValueError):
            
                raise TypeError('Cannot convert {!r} to {}.'.format(
                    value,
                    ty.__name__
                ))

class Field(object):
    def __init__(self, type, default=None, safe=False):
        '''
        Denote that the field should have the given type and default value.
        
        `safe` fields are ones that are "safe" to read from untrusted configuration
        files. ("Safe" might be sanely interpreted as meaning that no injection of arbitrary
        code is possible, and no data loss will occur.)
        '''
        self.type = type
        self.default = default
        self.name = None
        self.safe = safe
        
    def __repr__(self):
        return 'Field{!r}'.format((self.type, self.default, self.name))
        
    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            try:
                return instance._values_[self.name]
            except KeyError:
                if instance._chain_ is not None:
                    return getattr(instance._chain_, self.name)
                else:
                    return self.default
                    
    def clear(self, instance):
        del instance._values_[self.name]

    def __set__(self, instance, value):
        instance._values_[self.name] = Conversions.convert(self.type, value)
        
    def set_safely(self, instance, value):
        if self.safe:
            self.__set__(instance, value)
        else:
            warnings.warn(UserWarning('Field {} is not marked as safe; it is not permitted ' 
                                      'to be read from an untrusted configuration file.'.format(self.name)))
                                    
        

    def _test_iterable(self, xs):
        try:
            iter(xs)
            return True
        except TypeError:
            warnings.warn(UserWarning('Can only append or remove a list from {!r}'.format(self.name)))
            return False
            
    def set(self, instance, value, safe):
        if safe:
            self.set_safely(instance, value)
        else:
            self.__set__(instance, value)
    
                
    def append(self, instance, value, safe):
        if not self._test_iterable(value): return
        
        if issubclass(self.type, tuple):
            self.set(instance, self.__get__(instance, None) + value, safe)
        elif issubclass(self.type, frozenset):
            self.set(instance, self.__get__(instance, None) | frozenset(value), safe)
        else:
            warnings.warn(UserWarning('Field {} cannot be appended.'.format(self.name)))
    
    def remove(self, instance, value, safe):
        if not self._test_iterable(value): return
    
        if issubclass(self.type, tuple):
            curval = list(self.__get__(instance, None))
            for val in value:
                try:
                    curval.remove(val)
                except ValueError:
                    return
            self.set(instance, tuple(curval), safe)
        elif issubclass(self.type, frozenset):
            self.set(instance, self.__get__(instance, None) - frozenset(value), safe)
        else:
            warnings.warn(UserWarning('Field {} cannot be removed from.'.format(self.name)))            
                                    
class SafetyContext(enum.IntEnum):
    safe = 1
    unsafe = 2
    either = safe | unsafe
    neither = 0
    
    
class EnumField(Field):
    def __init__(self, type, choices, default=None, safe=False, allow_others=SafetyContext.neither):
        super().__init__(type, default, safe)
        self.choices = dict(choices)
        self.allow_others = allow_others
    
    def _set(self, instance, value, context):
        if value in self.choices.values():
            super().__set__(instance, value)
        elif value in self.choices:
            super().__set__(instance, self.choices[value])
        elif self.allow_others & context:
            super().__set__(instance, value)
        else:
            raise ValueError('Invalid value for enumeration field when set from this context.')
        
    def __set__(self, instance, value):
        self._set(instance, value, SafetyContext.safe)
    
    def set_safely(self, instance, value):
        if self.safe:
            self._set(instance, value, SafetyContext.unsafe)
        else:
            super().set_safely(instance, value)
        
import logging
class SetField(Field):
    def __init__(self, etype, default=frozenset(), choices=None, safe=False, allow_others=SafetyContext.neither):
        super().__init__(frozenset, default, safe)
        self.choices = dict(choices) if choices is not None else None
        self.allow_others = allow_others
        self.etype = etype
        
    def _set(self, instance, values, context):
#         print(values)
        normvals = []
        
        if self.choices is not None:
            for value in values:
                if value in self.choices.values():
                    normvals.append(value)
                elif value in self.choices:
                    normvals.append(self.choices[value])
                elif self.allow_others & context:
                    normvals.append(Conversions.convert(self.etype, value))
                else:
                    raise ValueError('invalid value for set field when set from this context')
        else:
            normvals = [Conversions.convert(self.etype, v) for v in values]
            
        super().__set__(instance, self.__get__(instance, None) | frozenset(normvals))
        
    def __set__(self, instance, value):
        try:
            self._set(instance, value, SafetyContext.safe)
        except:
            logging.exception('setfield')
            
    def set_safely(self, instance, value):
        try:
            if self.safe:
                self._set(instance, value, SafetyContext.unsafe)
            else:
                super().set_safely(instance, value)        
                
        except:
            logging.exception('setfield')


_config_namespaces = {}        

def namespaces():
    return types.MappingProxyType(_config_namespaces)

class ConfigMeta(type):
    def __new__(cls, name, bases, classdict):
        fields = {}
        for key, val in classdict.items():
            if isinstance(val, Field):
                val.name = key
                fields[val.name] = val
        

        classdict['_fields_'] = fields
        
        if '_ns_' in classdict:
            classdict['yaml_tag'] = '!' + classdict['_ns_']
        
        
        result = super().__new__(cls, name, bases, classdict)
        
        if hasattr(result, '_ns_'):
#             yaml.add_representer(result, result.to_yaml)
#             yaml.add_constructor(result.yaml_tag, result.from_yaml)
#             yaml.SafeLoader.add_constructor(result.yaml_tag, result.from_yaml_safely)
            _config_namespaces[result._ns_] = result
        
        return result

class Config(object):

    def __init__(self):
        self.groups = {}
        self.chain = None

    def derive(self):
        result = Config()
        result.chain = self
        return result
            
    def dump_yaml(self, sink=None, **kw):
        return yaml.dump(list(self.groups.values()), sink, **kw)
    
    def load_yaml(self, source, safe):
        if safe:
            items = yaml.safe_load(source)
        else:
            items = yaml.load(source)

        if not isinstance(items, dict):
            warnings.warn(UserWarning('Top level of YAML configuration file must be dictionary. Got {!r}.'
                                      .format(type(items).__name__)))
            return

        for k, v in items.items():
            try:
                ns = _config_namespaces[k]
            except KeyError:
                warnings.warn(UserWarning('Unknown config namespace: {!r}.'.format(ns)))
            else:
                settings = ns.from_config(self)
                settings.update(v, safe)
    def load_yaml_safely(self, source):
        return self.load_yaml(source, safe=True)

#         try:
#             print(items[0]._values_)
#         except:
#             pass
#        if items is None: return
#        for item in items:
#            item_type = type(item)
#            item_type.from_config(self).merge_from(item)
#            
#             if item_type in self.groups:
#                 self.groups[item_type].merge_from(item)
#             else:
#                 self.groups[item_type] = item
            
Config.root = Config()
        

        
    
class Settings(metaclass=ConfigMeta): 
    '''
    A group of configuration values.
    
    >>> class AppConfig(ConfigGroup):
    ...     _ns_ = 'myapp.AppConfig'
    ...     max_undo = Field(int, 1000)
    ...
    >>> global_conf = Config()
    >>> global_app_conf = AppConfig.from_config(global_conf)
    >>> window_conf = global_conf.derive()
    >>> window_app_conf = AppConfig.from_config(window_conf)
    >>> global_app_conf.max_undo
    1000
    >>> global_app_conf.max_undo = 10
    >>> window_app_conf.max_undo
    10
    >>> window_app_conf.max_undo = 100
    >>> window_app_conf.max_undo
    100
    >>> global_app_conf.max_undo
    10    
    '''
    
    def __init__(self):
        super().__init__()
        self._values_ = {}
        self._chain_ = None
    
    @classmethod
    def from_config(cls, config):
        if cls in config.groups:
            return config.groups[cls]
        elif config.chain is not None:
            chain = cls.from_config(config.chain)
            result = chain.derive()
            config.groups[cls] = result
            return result
        else:
            result = cls()
            config.groups[cls] = result
            return result            
    
    def derive(self):
        res = type(self)()
        res._chain_ = self
        return res
        
    def to_dict(self):
        return self._values_
        
    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping(cls.yaml_tag, data.to_dict())
        
    @classmethod
    def from_yaml(cls, loader, node):
        return cls().self_from_yaml(loader, node)
        
    def self_from_yaml(self, loader, node):
        result =  self
        for k, v in loader.construct_mapping(node).items():
            result._fields_[k].__set__(result, v)
        return result
    
    @classmethod
    def from_yaml_safely(cls, loader, node):
        result = cls()
        result.self_from_yaml_safely(loader, node)
        return result

    def self_from_yaml_safely(self, loader, node):
        result = self

        for k, v in loader.construct_mapping(node, deep=True).items():
#             print('a', k,v)
            result._fields_[k].set_safely(result, v)
        return result
        
    def merge_from(self, other):
        for k, v in other._values_.items():
            self._fields_[k].__set__(self, v)

    def update(self, mapping, safe):
        for k, v in mapping.items():
            parts = k.split('.')
            if len(parts) == 1:
                try:
                    field = self._fields_[k]
                except KeyError:
                    warnings.warn(UserWarning('Unknown configuration key {!r}.'.format(k)))
                else:
                    field.set(self, v, safe)
                    
            elif len(parts) == 2:
                k, m = parts
                try:
                    field = self._fields_[k]
                except KeyError:
                    warnings.warn(UserWarning('Unknown configuration key {!r}.'.format(k)))
                else:
                    if m == 'add':
                        field.append(self, v, safe)
                    elif m == 'remove':
                        field.remove(self, v, safe)
                    else:
                        warnings.warn(UserWarning('Unknown method {m!r} for field {k!r}'.format(**locals())))
            else:
                warnings.warn(UserWarning('Too many dots in name {!r}.'.format(k)))


    
#     def clear(self, name):
#         self._fields_[k].clear()

ConfigGroup = Settings # deprecated alias

import pathlib
import pprint

Conversions.register(pathlib.Path, pathlib.Path)

class Example(ConfigGroup):
    _ns_ = 'stem.test_config'

    tab_stop = Field(int, 4, safe=True)
    libpath  = Field(pathlib.Path)
    
class OtherExample(ConfigGroup):
    _ns_ = 'stem.other_test_config'
    
    clang = Field(str)


# print(Example.yaml_tag)
# yaml.add_representer(Example, Example.to_yaml)

def path_rep(dumper, data):
    return dumper.represent_scalar('!path', str(data))

def path_cons(loader, node):
    return pathlib.Path(loader.construct_scalar(node))
    
yaml.add_multi_representer(pathlib.Path, path_rep)
yaml.add_constructor('!path', path_cons)
# 
# conf = Config()
# confd = conf.derive()
# 
# base = Example.from_config(conf)
# deriv = Example.from_config(confd)
# deriv.tab_stop = 2
# base.tab_stop = 8
# deriv.libpath = '/lib/library.dylib'
# 
# print(conf.dump_yaml())
# y = confd.dump_yaml()
# print(y)
# 
# confr = Config()
# confr.load_yaml(y)
# print(confr.dump_yaml())
# 
testdoc = '''

- !stem.test_config
    libpath: /lib/library.dylib
    tab_stop: 3


- !stem.other_test_config
    clang: 'a'



'''
if __name__ == '__main__':
    conf = Config()
    conf.load_yaml_safely(testdoc)
    import pprint
    tc = Example.from_config(conf)
    pprint.pprint(tc.to_dict())
    
# conf = Config()
# conf.load_yaml(testdoc)
# 
# ex = Example.from_config(conf)
# print(ex.libpath)
# print(ex.tab_stop)
# 
# ex2 = OtherExample.from_config(conf)
# print(ex2.clang)

# print(deriv.tab_stop)
# print(yaml.load(yaml.dump(dict(base=base, deriv=deriv))))


# deriv._chain_ = base

# pprint.pprint(base.to_dict())

# pprint.pprint(deriv.to_dict())

# print(yaml.dump(base.to_dict()))
# print(yaml.dump(deriv.to_dict()))
