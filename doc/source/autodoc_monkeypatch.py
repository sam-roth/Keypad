from sphinx.application import Sphinx

from sphinx.ext import autodoc
from stem.core.nconfig import Settings, Field



class PatchedClassDocumenter(autodoc.ClassDocumenter):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def add_directive_header(self, sig):

#         if Settings in self.object.__bases__:
#             sphinxapp.warn('Found settings: ' + repr(self.object))
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
        res = isinstance(member, Field)
        if res:
            sphinxapp.warn('FieldDocumenter ' + repr(member))
        return res
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

class SettingsDocumenter(autodoc.ClassDocumenter):
    priority = 100
    objtype = 'settings'
    directivetype = 'class'

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        res = super().can_document_member(member, membername, isattr, parent) and issubclass(member, Settings)
        if res:
            sphinxapp.warn('SettingsDocumenter: ' + str(member))
        return res
    def add_directive_header(self, sig):
        super().add_directive_header(sig)
        if hasattr(self.object, '_ns_'):
            self.add_line('', '<autodoc>')
            self.add_line('   Config Namespace: ``{}``'.format(self.object._ns_), '<autodoc>')



def setup(app):
    global sphinxapp
    sphinxapp = app
    autodoc.setup(app)
    autodoc.add_documenter(FieldDocumenter)
    autodoc.add_documenter(SettingsDocumenter)
#     app.add_autodocumenter(SettingsDocumenter)
#     app.add_autodocumenter(FieldDocumenter)