

import textwrap
import re

# from textwrap
_whitespace_only_re = re.compile('^[ \t*#/]+$', re.MULTILINE)
_leading_whitespace_re = re.compile('(^[ \t*#/]*)(?:[^ \t\n])', re.MULTILINE)


def common_indent(text):
    # This is mostly taken from textwrap.dedent

    # Look for the longest leading string of spaces and tabs common to
    # all lines.
    margin = None
    text = _whitespace_only_re.sub('', text)
    indents = _leading_whitespace_re.findall(text)
    for indent in indents:
        if margin is None:
            margin = indent

        # Current line more deeply indented than previous winner:
        # no change (previous winner is still on top).
        elif indent.startswith(margin):
            pass

        # Current line consistent with and no deeper than previous winner:
        # it's the new winner.
        elif margin.startswith(indent):
            margin = indent

        # Current line and previous winner have no common whitespace:
        # there is no margin.
        else:
            margin = ""
            break

    return margin or ''

def strip_indent(text, indent):
    return re.sub(r'(?m)^' + indent, '', text)

def add_indent(text, indent):
    return '\n'.join(indent + line for line in text.splitlines()) + '\n'

class ParagraphWrapper(textwrap.TextWrapper):
    def wrap(self, text):
        """Override textwrap.TextWrapper to process 'text' properly when
        multiple paragraphs present"""
        # This is shamelessly stolen from
        # http://code.activestate.com/recipes/358228-extend-textwraptextwrapper-to-handle-multiple-para/
        para_edge = re.compile(r"(\n\s*\n)", re.MULTILINE)
        paragraphs = para_edge.split(text)
        wrapped_lines = []
        for para in paragraphs:
            if para.isspace():
                if not self.replace_whitespace:
                    # Do not take the leading and trailing newlines since
                    # joining the list with newlines (as self.fill will do)
                    # will put them back in.
                    if self.expand_tabs:
                        para = para.expandtabs()
                    wrapped_lines.append(para[1:-1])
                else:
                    # self.fill will end up putting in the needed newline to
                    # space out the paragraphs
                    wrapped_lines.append('')
            else:
                wrapped_lines.extend(textwrap.TextWrapper.wrap(self, para))
        return wrapped_lines



def paragraph_fill(text, **kw):
    '''
    Like textwrap.fill, but respect paragraph (blank line) boundaries and
    preserve indentation.
    '''
    initial_indent = kw.get('initial_indent', '')
    subsequent_indent = kw.get('subsequent_indent', '')

    indent = common_indent(text)
    subsequent_indent = indent + subsequent_indent
    initial_indent = indent + initial_indent

    kw.update(initial_indent=initial_indent, 
              subsequent_indent=subsequent_indent)

    wrapper = ParagraphWrapper(**kw)
    return wrapper.fill(strip_indent(text, indent))


