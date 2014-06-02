
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




