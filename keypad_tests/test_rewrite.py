
import pathlib
import textwrap

from keypad.abstract.rewriting import ReplaceFileRewrite
from keypad.buffers import Buffer, Cursor

def make_buffer():
    text = 'foo\nbar\nbaz'
    return Buffer.from_text(text)

def make_rewrite():
    text = 'foo\nquux\nbaz'
    # Use a file that cannot exist to avoid machine state upsetting tests.
    return ReplaceFileRewrite(pathlib.Path('/dev/null/does/not/exist'),
                              text)

def test_diff():
    buf = make_buffer()
    rw = make_rewrite()
    diff = rw.diff(buf)

    expected = '''\
    --- /dev/null/does/not/exist
    +++ /dev/null/does/not/exist
    @@ -1,3 +1,3 @@
     foo
    -bar
    +quux
     baz'''

    assert diff == textwrap.dedent(expected)

def test_perform():
    buf = make_buffer()
    rw = make_rewrite()

    expected = 'foo\nquux\nbaz'
    rw.perform(buf)
    
    assert buf.text == expected

