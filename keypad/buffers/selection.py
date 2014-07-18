
import abc
import contextlib
import re
import enum

from ..core import Signal
from ..options import GeneralSettings
from ..core.nconfig import Settings, Field, Conversions
from .span import Span

_AdvanceWordRegex = re.compile(
    r'''
      \b 
    | $ 
    | ^ 
    | _                     # for snake_case idents
    | (?<= _ ) \w           #  -> match after "_" too
    | (?<= [a-z] ) [A-Z]    # for camelCase and PascalCase idents
    | ['"]                  # match strings
    | (?<= ['"] ) .         # match after strings
    ''',
    re.VERBOSE
)


class Flag(object):
    def __init__(self):
        self.value = False
    def __bool__(self):
        return self.value
    @contextlib.contextmanager
    def __call__(self):
        oldval = self.value
        try:
            self.value = True
            yield
        finally:
            self.value = oldval

class SelectionSettings(Settings):
    _ns_ = 'selection'

    max_history_entries = Field(int, 10,
                                docs='The maximum number of previous cursor positions to retain')

    history_fuzz_lines = Field(int, 10,
                               docs='The number of lines the cursor needs to move in order to '
                                    'add a new history entry.')

class Selection(object):
    def __init__(self, manip, config):
        '''
        Create a new selection on the given buffer.
        '''

        from .cursor import Cursor
        from .buffer_manipulator import BufferManipulator
        from .buffer import Buffer

        self.manip = manip
        if isinstance(manip, BufferManipulator):
            self.buffer = manip.buffer
        elif isinstance(manip, Buffer):
            self.buffer = manip
        else:
            raise TypeError('Must use Buffer or Manipulator for this constructor')

        self._insert_cursor = Cursor(manip)
        self._anchor_cursor = None
        self._history = []
        self._future = []
        self.__prev_pos = None
        self.__edited = False

        self.select = Flag()
        self.sel_settings = SelectionSettings.from_config(config)
        self.config = config


    def add_history(self):
        if len(self._history) >= self.sel_settings.max_history_entries:
            del self._history[0]

        add_entry = False
        if not self._history:
            add_entry = True
        else:
            y0, x0 = self._history[-1].pos
            y, x = self.pos

            if abs(y0 - y) >= self.sel_settings.history_fuzz_lines:
                add_entry = True

        if add_entry:
            self._future.clear()
            self._history.append(self.insert_cursor.clone())

    def to_previous_position(self):
        if self._history:
            first = True
            while (self._history 
                   and (first
                        or abs(top.pos[0] - self.pos[0])
                           < self.sel_settings.history_fuzz_lines)):
                top = self._history.pop()
                self._future.append(self.insert_cursor.clone())
                first = False
            self.move(top.pos)

    def to_next_position(self):
        if self._future:
            top = self._future.pop()
            self._history.append(self.insert_cursor.clone())
            self.move(top.pos)

    @property
    def region(self):
        if self.anchor_cursor is not None:
            return Span(self.insert_cursor, self.anchor_cursor).region
        else:
            return Span(self.insert_cursor, self.insert_cursor).region

    @property
    def history(self):
        return tuple(self._history)

    @property
    def indent(self):
        return GeneralSettings.from_config(self.config).indent_text

    @property
    def pos(self):
        return self.insert_cursor.pos

    @pos.setter
    def pos(self, value):
        y, x = value
        self.move(y, x)

    @property
    def insert_cursor(self): 
        return self._insert_cursor

    @property
    def anchor_cursor(self): 
        return self._anchor_cursor

    @Signal
    def moved(self):
        pass

    def _on_move(self, prev_pos, was_edited):
        pass

    def _pre_move(self):
        self.__prev_pos = self.pos
        if self.select and not self._anchor_cursor:
            self._anchor_cursor = self._insert_cursor.clone()
            self._anchor_cursor.chirality = self._anchor_cursor.Chirality.Left
        elif not self.select:
            self._anchor_cursor = None

    def _post_move(self):
        self._on_move(self.__prev_pos, self.__edited)
        self.__edited = False
        self.moved()


    @contextlib.contextmanager
    def moving(self):
        try:
            self._pre_move()
            yield
        finally:
            self._post_move()

    def advance_word(self, n):
        from ..core.attributed_string import lower_bound

        curs = self._insert_cursor
        line, col = curs.pos
        posns = [match.start() for match in 
                 _AdvanceWordRegex.finditer(curs.line.text)]
        idx = lower_bound(posns, col)
        idx += n

        with self.moving():
            if 0 <= idx < len(posns):
                new_col = posns[idx]
                curs.right(new_col - col)
            elif idx < 0 and not curs.on_first_line:
                curs.up().end()
            elif idx > 0 and not curs.on_last_line:
                curs.down().home()
        return self

    def right(self, n=1):
        with self.moving():
            self._insert_cursor.right(n)
        return self

    def down(self, n=1):
        with self.moving():
            self._insert_cursor.down(n)

        return self
    def move(self, line=None, col=None):
        with self.moving():
            self._insert_cursor.move(line, col)
        return self

    def advance(self, n=1):
        with self.moving():
            self._insert_cursor.advance(n)
        return self


    def home(self):
        with self.moving():
            self._insert_cursor.home()
        return self

    def end(self):
        with self.moving():
            self._insert_cursor.end()
        return self


    def last_line(self):
        with self.moving():
            self._insert_cursor.last_line()
        return self

    def get_text(self):
        if not self._anchor_cursor:
            return ''
        else:
            return self._anchor_cursor.text_to(self._insert_cursor)

    def set_text(self, value):
        if self._anchor_cursor:
            self._anchor_cursor.remove_to(self._insert_cursor)

        self.__edited = True
        with self.moving():
            self._insert_cursor.insert(value)

        if not value:
            self._anchor_cursor = None

        self.add_history()

    @property
    def text(self): return self.get_text()

    @text.setter
    def text(self, value): self.set_text(value)

    def replace(self, text):
        self.text = text
        return self

    def delete(self, n=1):
        if not self._anchor_cursor:
            with self.select():
                self.advance(n)

        self.text = ''
        return self

    def clear_selection(self):
        self._anchor_cursor = None

    def advance_para(self, n=1):
        with self.moving():
            skip = True
            c = self._insert_cursor
            for _ in c.walklines(n):
                if c.searchline(r'^\s*$'):
                    if not skip:
                        break       
                else:
                    skip = False
        return self


    def tab(self, n=1):
        if self._anchor_cursor:
            first, second = sorted([
                self._insert_cursor,
                self._anchor_cursor
            ], key=lambda c: c.pos)

            c = first.clone()

            for _ in c.walklines(1):
                if c.pos >= second.pos:
                    break

                c.home()

                span = c.line_span_matching(r'^\s*$')
                if span:
                    # if the line is just whitespace, remove its contents
                    span.remove()
                else:
                    # otherwise perform the indentation
                    if n > 0:
                        c.insert(self.indent * n)
                    else:
                        m = c.searchline(r'^\s+')
                        if m:
                            remove_count = min(m.end(), -len(self.indent) * n)
                            c.delete(remove_count)

        else:
            c = self._insert_cursor
            c.insert(self.indent * n)

        return self

    def backspace(self):
        return self.delete(-1)

    def line_break(self):
        '''
        Breaks and indents new line without aligning it.
        '''

        self.replace('\n')



