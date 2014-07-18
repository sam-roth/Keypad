
import textwrap
import string

import pathlib, contextlib

from keypad import buffers, control, core, options

from keypad.util import listdict
from keypad.core import Keys
from keypad.testutil import mocks
from keypad.buffers.testutil import placeholder_insert
from keypad.plugins.pymodel import PythonCodeModelPlugin


PythonCodeModelPlugin(None).attach()

def make_bctl():

        conf = core.Config.root.derive()
        settings = options.GeneralSettings.from_config(conf)
        settings.indent_text = '\t'


        bctl = control.BufferController(buffer_set=None,
                                        view=mocks.MockCodeView(),
                                        buff=buffers.Buffer(),
                                        provide_interaction_mode=True,
                                        config=conf)

        bctl.path = pathlib.Path('/tmp/a.py')
        return bctl




def text2keys(text):
    for ch in text:
        if ch == '\n':
            yield Keys.return_
        elif ch == '\t':
            yield Keys.tab
        elif ch in shifted_keys:
            yield core.SimpleKeySequence(core.Modifiers.Shift, ord(ch))
        else:
            yield core.SimpleKeySequence(0, ord(ch.upper()))

def typekeys(bctl, *textandkeys):
    for part in textandkeys:
        if isinstance(part, str):
            bctl.view.press(*text2keys(part))
        else:
            bctl.view.press(part)

def addtext(bctl, text):
    return placeholder_insert(buffers.Cursor(bctl.buffer),
                              textwrap.dedent(text))



shifted_keys = listdict.ListDict()
for key in '~!@#$%^&*()_+|{}:"<>?' + string.ascii_uppercase:
    shifted_keys[key] = None


def test_simple():
    with make_bctl() as bctl:
        text = 'def foo():`c`'

        cursors = addtext(bctl, text)
        bctl.selection.move(cursors.c)
        typekeys(bctl, Keys.return_, 'abcd')

        assert bctl.buffer.text == 'def foo():\n\tabcd'

def test_indent_align():
    with make_bctl() as bctl:
        text = 'def foo():\n\tdef bar(a,`c`'

        cursors = addtext(bctl, text)
        expected = bctl.buffer.text + '\n\t        b'
        bctl.selection.move(cursors.c)
        typekeys(bctl, Keys.return_, 'b')

        assert bctl.buffer.text == expected



def test_quoted_mismatch():
    with make_bctl() as bctl:
        typekeys(bctl, '\t\'(\'\n', Keys.backspace, '\'{}')
        assert not bctl.buffer.lines[1].text.startswith('\t')

    


