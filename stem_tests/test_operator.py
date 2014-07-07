


orig_text = '''
....abcd
....efgh
..
.....ijkl
.mnop
'''

after_indent = '''
........abcd
........efgh

.........ijkl
.....mnop
'''

after_dedent = '''
abcd
efgh

.ijkl
mnop
'''

from stem.buffers.buffer import Buffer
from stem.buffers.operator import indent, enclosed_span, line_region, prepend, replace
from stem.buffers.cursor import Cursor
from stem.buffers.span import Span
from stem.core.default_code_model import DefaultCodeModel
from stem.buffers import testutil
import textwrap

def todot(x):
    return x.replace(' ', '.')

def fromdot(x):
    return x.replace('.', ' ')

def test_indent():
    buff = Buffer.from_text(fromdot(orig_text))

    region = Span(Cursor(buff),
                  Cursor(buff).last_line().end())


    indent(region, indent_string='    ')

    assert after_indent == todot(buff.text)


def test_dedent():
    buff = Buffer.from_text(fromdot(orig_text))

    region = Span(Cursor(buff),
                  Cursor(buff).last_line().end())


    indent(region, indent_string='    ', levels=-1)

    assert after_dedent == todot(buff.text)


def test_remove_in_parens():
    text_in = '''
    (foo (ba`c`r
        baz
        quux
    ))
    '''

    text_out = '''
    (foo ())
    '''

    buff = Buffer()
    buff.code_model = DefaultCodeModel(buff, None)
    placeholders = testutil.placeholder_insert(Cursor(buff), text_in)

    c = Cursor(buff, placeholders.c)

    enclosed_span(c).remove()

    assert buff.text == text_out


def test_line_vector_insert():

    text_in = '''\
    oo
    ar
    az'''

    text_out = '''\
    foo
    far
    faz'''

    buff = Buffer.from_text(textwrap.dedent(text_in))
    reg = line_region(Span(Cursor(buff),
                           Cursor(buff).last_line().end()))
    prepend(reg, 'f')

    assert buff.text == textwrap.dedent(text_out)

def test_line_vector_replace():

    text_in = '''\
    oo
    ar
    az'''

    text_out = '''\
    foo
    foo
    foo'''

    buff = Buffer.from_text(textwrap.dedent(text_in))
    reg = line_region(Span(Cursor(buff),
                           Cursor(buff).last_line().end()))
    
    replace(reg, 'foo')

    assert buff.text == textwrap.dedent(text_out)


