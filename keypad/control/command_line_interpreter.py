


from . import interactive

import shlex

class CommandLineInterpreter(object):

    @staticmethod
    def _lex(cmdline):
        lexer = shlex.shlex(cmdline)
        lexer.whitespace_split = True
        return list(lexer)

    def exec(self, first_responder, cmdline):
        tokens = self._lex(cmdline)
        
        if tokens and all(c.isnumeric() for c in tokens[0]):
            tokens = ['line'] + tokens # entering a number goes to a line of the file
            
        interactive.dispatcher.dispatch(first_responder, *tokens)
    


