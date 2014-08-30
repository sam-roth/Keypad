
import abc
import functools
from ..core.signal import Signal

class AbstractMessageBarTarget(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def show_message_bar(self, bar):
        '''
        Show a message bar.

        :type bar: MessageBar
        '''

class MessageBar:
    def __init__(self, *, title, choices=[], text_box=None, is_valid=True):
        self.title = title
        self.choices = choices
        self.callbacks = []
        self.text_box = text_box
        self._is_valid = is_valid
        
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

