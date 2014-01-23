

from .cua_interaction import CUAInteractionMode
from ..core import Signal, Keys, errors
from ..buffers import Cursor



class CommandLineInteractionMode(CUAInteractionMode):
    def __init__(self, controller):
        super().__init__(controller)
        self.keybindings.update([
            (Keys.enter,            lambda evt: self.accept()),
            (Keys.return_,          lambda evt: self.accept()),
            (Keys.up,               lambda evt: self.prev_history_item()),
            (Keys.down,             lambda evt: self.next_history_item()),
        ])
        self.__command_history = []
        self.__history_pos = 0
        self.__current_cmdline = ''

        self.controller.manipulator.executed_change.connect(self.__on_user_buffer_chg)


    def push_history_item(self, text):
        self.__command_history.append(text)
        self.__history_pos = 0

    def __on_user_buffer_chg(self, chg):
        self.__history_pos = 0
        self.__current_cmdline = self.controller.buffer.text
        print('__current_cmdline=', self.__current_cmdline)

    def accept(self):
        self.accepted()
        self.push_history_item(self.controller.buffer.text)
        self.controller.clear()
        self.__current_cmdline = ''

    def prev_history_item(self):
        try:
            item = self.__command_history[self.__history_pos - 1]
        except IndexError:
            raise errors.OldestHistoryItemError('Oldest history item')
        else:
            self.__history_pos -= 1
            self.controller.clear()
            Cursor(self.controller.buffer).insert(item)

    def next_history_item(self):
        if self.__history_pos + 1 > 0:
            raise errors.NewestHistoryItemError('Newest history item')
        else:
            self.__history_pos += 1
            if self.__history_pos == 0:
                item = self.__current_cmdline
            else:
                item = self.__command_history[self.__history_pos]
            self.controller.clear()
            Cursor(self.controller.buffer).insert(item)

    @Signal
    def accepted(self):
        pass
    
    
