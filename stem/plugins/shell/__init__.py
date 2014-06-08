from stem.api import (Plugin,
                      register_plugin,
                      Filetype)


@register_plugin
class ShellCodeModelPlugin(Plugin):
    name = 'Shell Code Model'
    author = 'Sam Roth <sam.roth1@gmail.com>'

    @staticmethod
    def __make_bourne_code_model(*args, **kw):
        from . import bourne_model
        return bourne_model.BourneCodeModel(*args, **kw)


    def attach(self):
        Filetype('bourne_shell',
                 suffixes='.sh .bash .zsh'.split(),
                 code_model=self.__make_bourne_code_model)
        


    def detach(self):
        pass

