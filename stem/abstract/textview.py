
import abc
import collections
import enum

from stem.core import Signal


class KeyEvent(collections.namedtuple('KeyEvent', 'key text')):
    
    def __new__(cls, *args, **kw):
        self = super().__new__(cls, *args, **kw)
        self._is_intercepted = False
        return self
    
    @property
    def is_intercepted(self): return self._is_intercepted

    def intercept(self):
        self._is_intercepted = True


class MouseButton(enum.IntEnum):
    no_button = 0x0
    left_button = 0x1
    right_button = 0x2
    middle_button = 0x4
    x_button_1 = 0x8
    x_button_2 = 0x10

class AbstractTextView(metaclass=abc.ABCMeta):

    @abc.abstractproperty
    def buffer(self):
        pass

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
        pass

    @modelines_visible.setter
    def modelines_visible(self, value):
        pass

    @abc.abstractproperty
    def cursor_pos(self):
        pass

    @cursor_pos.setter
    def cursor_pos(self, value):
        pass

    @abc.abstractproperty
    def first_line(self):
        pass

    @first_line.setter
    def first_line(self, value):
        pass


    @abc.abstractproperty
    def last_line(self):
        pass


    @abc.abstractproperty
    def plane_size(self):
        pass

    def scroll_to_line(self, line, *, center=False):
        if not (self.first_line <= line < self.last_line):
            height = self.last_line - self.first_line
            if center:
                line = max(line - height / 2, 0)
            elif line >= self.last_line:
                line = max(line - height + 1, 0)
    
            self.first_line = line


    @abc.abstractmethod
    def set_overlays(self, token, overlays):
        pass

    @abc.abstractmethod
    def update(self):
        pass
        
    @Signal
    def mouse_down_char(self, line, col): pass

    @Signal
    def mouse_move_char(self, buttons, line, col): pass

    @Signal
    def key_press(self, event: KeyEvent): pass

    @Signal
    def should_override_app_shortcut(self, event: KeyEvent): pass


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