class BacktabMixin(object):

    def backspace(self):
        ts = len(self.indent)
        if self.anchor_cursor or \
                not re.match(r'^\s*$', self.insert_cursor.line.text[:self.insert_cursor.x]) or\
                (self.insert_cursor.x % ts) != 0 or\
                self.insert_cursor.x == 0:
            super().backspace()
        else:
            self.delete(-ts)


class BacktabSelection(BacktabMixin, Selection):
    pass


class AlignPolicy(enum.Enum):
    align_with_spaces = (True, False, True)
    align_with_indent_text = (True, True, True)
    indent = (False, None, True)
    disable = (False, None, False)

    def __init__(self, align, use_indent_text, enable):
        self.align = align
        self.use_indent_text = use_indent_text
        self.enable = enable

    def align_text(self, space_count, indent_text, tab_width):
        if not self.enable:
            return ''

        if self.align:
            if self.use_indent_text:
                width = len(indent_text.expandtabs(tab_width))
                return indent_text * (space_count // width)
            else:
                return ' ' * space_count
        else:
            if space_count > 0:
                return indent_text

Conversions.register(AlignPolicy, lambda x: AlignPolicy[x])

class AutoindentSettings(Settings):
    _ns_ = 'autoindent'

    __align_policy_doc = '''
    Determines how alignment should be performed. Possible values are:

    ``align_with_spaces``
        (Default) Use spaces for alignment, regardless of whether tabs are  used
        for indentation. This is the recommended strategy, sometimes called "Smart
        Tabs" or "Semantic Tabs". See http://www.emacswiki.org/SmartTabs . It
        allows users select an arbitrary tab width, while preserving alignment.
        This is also what you want if you're using spaces for indentation. 

    ``align_with_indent_text``
        Use the indent text (such as tabs) for alignment. This usually won't
        provide consistent alignment, since the indent level will be rounded down.

    ``indent``
        Indent by one level, rather than aligning.

    ``disable``                   
        Don't perform any automatic alignment. This does not affect whether
        automatic indentation is performed.

    '''
    AlignPolicy = AlignPolicy

    trigger_on_newline = Field(bool, True)
    trigger_on_move    = Field(bool, True)

    move_trigger_phase_timeout_ms = Field(int, 10,
                                          docs='Timeout for each phase of the automatic indent algorithm, in ms, '
                                               'when it is triggered by moving the cursor.')

    strip  = Field(bool, True, 
                   docs='Strip trailing whitespace from the previously indented line when indenting '
                        'a new line.')

    align_policy = Field(AlignPolicy, 
                         AlignPolicy.align_with_spaces,
                         safe=True,
                         docs=__align_policy_doc)




class IndentingSelectionMixin:
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.__ai_settings = AutoindentSettings.from_config(self.config)
        self.__gen_settings = GeneralSettings.from_config(self.config)

        # track previous indentation positions, so that superfluous indentation is removed
        self.__last_autoindent_curs = None

    def _on_move(self, prev_pos, was_edited):
        super()._on_move(prev_pos, was_edited)
        py, px = prev_pos
        cy, cx = self.pos
        if (self.__ai_settings.trigger_on_move 
                and not was_edited
                and not self.select
                and py != cy
                and self.insert_cursor.searchline(r'^\s*$')):
            self.reindent(phase_timeout_ms=self.__ai_settings.move_trigger_phase_timeout_ms)

    def line_break(self):
        self.set_text('\n', align=False)

    def set_text(self, text, *, align=True):
        cm = self.buffer.code_model

        # Determine whether automatic indentation should occur.
        indent = False
        # No code model means no autoindent.
        if self.__ai_settings.trigger_on_newline and cm is not None:
            # Indent new lines
            if text.endswith('\n'):
                indent = True
            # Indent upon hitting a special trigger, such as '}'
            elif text.endswith(tuple(cm.reindent_triggers)):
                # Even then, if there's something else on the line, don't try to
                # second-guess the user.
                if not self.insert_cursor.line.text.strip():
                    indent = True
        super().set_text(text)

        if indent:
            self.reindent(align=align)

    def reindent(self, *, phase_timeout_ms=50, align=True):
        cm = self.buffer.code_model
        if cm is None:
            return

        # Using the scratchpad for these changes prevents creation of spurious undo history,
        # as well as keeping indentation from being saved.

        with self.manip.history.scratchpad():
            curs = self.insert_cursor.clone()

            indentation = cm.indentation(curs.pos, 
                                         brace_search_timeout_ms=phase_timeout_ms,
                                         indent_level_timeout_ms=phase_timeout_ms)
            indent_level = indentation.level

            # strip existing indent
            curs.line_span_matching(r'^\s*').remove()

            # add new indent
            curs.home().insert(self.__gen_settings.indent_text * indentation.level)

            # align if needed
            if align and indentation.align is not None:
                spaces_to_align = indentation.align - curs.x
                if spaces_to_align > 0:
                    curs.insert(self.__ai_settings.align_policy.align_text(spaces_to_align,
                                                                           self.__gen_settings.indent_text,
                                                                           self.__gen_settings.tab_stop))


            # strip previously auto-indented line if it contains trailing spaces
            # (or is blank)
            if self.__last_autoindent_curs is not None:
                lc = self.__last_autoindent_curs.clone()
                # This can happen when moving the cursor up after inserting a new line.
                # If we don't check, our indent could get wiped out.
                if lc.y != curs.y:
                    lc.line_span_matching(r'\s*$').remove()

            # update the last autoindent position
            lc = curs.clone()
            lc.chirality = lc.Chirality.Left # keep left of indented text
            self.__last_autoindent_curs = lc

class IndentingBacktabSelection(IndentingSelectionMixin, BacktabMixin, Selection):
    pass

