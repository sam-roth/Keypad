'''
Lexer for Bourne shells.
'''

import re
from stem.plugins.semantics.syntaxlib import keyword, regex, region, Lexer

class HeredocEndLexer(Lexer):
    def __init__(self, text, attrs):
        super().__init__(attrs)
        self.text = text


    def guard_match(self, string, start, stop):
        return None

    def exit_match(self, string, start, stop):

        index = string.text[start:].find(self.text)

        if index >= 0:
            return index + start, index + len(self.text) + start
        else:
            return None

class HeredocStartLexer(Lexer):
    rgx = re.compile(r'<<-?\s*(\'?)\\?(\w+)') #[\w\W]+?')

    def guard_match(self, string, start, stop):
        match = self.rgx.search(
            string.text,
            start, 
            stop
        )



        if match is None:
            return None
        else:
            self.eof_pat = match.group(2)
            try:
                return match.start('body'), match.end('body')
            except LookupError:
                return match.start(), match.end()

    def exit_match(self, string, start, stop):
        return None


    def enter(self):
        return HeredocEndLexer(self.eof_pat, self.attrs)



# based on https://bitbucket.org/birkenfeld/pygments-main/src/
# 2ba9b53c87eeed24f7c5d2895ca27e637bca40a1/pygments/lexers/
# shell.py?at=default


FUNCTION    = dict(lexcat='function')    
KEYWORD     = dict(lexcat='keyword')
ESCAPE      = dict(lexcat='escape')
STRING      = dict(lexcat='literal')
NUMBER      = dict(lexcat='literal')
COMMENT     = dict(lexcat='comment')
DOC         = dict(lexcat='docstring')
PREPROC     = dict(lexcat='preprocessor')
TODO        = dict(lexcat='todo')
BUILTIN     = dict(lexcat='preprocessor')


Builtin = regex(r'\b(alias|bg|bind|break|builtin|caller|cd|command|compgen|'
                r'complete|declare|dirs|disown|echo|enable|eval|exec|exit|'
                r'export|false|fc|fg|getopts|hash|help|history|jobs|kill|let|'
                r'local|logout|popd|printf|pushd|pwd|read|readonly|set|shift|'
                r'shopt|source|suspend|test|time|times|trap|true|type|typeset|'
                r'ulimit|umask|unalias|unset|wait)\s*\b(?!\.)',
                BUILTIN)

Keyword = regex(r'\b(if|fi|else|while|do|done|for|then|return|function|case|'
                r'select|continue|until|esac|elif)(\s*)\b',
                KEYWORD)



Escape = regex(r'\\[\w\W]', ESCAPE)


Heredoc = HeredocStartLexer(STRING)

DQStringEsc = regex(r'\\\\|\\[0-7]+|\\.', ESCAPE)



SQString = regex(r"(?s)\$?'(\\\\|\\[0-7]+|\\.|[^'\\])*'", STRING)


VarRef = regex(r'\$#?(\w+|.)', FUNCTION)
VarDecl = regex(r'^(?P<body>\s*#?(\w+|.)\s*)=', FUNCTION)




Comment = regex(r'#.*$', COMMENT)


Dollar = region(guard=regex(r'\$\('),
                exit=regex(r'\)'),
                contains=[],
                attrs=ESCAPE)



DQString = region(guard=regex(r'(?s)\$?"'),
                  exit=regex(r'"'),
                  contains=[DQStringEsc, VarRef, Dollar],
                  attrs=STRING)

Shell = region(guard=None,
               exit=None,
               contains=[Keyword, Comment, Builtin,
                         Escape, Heredoc, SQString, DQString,
                         VarRef, VarDecl, Dollar])

Dollar.contains += Shell.contains
