'''
New settings system.

Read :ref:`settings-howto` for an overview.
'''

import yaml
import warnings
import enum
import types
import importlib
import logging

from .signal import Signal

def _sphinx_omit(func):
    func._sphinx_omit = True
    return func

class Conversions:
    '''
    A namespace class for grouping conversion functions.


    .. Sphinx is having trouble with these classmethods, so I've
    .. duplicated them here.

    .. py:classmethod:: register(cls, ty, converter)

        Register a conversion function for a given type. There can be only
        one conversion function for a given type. If it is necessary to dispatch
        on the input type, that dispatch must be done within the conversion function.
        
        :param ty: The type being converted to.
        :param converter: The function responsible for the conversion.

    .. py:classmethod:: convert(cls, ty, value)

        Using the registered converters, convert a value to a given type 
        if necessary. No conversion is performed if the value is None or
        is already of the requested type.

        :param ty: The destination type.
        :param value: The object to convert.
        :raise TypeError: if there is no conversion to the given type


    '''
    _entries = {}
    
    @classmethod
    def register(cls, ty, converter):
        '''
        Register a conversion function for a given type. There can be only
        one conversion function for a given type. If it is necessary to dispatch
        on the input type, that dispatch must be done within the conversion function.

        :param ty: The type being converted to.
        :param converter: The function responsible for the conversion.
        '''
        cls._entries[ty] = converter
        
    @classmethod
    def convert(cls, ty, value):
        '''
        Using the registered converters, convert a value to a given type 
        if necessary. No conversion is performed if the value is None or
        is already of the requested type.

        :param ty: The destination type.
        :param value: The object to convert.
        :raise TypeError: if there is no conversion to the given type

        '''
        if value is None or isinstance(value, ty):
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

def _safe_float(x):
    if isinstance(x, (float, int)):
        return float(x)
    else:
        raise ValueError

def _safe_int(x):
    if isinstance(x, (float, int)):
        return int(x)
    else:
        raise ValueError
        
Conversions.register(int, _safe_int)
Conversions.register(float, _safe_float)

class Factory(object):
    def __init__(self, dotted_name):
        if isinstance(dotted_name, str):
            self.dotted_name = dotted_name
        else:
            self.dotted_name = '<value>'
            self._constructor = dotted_name
        
    @property
    def constructor(self):
        try:
            return self._constructor
        except AttributeError:
            head, tail = self.dotted_name.rsplit('.', 1)
            mod = importlib.import_module(head)
            self._constructor = getattr(mod, tail)
            return self._constructor
    
    def __call__(self, *args, **kw):
        return self.constructor(*args, **kw)
        
    def __repr__(self):
        if hasattr(self, '_constructor') and hasattr(self._constructor, '__qualname__'): 
            name = self._constructor.__qualname__
        else:
            name= self.dotted_name
        return 'Factory({!r})'.format(name)

Conversions.register(Factory, Factory)

class Field(object):
    '''
    Denote that the field should have the given type and default value.
    
    "Safe" fields are ones that are "safe" to read from untrusted configuration
    files. ("Safe" might be sanely interpreted as meaning that no injection of arbitrary
    code is possible, and no data loss will occur.)

    :param type: 
        The type of the field. If a value is assigned not of this type,
        the settings system will attempt to look up a conversion in
        `Conversions`. Failing that, a `TypeError` will be raised.
    :param default: The default value of the field.
    :param safe: Whether the field is "safe" to read from an untrusted configuration
                 file.
    :param docs: The docstring for the field.
    '''
    def __init__(self, type, default=None, safe=False,
                 docs=None):

        self.type = type
        self.default = Conversions.convert(type, default)
        self.name = None
        self.safe = safe
        self.__doc__ = docs
        
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
                    
    @_sphinx_omit
    def clear(self, instance):
        del instance._values_[self.name]

    def __set__(self, instance, value):
        conv_value = Conversions.convert(self.type, value)
        changed = conv_value != instance._values_.get(self.name, object())
        instance._values_[self.name] = conv_value
        instance.value_changed(self.name, conv_value)
        
    @_sphinx_omit
    def set_safely(self, instance, value):
        if self.safe:
            self.__set__(instance, value)
        else:
            warnings.warn(UserWarning('Field {} is not marked as safe; it is not permitted ' 
                                      'to be read from an untrusted configuration file.'.format(self.name)))
                                    
        

    @_sphinx_omit
    def _test_iterable(self, xs):
        try:
            iter(xs)
            return True
        except TypeError:
            warnings.warn(UserWarning('Can only append or remove a list from {!r}'.format(self.name)))
            return False
            
    @_sphinx_omit
    def set(self, instance, value, safe):
        if safe:
            self.set_safely(instance, value)
        else:
            self.__set__(instance, value)
    
                
    @_sphinx_omit
    def append(self, instance, value, safe):
        if not self._test_iterable(value): return
        
        if issubclass(self.type, tuple):
            self.set(instance, self.__get__(instance, None) + tuple(value), safe)
        elif issubclass(self.type, frozenset):
            self.set(instance, self.__get__(instance, None) | frozenset(value), safe)
        else:
            warnings.warn(UserWarning('Field {} cannot be appended.'.format(self.name)))
    
    @_sphinx_omit
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
@_sphinx_omit                       
class SafetyContext(enum.IntEnum):
    safe = 1
    unsafe = 2
    either = safe | unsafe
    neither = 0
    
