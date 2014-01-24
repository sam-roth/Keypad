


from . import interactive

import shlex

class CommandLineInterpreter(object):
    def exec(self, first_responder, cmdline):
        tokens = list(shlex.shlex(cmdline))
        interactive.dispatcher.dispatch(first_responder, *tokens)
        #interactive.dispatcher.dispatch(first_responder, cmdline.strip())
    


