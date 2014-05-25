from stem.api import (BufferController,
                      Plugin,
                      command,
                      register_plugin,
                      Cursor,
                      Span,
                      Region,
                      errors)
                      
import re

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

@register_plugin
class CommentTogglePlugin(Plugin):
    name = 'Comment Toggle'
    author = 'Sam Roth <sam.roth1@gmail.com>'

    def attach(self):
        pass

    def detach(self):
        pass

    @command('comment_toggle')
    def comment_toggle(self, bctl: BufferController):
        if bctl.code_model is None:
            raise errors.NoCodeModelError('A code model is required to comment lines.')
            
        comment_char = bctl.code_model.line_comment
        try:
            if bctl.anchor_cursor is not None:
                sel = Span(bctl.canonical_cursor, bctl.anchor_cursor)
            else:
                sel = Span(bctl.canonical_cursor.clone().home(),
                           bctl.canonical_cursor.clone().end())
            with bctl.history.transaction():
                if is_commented(sel, comment_char):
                    uncomment(sel, comment_char)
                else:
                    comment(sel, comment_char)
    
            bctl.refresh_view(full=True)
        except:
            import logging
            logging.exception('comment toggle')
