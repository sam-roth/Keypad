
from keypad.api import (Plugin, 
                        register_plugin,
                        Filetype,
                        command,
                        interactive,
                        errors)

from .pymodel import PythonCodeModel
def make_python_code_model(*args):
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

    @command('pyedit')
    def pyedit(self, _: object, name):
        '''
        :pyedit name

        Open the source for the Python module with the given name.
        '''
        import jedi

        # based on :PyImport from vim-jedi

        sc = jedi.Script('import {}'.format(name))
        try:
            compl = sc.goto_assignments()[0]
        except IndexError:
            raise errors.NameNotFoundError('Name not found: {!r}'.format(name)) from None
        else:
            if compl.in_builtin_module():
                raise errors.NameNotFoundError('Module is builtin: {!r}'.format(name))
            else:
                interactive.run('edit', compl.module_path)

#                 
#     @command('rename')
#     def rename(self, cm: PythonCodeModel, name):
#         from keypad import api
#         bctl = self.app.find_object(api.BufferController)
#         cm.rename(bctl.selection.pos, name)
# 

