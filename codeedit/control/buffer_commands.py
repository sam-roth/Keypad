
from .interactive import interactive
from .buffer_controller import BufferController


@interactive('write')
def write(buff: BufferController, path: str=None):
    buff.write_to_path(buff.path)


@interactive('clear')
def clear(buff: BufferController, path: str=None):
    with buff.history.transaction():
        buff.clear()


@interactive('lorem')
def lorem(buff: BufferController):
    from . import lorem
    with buff.history.transaction():
        buff.canonical_cursor.insert(lorem.text_wrapped)


@interactive('py')
def eval_python(first_responder: object, *python_code):
    code = ' '.join(python_code)

    print(code)

import ast

@interactive('tag')
def add_tag(buff: BufferController, key, value):
    buff.add_tags(**{key: ast.literal_eval(value)})

@interactive('untag', 'unt')
def add_tag(buff: BufferController, key):
    buff.remove_tags([key])