@_sphinx_omit
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
        

@_sphinx_omit
class SetField(Field):
    def __init__(self, etype, default=frozenset(), choices=None, safe=False, allow_others=SafetyContext.neither):
        super().__init__(frozenset, default, safe)
        self.choices = dict(choices) if choices is not None else None
        self.allow_others = allow_others
        self.etype = etype
        
    def _set(self, instance, values, context):
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
    '''
    Return a mapping from configuration namespace names
    to Settings classes.
    '''
    return types.MappingProxyType(_config_namespaces)

class _ConfigMeta(type):
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
            _config_namespaces[result._ns_] = result
        
        return result

class Config(object):
    '''
    A class for holding configuration values (conceptually, at least).
    '''

    #: The root ancestor for all Config objects (by convention).
    root = None

    def __init__(self):
        self.groups = {}
        self.chain = None

    def derive(self):
        '''
        Create a dependent `Config` instance. Changes made in this instance will
        propagate to the dependent instance, but changes made in the dependent
        instance will not propagate back to this instance.
        '''
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
                warnings.warn(UserWarning('Unknown config namespace: {!r}.'.format(k)))
            else:
                settings = ns.from_config(self)
                settings.update(v, safe)
                
    def load_yaml_safely(self, source):
        return self.load_yaml(source, safe=True)
        
    def update(self, mapping, safe):
        for k, v in mapping.items():
            try:
                ns = _config_namespaces[k]
            except KeyError:
                raise KeyError('Unknown config namespace: {!r}.'.format(k))
            else:
                settings = ns.from_config(self)
                settings.update(v, safe)
                
    def get(self, namespace, key):
        return getattr(_config_namespaces[namespace].from_config(self), key)

Config.root = Config()
        

        
    
class Settings(metaclass=_ConfigMeta): 
    '''
    A schema for a group of settings.

    >>> class AppSettings(Settings):
    ...     _ns_ = 'myapp.AppSettings'
    ...     max_undo = Field(int, 1000)
    ...
    >>> global_conf = Config()
    >>> global_app_conf = AppSettings.from_config(global_conf)
    >>> window_conf = global_conf.derive()
    >>> window_app_conf = AppSettings.from_config(window_conf)
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
    
    @Signal
    def value_changed(self, fieldname, value):
        '''
        Emitted when a field value changes, even if it is changed in an
        ancestor configuration.

        :param fieldname: The name of the field that changed.
        :param value:     Its new value.
        '''
        
    def __on_chained_value_change(self, fieldname, value):
        self.value_changed(fieldname, getattr(self, fieldname))
    
    @classmethod
    def from_config(cls, config):
        '''
        Get the instance of this `Settings` class for the given 
        configuration.
        '''
        if config is None:
            config = Config.root
            
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
    
    @_sphinx_omit
    def derive(self):
        res = type(self)()
        res._chain_ = self
        self.value_changed += res.__on_chained_value_change
        return res

    def to_dict(self):
        return self._values_
        
    @_sphinx_omit
    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_mapping(cls.yaml_tag, data.to_dict())
        
    @_sphinx_omit
    @classmethod
    def from_yaml(cls, loader, node):
        return cls().self_from_yaml(loader, node)
        
    @_sphinx_omit
    def self_from_yaml(self, loader, node):
        result =  self
        for k, v in loader.construct_mapping(node).items():
            result._fields_[k].__set__(result, v)
        return result

    @_sphinx_omit
    @classmethod
    def from_yaml_safely(cls, loader, node):
        result = cls()
        result.self_from_yaml_safely(loader, node)
        return result

    @_sphinx_omit
    def self_from_yaml_safely(self, loader, node):
        result = self

        for k, v in loader.construct_mapping(node, deep=True).items():
            result._fields_[k].set_safely(result, v)
        return result
        
    @_sphinx_omit
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

    def __getstate__(self):
        return self._values_, self._chain_
    
    def __setstate__(self, value):
        v, c = value
        self._values_ = v
        self._chain_ = c
        if c is not None:
            c.value_changed += self.__on_chained_value_change


ConfigGroup = Settings # deprecated alias

import pathlib
import pprint

Conversions.register(pathlib.Path, pathlib.Path)
Conversions.register(tuple, tuple)

def _path_rep(dumper, data):
    return dumper.represent_scalar('!path', str(data))

def _path_cons(loader, node):
    return pathlib.Path(loader.construct_scalar(node))
    
yaml.add_multi_representer(pathlib.Path, _path_rep)
yaml.add_constructor('!path', _path_cons)
