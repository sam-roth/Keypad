




from stem.api import autoconnect, BufferController
from stem.buffers import Buffer, Cursor

def suite_first_line_indent(curs, indent='    '):
    '''
    Returns the appropriate indentation for the current cursor line if the
    current cursor line begins a suite, otherwise None.

    :type curs: stem.buffers.Cursor

    >>> buff = Buffer.from_text('def foo():\\n')
    >>> buff_end = buff.end_pos
    >>> curs = Cursor(buff).move(buff_end)
    >>> suite_first_line_indent(curs)
    '    '
    '''

    curs = curs.clone()

    if curs.y == 0:
        return None

    curs.up()
    
    if not curs.searchline(r':\s*$'):
        return None

    cur_indent_match = curs.searchline('^\s*')
    
    if cur_indent_match:
        cur_indent = cur_indent_match.group(0)
    else:
        cur_indent = ''
    
    
    return cur_indent + indent



@autoconnect(BufferController.user_changed_buffer,
             lambda tags: tags.get('syntax') == 'python')
def pyindent(bufctl, chg):
    if chg.insert.endswith('\n'):
        curs = Cursor(bufctl.buffer).move(chg.insert_end_pos)
        indent = suite_first_line_indent(curs)

        if indent is not None:
            leading_space_match = curs.searchline(r'^\s*')
            if leading_space_match is not None:
                curs.home()
                end = curs.clone().right(leading_space_match.end())
                curs.remove_to(end)
            curs.insert(indent)
        
