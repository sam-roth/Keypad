

import subprocess
from keypad.api import AttributedString, Cursor

from .bourne_model import BourneCodeModel, ShellCompletionResults

import logging

class GetCompletionsTask:
    def __init__(self, prefix):
        self.prefix = prefix

    def __call__(self, ns):
#         print(self.prefix)
        # take advantage of safe argument passing by providing the script on stdin rather than through
        # the argument array
        with subprocess.Popen(['fish',
                               '/dev/stdin',
                               self.prefix],
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE) as proc:
            out, err = proc.communicate(b'complete --do-complete=$argv[1]\n')

        output = []

#         print(out)
        for item in out.splitlines():
            left, *right = item.decode().split('\t', maxsplit=2)

            if not right:
                right = ['']
            
            output.append((AttributedString(left),
                           AttributedString(right[0])))

#         print(output)
        return output

class FishShellCompletionResults(ShellCompletionResults):
    def __init__(self, token_start, results, prox):
        try:
            super().__init__(token_start, [], prox)
            self.results = results
        except:
            logging.exception('error')
            raise


class FishCodeModel(BourneCodeModel):

    def completions_async(self, pos):
        '''
        Return a future to the completions available at the given position in the document.
        
        Raise NotImplementedError if not implemented.
        '''

        try:
            y0, x0 = pos
            c = Cursor(self.buffer).move(pos)
            prefix = c.line.text[:c.x]
    
            for ch in c.walk(-1):
                if ch.isspace() or c.y != y0:
                    break
    
            c.advance()

    
            return self._prox.submit(GetCompletionsTask(prefix),
                                     transform=lambda r: FishShellCompletionResults(c.pos, r,
                                                                                    self._prox))

        except:
            logging.exception('')
            raise
            
    
    
    
    