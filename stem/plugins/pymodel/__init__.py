
from stem.api import Plugin, register_plugin, Filetype

def make_python_code_model(*args):
    from .pymodel import PythonCodeModel
    return PythonCodeModel(*args)


@register_plugin
class PythonCodeModelPlugin(Plugin):
    name = 'Python code model'
    author = 'Sam Roth'

    def attach(self):
        Filetype('python', 
                 suffixes=('.py',),
                 code_model=make_python_code_model)

    def detach(self):
        pass

