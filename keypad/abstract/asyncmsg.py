
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
    def __init__(self, *, title, choices=[]):
        self.title = title
        self.choices = choices
        self.callbacks = []

    @Signal
    def done(self, choice):
        '''
        Emitted when the bar is closed or an option is chosen.
        '''

    def emit_done(self, choice):
        self.done(choice)

    def add_callback(self, callback):
        self.done.connect(callback)
        self.callbacks.append(callback)
        return self

