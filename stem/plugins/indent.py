from stem.api import interactive, BufferController
from stem.control.interactive import run as run_interactive
from stem.buffers import Cursor, Span
import re


TABSTOP = 4


def buftag_getter(tag, default):
    def result(bufctl):
        return bufctl.tags.get(tag, default)
    return result

get_tabstop         = buftag_getter('tabstop', TABSTOP)
get_shiftwidth      = buftag_getter('shiftwidth', TABSTOP)
get_commentchar     = buftag_getter('commentchar', '#')

def _change_line_indent(line, delta, *, absolute=None):
    # TODO tab support
    
    def replacement(match):
        indentation = match.group(0)
        if absolute is not None:
            indentation = ' ' * absolute
        elif delta < 0:
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


@interactive('align')
def align(bctl: BufferController):
    cc = Cursor(bctl.buffer).move(*bctl.canonical_cursor.pos)
    if cc.pos[0] == 0:
        return

    cc.up()

    leading_spaces = 0
    unmatched_parens = []
    for i, ch in enumerate(cc.line.text):
        if ch.isspace():
            leading_spaces += 1
        elif ch in '({[':
            unmatched_parens.append(i + 1)
        elif ch in ')}]':
            if unmatched_parens:
                unmatched_parens.pop()
    
    if unmatched_parens:
        align_column = unmatched_parens[-1]
    else:
        align_column = leading_spaces
    
    with bctl.history.rec_transaction():
        cc.down().home()
        ac = cc.clone()
        cc.end()
        line = _change_line_indent(ac.text_to(cc), delta=None, absolute=align_column)
        ac.remove_to(cc)
        ac.insert(line)


@interactive('newline_aligned')
def newline_aligned(bctl: BufferController):
    with bctl.history.transaction():
        bctl.canonical_cursor.insert('\n')
        align(bctl)
        bctl.canonical_cursor.home()
    run_interactive('cursor', 'move', 'advance_word')


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
