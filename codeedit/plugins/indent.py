from codeedit.api import interactive, BufferController
from codeedit.buffers import Cursor, Span
import re


TABSTOP = 4


def buftag_getter(tag, default):
    def result(bufctl):
        return bufctl.tags.get(tag, default)
    return result

get_tabstop         = buftag_getter('tabstop', TABSTOP)
get_shiftwidth      = buftag_getter('shiftwidth', TABSTOP)
get_commentchar     = buftag_getter('commentchar', '#')

def _change_line_indent(line, delta):
    # TODO tab support
    
    def replacement(match):
        indentation = match.group(0)
        if delta < 0:
            indentation = indentation[:delta]
        else:
            indentation += ' ' * delta

        return indentation

    result = re.sub(r'^(\s*)', replacement, line)
    print(repr(result))
    return result

@interactive('indent_block')
def indent_block(bctl: BufferController, levels=1):
    cc = Cursor(bctl.buffer).move(*bctl.canonical_cursor.pos)
    ac = Cursor(bctl.buffer).move(*bctl.anchor_cursor.pos) if bctl.anchor_cursor else None
    
    with bctl.history.transaction():
        if not ac:
            cc.insert('    ')
        else:
            text = ac.text_to(cc)
            indent_text = '\n'.join(_change_line_indent(line, levels * get_shiftwidth(bctl))
                                    for line in text.splitlines())
            ac.remove_to(cc)
            pos = ac.pos
            cc.insert(indent_text)

            bctl.canonical_cursor.pos = cc.pos
            bctl.anchor_cursor.pos = pos
            bctl.refresh_view(True)


def is_commented(span, comment_char):
    lines = 0
    commented_lines = 0
    for r in span.ranges:
        if re.match(r'^\s*' + re.escape(comment_char), r.line.text):
            commented_lines += 1
        lines += 1
    
    return commented_lines > max(min(0.9 * lines, lines-2), lines*0.5)

def comment(span, comment_char):
    for r in span.ranges:
        Cursor(span.buffer).move(r.y, 0).insert(comment_char + ' ')


def uncomment(span, comment_char):
    for r in span.ranges:
        match = re.match(r'^\s*' + re.escape(comment_char) +' ?', r.line.text)
        if match:
            start = Cursor(span.buffer).move(r.y, match.start())
            end = Cursor(span.buffer).move(r.y, match.end())
            start.remove_to(end)


@interactive('comment_toggle')
def comment_toggle(bctl: BufferController):
    comment_char = get_commentchar(bctl)
    try:
        sel = Span(bctl.canonical_cursor, bctl.anchor_cursor)
        with bctl.history.transaction():
            if is_commented(sel, comment_char):
                uncomment(sel, comment_char)
            else:
                comment(sel, comment_char)

        bctl.refresh_view(full=True)
    except:
        import logging
        logging.exception('comment toggle')
