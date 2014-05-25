
import traceback

from .cua_interaction import CUAInteractionMode
from ..core import Signal, Keys, errors
from ..buffers import Cursor, Span
from ..buffers.buffer_protector import BufferProtector
import logging
import types
from ..util import ImmutableListView
from .interactive import run

class PromptWriter(object):
    def write(self, text):
        self.text_written(text)

    @Signal
    def text_written(self, text):
        pass

writer = PromptWriter()

class CommandLineInteractionMode(CUAInteractionMode):
    def __init__(self, controller):
        super().__init__(controller)
        self.keybindings.update([
            (Keys.enter,            lambda evt: self.accept()),
            (Keys.return_,          lambda evt: self.accept()),
            (Keys.up,               lambda evt: self.prev_history_item()),
            (Keys.down,             lambda evt: self.next_history_item()),
            (Keys.esc,              lambda evt: self.cancelled()),
            (Keys.tab,              lambda evt: run('complete'))
        ])

        self.__prompt = ': '
        self.__command_history = []
        self.__history_pos = 0
        self.__current_cmdline = ''

        self.controller.manipulator.executed_change.connect(self.__on_user_buffer_chg)
        self.controller.view.should_override_app_shortcut.connect(self.intercept_app_shortcut)
        self.__protector = BufferProtector(self.controller.manipulator)
        self.__wrote_newline = False
        with self.controller.history.transaction():
            self.__next_line(add_newline=False)

        writer.text_written.connect(self.__on_write_text)
        

    def intercept_app_shortcut(self, event):
        if Keys.tab.matches(event.key):
            event.intercept()
            run('complete')



    @Signal
    def text_written(self):
        '''
        Text was written to the buffer.
        '''
        pass

    @property
    def cmdline_col(self):
        return len(self.__prompt)

    @property
    def current_cmdline(self):
        return self.__current_cmdline
    
    @current_cmdline.setter
    def current_cmdline(self, value):
        sel = self.controller.selection
        sel.last_line().end()
        with sel.select():
            sel.move(col=self.cmdline_col)
        with self.controller.history.transaction():
            sel.replace(value)
    
    def push_history_item(self, text):
        self.__command_history.append(text)
        self.__history_pos = 0

    def __on_write_text(self, text):
        Cursor(self.controller.buffer).last_line().end().insert('\n' + str(text))
        self.__next_line()
        self.text_written()

    def update_cmdline(self):
        self.__history_pos = 0
        home = Cursor(self.controller.buffer).last_line().home().right(len(self.__prompt))
        end = home.clone().end()
        self.__current_cmdline = home.text_to(end) 


    def __on_user_buffer_chg(self, chg):
        self.update_cmdline()

    def __next_line(self, add_newline=True):
        prot_end_curs = Cursor(self.controller.buffer).last_line().end()
        if add_newline:
            prot_end_curs.insert('\n')
            self.__wrote_newline = True

        prot_end_curs.insert(self.__prompt).left()
        span = self.__protector.region = Span(Cursor(self.controller.buffer), prot_end_curs)


        self.__current_cmdline = ''

        self.controller.history.clear()
        self.controller.scroll_to_cursor()

    def accept(self):
        self.update_cmdline()
        if not self.__current_cmdline:
            self.cancelled()
            return
        

        self.__wrote_newline = False
        self.push_history_item(self.__current_cmdline)
        self.accepted()

        if not self.__wrote_newline:
            self.__next_line()

        if self.accepted.errors:
            error = self.accepted.errors[0]
            from ..core import notification_queue
            def error_shower():
                self.show_error('{} [{}]'.format(str(error), type(error).__name__))

            notification_queue.run_in_main_thread(error_shower)

    def __set_last_line(self, text):
        home = Cursor(self.controller.buffer).last_line().home()
        end = home.clone().end()
        home.remove_to(end)
        self.__next_line(add_newline=False)
        insert_point = Cursor(self.controller.buffer).last_line().end()
        insert_point.insert(text)
        self.__current_cmdline = text

    def prev_history_item(self):
        try:
            item = self.__command_history[self.__history_pos - 1]
        except IndexError:
            raise errors.OldestHistoryItemError('Oldest history item')
        else:
            self.__history_pos -= 1
            
            self.__set_last_line(item)

    def next_history_item(self):
        if self.__history_pos + 1 > 0:
            raise errors.NewestHistoryItemError('Newest history item')
        else:
            self.__history_pos += 1
            if self.__history_pos == 0:
                item = self.__current_cmdline
            else:
                item = self.__command_history[self.__history_pos]
            self.__set_last_line(item)

    @property
    def command_history(self):
        return ImmutableListView(self.__command_history)

    @Signal
    def accepted(self):
        pass

    @Signal
    def cancelled(self):
        pass
    
    
