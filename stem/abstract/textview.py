
import abc
import collections
import enum
import functools

from stem.core import Signal


class KeyEvent(collections.namedtuple('KeyEvent', 'key text')):
    '''
    KeyEvent(key, text)

    :param key: The key pressed.
    :param text: The text that should inserted due to the keypress.

    :type key: stem.core.key.SimpleKeySequence
    :type text: str

    .. autoattribute:: key
    .. autoattribute:: text
    '''
    def __new__(cls, *args, **kw):
        self = super().__new__(cls, *args, **kw)
        self._is_intercepted = False
        return self
    
    @property
    def is_intercepted(self): return self._is_intercepted

    def intercept(self):
        '''
        Do not allow this event to propagate to containing views.
        '''
        self._is_intercepted = True


class MouseButton(enum.IntEnum):
    no_button = 0x0
    left_button = 0x1
    right_button = 0x2
    middle_button = 0x4
    x_button_1 = 0x8
    x_button_2 = 0x10



class AbstractColumnDelegate(metaclass=abc.ABCMeta):
    '''
    Provides additional linewise text, such as folding information
    or line numbers.
    '''

    Row = collections.namedtuple('Row', 'text bgcolor')


    def __init__(self, max_cache_size=256):
        self.__row_cache = functools.lru_cache(maxsize=max_cache_size)(self._row)

    @abc.abstractproperty
    def enabled(self):
        pass

    @abc.abstractmethod
    def _row(self, line):
        pass

    def row(self, line):
        return self.__row_cache(line)

    @Signal
    def invalidated(self):
        pass

    def _invalidate(self):
        self.invalidated()
        self.__row_cache.cache_clear()







class AbstractTextView(metaclass=abc.ABCMeta):
    '''
    The abstract base class for text views.
    '''

    @abc.abstractproperty
    def buffer(self):
        '''
        The buffer shown.

        :rtype: `~stem.buffers.buffer.Buffer`
        '''

    @buffer.setter
    def buffer(self, value):
        pass


    @abc.abstractproperty
    def modelines(self):
        pass

    @modelines.setter
    def modelines(self, value):
        pass
        

    @abc.abstractproperty
    def modelines_visible(self):
        '''
        A boolean value indicating whether the modelines (e.g., ``... [CUAInteractionMode]``)
        should be visible.
        '''

    @modelines_visible.setter
    def modelines_visible(self, value):
        pass

    @abc.abstractproperty
    def cursor_pos(self):
        '''
        The **text** cursor position.

        :returns: A tuple of (y, x).
        '''

    @cursor_pos.setter
    def cursor_pos(self, value):
        '''
        The **text** cursor position.

        :param value: A tuple of (y, x) indicating the new cursor position.
        '''

    @abc.abstractproperty
    def first_line(self):
        '''
        The first visible line.
        '''

    @first_line.setter
    def first_line(self, value):
        pass


    @abc.abstractproperty
    def last_line(self):
        '''
        The last visible line (read-only).
        '''


    @abc.abstractproperty
    def plane_size(self):
        pass

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


    @abc.abstractmethod
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

    @abc.abstractmethod
    def update(self):
        '''
        Force redrawing of the entire view.
        '''

    @Signal
    def mouse_down_char(self, line, col): 
        '''
        Emitted when the left mouse button is pressed.

        :param line: the line number under the mouse cursor
        :param col: the column number under the mouse cursor
        '''

    @Signal
    def mouse_move_char(self, buttons, line, col):
        '''
        Emitted when the mouse moves.

        .. note::
            This signal may be emitted only while a button is pressed, depending
            on implementation.

        :param buttons: The bitwise OR of the mouse buttons pressed.
        :param line: The line number.
        :param col: The column number.

        :type buttons: bitwise OR of `~MouseButton`
        '''

    @Signal
    def key_press(self, event: KeyEvent):
        '''
        The user pressed a key while the view was focused.
        '''

    @Signal
    def should_override_app_shortcut(self, event: KeyEvent):
        '''
        Emitted before an event is interpreted as an application shortcut.
        To intercept, use the :py:meth:`~KeyEvent.intercept` method.
        '''

    @Signal
    def input_method_preedit(self, text):
        '''
        Optionally emitted by a TextView on receiving a preedit event from
        the OS's input method.

        This is used for implementing compose/dead-key support.
        '''

    @Signal
    def input_method_commit(self, 
                            preedit_text,
                            replace_start, replace_stop,
                            replace_text):
        '''
        Optionally emitted by a TextView on receiving a commit event from
        the OS's input method.

        This is used for implementing compose/dead-key support.
        '''


class AbstractCodeView(AbstractTextView):
    '''
    Subclass of `AbstractTextView` with completion view and call tip
    view.
    '''

    @property
    @abc.abstractmethod
    def completion_view(self): # FIXME: model should be the property, not view
        '''
        :rtype: stem.abstract.completion.AbstractCompletionView
        '''


    @abc.abstractproperty
    def call_tip_model(self):
        pass

    @call_tip_model.setter
    def call_tip_model(self, value):
        pass


    @abc.abstractmethod
    def show_completions(self):
        self.completion_view.visible = True


    @property
    def completion_doc_lines(self):
        return self.completion_view.doc_lines

    @completion_doc_lines.setter
    def completion_doc_lines(self, val):
        self.completion_view.doc_lines = val

    @property
    def completion_doc_plane_size(self):
        return self.completion_view.doc_plane_size

    @property
    def completions(self):
        return self.completion_view.model.completions

    @completions.setter
    def completions(self, val):
        self.completion_view.model.completions = val




