from sphinx.application import Sphinx
from sphinx.domains.python import (PyClassmember, 
                                   PyClasslike,
                                   PythonDomain,
                                   ObjType,
                                   PyXRefRole,
                                   Index)
from sphinx.ext import autodoc
from stem.core.nconfig import Settings, Field
from stem.core.signal import Signal, InstanceSignal
import enum


class PatchedClassDocumenter(autodoc.ClassDocumenter):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def add_directive_header(self, sig):
        fname = self.format_name()
        self.add_line(fname, '<autodoc>')
        self.add_line('^' * len(fname), '<autodoc>')
        super().add_directive_header(sig)

autodoc.ClassDocumenter = PatchedClassDocumenter

class FieldDocumenter(autodoc.AttributeDocumenter):
    priority = 100
    objtype = 'setfield'
    directivetype = 'attribute'

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, Field)

    def format_name(self):
        if self.objpath:
            return self.objpath[-1]
        else:
            return '???'

    def format_signature(self):
        return ': ' + self.retann + ' = ' + repr(self.object.default)
    def import_object(self):
        res = super().import_object()
        self.retann = self.object.type.__name__ if self.object.type else 'any'
        return res


class EnumDocumenter(autodoc.ClassDocumenter):
    objtype = 'enum'
    member_order = 19

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, type) and issubclass(member, enum.Enum)

    def get_object_members(self, want_all):
        return False, [(k, v.value) 
                       for (k, v) in
                       self.object.__members__.items()]

    def filter_members(self, members, want_all):
        return [(name, member, True) for (name, member) in members]

#     @staticmethod
#     def get_attr(obj, name, *defargs):
#         """getattr() override for types such as Zope interfaces."""
#         return obj[name].value

class SignalDirective(PyClassmember):
    signal_prefix = 'signal '
    def needs_arglist(self):
        return True

    def get_signature_prefix(self, sig):
        return self.signal_prefix

    def get_index_text(self, modname, name_cls):
        name, cls = name_cls
        add_modules = self.env.config.add_module_names
        try:
            clsname, methname = name.rsplit('.', 1)
        except ValueError:
            if modname:
                return ('%s() (in module %s)') % (name, modname)
            else:
                return '%s()' % name
        if modname:
            return ('%s() (%s.%s signal)') % (methname, modname,
                                                     clsname)
        else:
            return ('%s() (%s signal)') % (methname, clsname)
# class FancyClassDirective(PyClasslike):
#     pass

class ClassSignalDirective(SignalDirective):
    signal_prefix = 'class-signal '
    def needs_arglist(self):
        return True

    def get_signature_prefix(self, sig):
        return self.signal_prefix

    def get_index_text(self, modname, name_cls):
        name, cls = name_cls
        add_modules = self.env.config.add_module_names
        try:
            clsname, methname = name.rsplit('.', 1)
        except ValueError:
            if modname:
                return ('%s() (in module %s)') % (name, modname)
            else:
                return '%s()' % name
        if modname:
            return ('%s() (%s.%s signal)') % (methname, modname,
                                                     clsname)
        else:
            return ('%s() (%s signal)') % (methname, clsname)

PythonDomain.directives['signal'] = SignalDirective
# PythonDomain.directives['classsignal'] = ClassSignalDirective
PythonDomain.directives['enum'] = PyClasslike
# PythonDomain.directives['settings'] = PyClasslike

PythonDomain.object_types['signal'] = ObjType('signal', 'sig', 'obj')
PythonDomain.object_types['classsignal'] = ObjType('classsignal', 'csig', 'obj')
PythonDomain.object_types['enum'] = ObjType('enum', 'enm', 'obj')
# PythonDomain.object_types['settings'] = ObjType('settings', 'stg', 'obj')

PythonDomain.roles['csig'] = PyXRefRole()
PythonDomain.roles['sig'] = PyXRefRole()
PythonDomain.roles['enm'] = PyXRefRole()

class SignalDocumenter(autodoc.MethodDocumenter):
    priority = 100
#     objtype = 'signal'
#     directivetype = 'signal'

    @classmethod
    def can_document_member(cls, member, membername,
                            isattr, parent):

        return (isinstance(member, (Signal))
                and not isinstance(parent, autodoc.ModuleDocumenter))

    def import_object(self):
        rv = super().import_object()

        if isinstance(rv, InstanceSignal):
            self.directivetype = 'classsignal'
            self.objtype = 'classsignal'
        else:
            self.directivetype = 'signal'
            self.objtype = 'signal'

        return rv

    def format_args(self):
        o = self.object._proto_func

        if autodoc.inspect.isbuiltin(o) or \
               autodoc.inspect.ismethoddescriptor(o):
            # cannot introspect arguments of a C function or method
            return None
        try:
            argspec = autodoc.getargspec(o)
        except TypeError:
            if (autodoc.is_builtin_class_method(o, '__new__') and
               autodoc.is_builtin_class_method(o, '__init__')):
                raise TypeError('%r is a builtin class' % o)

            # if a class should be documented as function (yay duck
            # typing) we try to use the constructor signature as function
            # signature without the first argument.
            try:
                argspec = autodoc.getargspec(o.__new__)
            except TypeError:
                argspec = autodoc.getargspec(o.__init__)
                if argspec[0]:
                    del argspec[0][0]
        args = autodoc.inspect.formatargspec(*argspec)
        # escape backslashes for reST
        args = args.replace('\\', '\\\\')
        return args

settings_list = set()

class SettingsDocumenter(autodoc.ClassDocumenter):
    priority = 100
    objtype = 'settings'
    directivetype = 'class'

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return (super().can_document_member(member, membername, isattr, parent) 
                and issubclass(member, Settings))

    def add_directive_header(self, sig):
        super().add_directive_header(sig)
        global settings_list
        settings_list.add(self.object_name)

        if hasattr(self.object, '_ns_'):
            self.add_line('', '<autodoc>')
            self.add_line('   Config Namespace: ``{}``'.format(self.object._ns_), '<autodoc>')

def skip_member_predicate(app, what, name, obj, skip, opts):
    if getattr(obj, '_sphinx_omit', False):
        return True
        

def setup(app):
    global sphinxapp
    sphinxapp = app
    autodoc.setup(app)
    autodoc.add_documenter(FieldDocumenter)
    autodoc.add_documenter(SettingsDocumenter)
    autodoc.add_documenter(SignalDocumenter)
    autodoc.add_documenter(EnumDocumenter)
    app.connect('autodoc-skip-member', skip_member_predicate)

