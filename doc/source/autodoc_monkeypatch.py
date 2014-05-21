
from sphinx.ext import autodoc

class PatchedClassDocumenter(autodoc.ClassDocumenter):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        
    def add_directive_header(self, sig):
        fname = self.format_name()
        self.add_line(fname, '<autodoc>')
        self.add_line('^' * len(fname), '<autodoc>')
        super().add_directive_header(sig)
                
autodoc.ClassDocumenter = PatchedClassDocumenter

setup = autodoc.setup
