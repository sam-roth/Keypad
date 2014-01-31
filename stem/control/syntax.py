
from .. import buffers
import re
import keyword

def highlight_kw(kwds):
    return highlight_regex('|'.join(r'\b' + k + r'\b' for k in kwds))


def highlight_regex(regex, flags=0):
    rgx = re.compile(regex, flags)

    def result(astr, **attrs):
        for match in rgx.finditer(astr.text):
            for attr, val in attrs.items():
                astr.set_attribute(match.start(), match.end(), attr, val)

    return result


_python_kwlist = frozenset(keyword.kwlist) - frozenset('from import None False True'.split())
_python_kw_highlighter = highlight_kw(_python_kwlist)
_d_string_highlighter = highlight_regex(r'"([^"]|\\")*"')
_q_string_highlighter = highlight_regex(r"'([^']|\\')*'")
_python_func_highlighter = highlight_regex(
    r"""

      (?<= def  ) \s+\w+        
    | (?<= class) \s+\w+
    | (?<= @    ) (\w|\.)+      # decorators
    | (?<= @    ) (\w|\.)+
    """,
    re.VERBOSE
)
_python_morefunc_highlighter = highlight_kw('None False True'.split())
_python_import_highlighter = highlight_regex(r'\bfrom\b|\bimport\b|@')



def python_syntax(buff):

    for line in buff.lines:
        if not line.caches.get('polished', False):
            line.set_attribute('color', None)
            line.set_attribute('bgcolor', None)

            _python_kw_highlighter(line, color='#859900')
            _python_func_highlighter(line, color='#268bd2')
            _python_morefunc_highlighter(line, color='#268BD2')
            _python_import_highlighter(line, color='#cb4b16')
            _d_string_highlighter(line, color='#2AA198')
            _q_string_highlighter(line, color='#2AA198')

            for match in re.finditer(r'#.*', line.text):
                attrs = dict(line.attributes(match.start()))
                if attrs.get('color') is None:
                    line.set_attribute(match.start(), match.end(), 'color', '#586e75')

            line.caches['polished'] = True
    

