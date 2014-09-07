
import abc
import functools
import enum
from ..core.signal import Signal

class AbstractMessageBarTarget(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def show_message_bar(self, bar):
        '''
        Show a message bar.

        :type bar: MessageBar
        '''

class ButtonKind(enum.Enum):
    default = 0
    ok = 1


class Button:
    __slots__ = 'name', 'kind'

    def __init__(self, name, kind=ButtonKind.default):
        self.name = name
        self.kind = kind

    def __repr__(self):
        if self.kind != ButtonKind.default:
            return 'Button({!r}, kind={!r})'.format(self.name, self.kind)
        else:
            return 'Button({!r})'.format(self.name)

def _to_button(button_or_str):
    if isinstance(button_or_str, Button):
        return button_or_str
    else:
        return Button(button_or_str)

class MessageBar:
    def __init__(self, *, title, choices=[], text_box=None, is_valid=True, steal_focus=False):
        self.title = title
        self.choices = tuple(map(_to_button, choices))
        self.callbacks = []
        self.text_box = text_box
        self._is_valid = is_valid
        self.steal_focus = steal_focus

    @property
    def is_valid(self):
        return self._is_valid

    @is_valid.setter
    def is_valid(self, value):
        '''
        When False, disable choice buttons (the close button is always enabled) and
        use a different color background for the text box, if applicable.
        '''
        self._is_valid = value
        self.is_valid_changed()

    @Signal
    def is_valid_changed(self):
        pass

    @Signal
    def text_changed(self, text):
        pass

    def emit_text_changed(self, text):
        self.text_changed(text)

    @Signal
    def done(self, choice):
        '''
        Emitted when the bar is closed or an option is chosen.

        If there is no text box, `choice` is the name of the option chosen.
        If there is a text box, `choice` is a tuple of (name of option,
        text).
        '''

    def emit_done(self, choice):
        self.done(choice)

    def add_callback(self, callback, *, add_sender=False):
        '''
        Add a callback to be executed upon emission of the done() signal
        and retain a strong reference to it.
        '''
        self.done.connect(callback, add_sender=add_sender)
        self.callbacks.append(callback)
        return self

    def add_text_changed_callback(self, callback, *, add_sender=False):
        '''
        Like add_callback() but for the text_changed() signal.
        '''

        self.text_changed.connect(callback, add_sender=add_sender)
        self.callbacks.append(callback)
        return self

