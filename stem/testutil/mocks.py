
from stem.abstract.textview import AbstractCodeView, KeyEvent
from stem.abstract.completion import AbstractCompletionView
from stem.core.key import Modifiers
import string

class MockCodeView(AbstractCodeView):
    buffer = None
    modelines = ()
    modelines_visible = True
    cursor_pos = (0, 0)
    first_line = 0
    plane_size = 40, 80
    _completion_view = None
    call_tip_model = None

    def press(self, *keys):
        for key in keys:
            try:
                c = chr(key.keycode)
                if c not in string.printable:
                    c = ''
                elif not (key.modifiers & Modifiers.Shift):
                    c = c.lower()
            except ValueError:
                c = ''
            self.key_press(KeyEvent(key, c))


    @property
    def completion_view(self):
        if self._completion_view is None:
            self._completion_view = MockCompletionView()
        return self._completion_view

    @property
    def last_line(self):
        height, _ = self.plane_size
        return height + self.first_line

    def scroll_to_line(self, line, *, center=False):
        '''
        Scroll the view so that the line is visible.

        :param line: The line number to scroll to.
        :param center:
            If True, center the line in the display;
            otherwise, scroll only as far as necessary.

        Returns a boolean indicating whether the view was
        actually scrolled.
        '''
        if not (self.first_line <= line < self.last_line):
            height = self.last_line - self.first_line
            if center:
                line = max(line - height / 2, 0)
            elif line >= self.last_line:
                line = max(line - height + 1, 0)

            self.first_line = line

            return True
        else:
            return False


    def set_overlays(self, token, overlays):
        '''
        Give the text specified the requested attributes without modifying the buffer.

        :param token:
            A unique identifier (of your choosing) that may be used to later
            erase or modify the attributes.

        :param overlays:
            A list of tuples of ``(span, key, value)`` indicating the attributes
            to apply.

        :type token: `object`
        :type overlays: [(`~stem.buffers.span.Span`, `object`, `object`)]

        '''

    def update(self):
        '''
        Force redrawing of the entire view.
        '''



    def show_completions(self):
        pass


    @property
    def completion_doc_lines(self):
        return []

    @completion_doc_lines.setter
    def completion_doc_lines(self, val):
        pass

    @property
    def completion_doc_plane_size(self):
        return 40, 40

    @property
    def completions(self):
        return []

    @completions.setter
    def completions(self, val):
        pass

    @property
    def cursor_visible(self):
        return True


    @cursor_visible.setter
    def cursor_visible(self, value):
        pass

class MockCompletionView(AbstractCompletionView):

    @property
    def current_row(self):
        return 0

    @property
    def completions(self):
        return []

    @completions.setter
    def completions(self, val):
        pass

    @property
    def visible(self):
        return False

    @visible.setter
    def visible(self, value):
        pass

    @property
    def anchor(self):
        '''
        The (line, col) position to which the completion view should be
        anchored.
        '''
        return 0,0

    @anchor.setter
    def anchor(self, value):
        pass


    @property
    def doc_view_visible(self):
        return True

    @doc_view_visible.setter
    def doc_view_visible(self, value):
        pass

    @property
    def doc_view(self):
        pass
