

import yaml

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
    def __init__(self, type, default=None):
        '''
        Denote that the field should have the given type and default value.
        '''
        self.type = type
        self.default = default
        self.name = None

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


    def __set__(self, instance, value):
        instance._values_[self.name] = Conversions.convert(self.type, value)
    
_config_namespaces = {}        

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
            yaml.add_representer(result, result.to_yaml)
            yaml.add_constructor(result.yaml_tag, result.from_yaml)
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
            
    def load_yaml(self, source):
        for item in yaml.load(source):
            self.groups[type(item)] = item
    
    def dump_yaml(self, sink=None, **kw):
        return yaml.dump(list(self.groups.values()), sink, **kw)
    
    
Config.root = Config()
        

        
    
class ConfigGroup(metaclass=ConfigMeta): 
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
        result = cls()
        for k, v in loader.construct_mapping(node).items():
            result._fields_[k].__set__(result, v)
        return result
    

import pathlib
import pprint

Conversions.register(pathlib.Path, pathlib.Path)

class Example(ConfigGroup):
    _ns_ = 'stem.test_config'

    tab_stop = Field(int, 4)
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
    clang: 1



'''
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