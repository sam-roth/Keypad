
import re
import types

def placeholder_insert(cursor, text):
    '''
    Insert text at the given cursor, removing words enclosed with backticks and marking their positions
    in a returned SimpleNamespace.

    :type cursor: stem.buffers.cursor.Cursor
    '''

    parts = re.split('(`.*?`)', text)

    marks = {}
    for part in parts:
        if part.startswith('`') and part.endswith('`'):
            marks[part[1:-1]] = cursor.pos
        else:
            cursor.insert(part)
    return types.SimpleNamespace(**marks) 

    