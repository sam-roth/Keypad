

from .span import Span, Region
from .cursor import Cursor
from .buffer import Buffer

from ..options import GeneralSettings


def buffer(x):
    '''
    Get the buffer associated with the given Span, Region, or Selection.

    :rtype: keypad.buffers.buffer.Buffer
    '''
    if isinstance(x, Buffer):
        return x
    else:
        return x.buffer

def getregion(region):
    '''
    If the object has a .region attribute, it is used to obtain a region,
    otherwise a TypeError is raised.

    :rtype: keypad.buffers.span.Region
    '''

    if hasattr(region, 'region'):
        return region.region
    else:
        raise TypeError('Invalid region: %r' % region)

def code_model(x):
    '''
    If `x` is an object with an associated buffer and code model, 
    return the buffer's code model. Otherwise, fail.

    :rtype: keypad.abstract.code.AbstractCodeModel
    '''

    buff = buffer(x)
    if buff.code_model is None:
        from ..core.errors import NoCodeModelError
        raise NoCodeModelError
    else:
        return buff.code_model



def line_cursors(region):
    '''
    Yield cursors from contiguous lines from the region. 
    Lines are yielded even if the line only partially contained within the region.

    The cursor will be reused between iterations. Clone it if you don't want it moving.

    :rtype: [keypad.buffers.cursor.Cursor]
    '''

    region = getregion(region)
    buff = buffer(region)
    curs = Cursor(buff)

    for y, line, start_x, end_x in region.ranges:
        curs.move(line=y).home()
        yield curs

def line_region(region):
    '''
    Return a Region composed of the lines from a region.
    '''

    return Region(*(Span(c, c.clone().end())
                    for c in line_cursors(region)))


def indent(region, *, indent_string, levels=1):
    '''
    :param indent_string: The string that will be prepended to the indented lines.
    '''

    for cursor in line_cursors(region):

        # remove lines that solely consist of whitespace
        match = cursor.line_span_matching(r'^\s*$')
        if match: 
            match.remove()
        elif levels > 0:
            cursor.insert(indent_string * levels)
        else:
            match = cursor.line_span_matching(r'^\s+')
            if match:
                remove_count = min(len(match.text), -len(indent_string) * levels)
                match[:remove_count].remove()



def enclosed_span(cursor):
    '''
    Get the span enclosed by a pair of delimiters.
    The cursor is not modified.

    Precondition: The cursor belongs to a buffer with a code model.
    '''

    buff = buffer(cursor)
    cm = code_model(buff)

    obp = cm.open_brace_pos(cursor.pos) or (0, 0)
    cbp = cm.close_brace_pos(cursor.pos) or buff.end_pos

    return Span(Cursor(buff, obp).advance(1),
                Cursor(buff, cbp))

def prepend(region, text):
    '''
    Insert text before each span in a region.
    '''

    region = getregion(region)

    for span in region.spans:
        span.prepend(text)

def append(region, text):
    '''
    Insert text after each span in a region.
    '''

    for span in getregion(region).spans:
        span.append(text)

def replace(region, text):
    '''
    Replace each span in the region with the given text.
    '''
    for span in getregion(region).spans:
        span.text = text




