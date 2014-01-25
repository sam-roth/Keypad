
import traceback

from .cua_interaction import CUAInteractionMode
from ..core import Signal, Keys, errors
from ..buffers import Cursor, Span
from ..buffers.buffer_protector import BufferProtector
import logging

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
            (Keys.esc,              lambda evt: self.cancelled())
        ])

        self.__prompt = ': '
        self.__command_history = []
        self.__history_pos = 0
        self.__current_cmdline = ''

        self.controller.manipulator.executed_change.connect(self.__on_user_buffer_chg)
        self.__protector = BufferProtector(self.controller.manipulator)
        self.__wrote_newline = False
        with self.controller.history.transaction():
            self.__next_line(add_newline=False)

        writer.text_written.connect(self.__on_write_text)
        

#    def _on_key_press(self, evt):
#        # FIXME: this isn't really the right way of doing this
#
#        anch = self.controller.anchor_cursor
#        buf_lines = len(self.controller.buffer.lines)
#
#        curs = self.controller.canonical_cursor
#
#        # don't allow edit in read-only area
#        no_super = curs.pos[0] != buf_lines - 1
#            
#
#        # remove selections in read-only area
#        if anch is not None and anch.pos[0] != buf_lines - 1:
#            self.controller.anchor_cursor = None
#            return    
#
#        # don't allow backspace into read-only area
#        if Keys.backspace.optional(Keys.shift.alt.ctrl.meta).matches(evt.key):
#            if curs.pos[1] == 0:
#                return
#                    
#
#        curs.last_line()
#
#        if not no_super:
#            super()._on_key_press(evt)
#

    @property
    def current_cmdline(self):
        return self.__current_cmdline
    
    def push_history_item(self, text):
        self.__command_history.append(text)
        self.__history_pos = 0

    def __on_write_text(self, text):
        Cursor(self.controller.buffer).last_line().end().insert('\n' + str(text))
        self.__next_line()

    def __on_user_buffer_chg(self, chg):
        self.__history_pos = 0
        home = Cursor(self.controller.buffer).last_line().home().right(len(self.__prompt))
        end = home.clone().end()
        self.__current_cmdline = home.text_to(end) 

    def __next_line(self, add_newline=True):
        prot_end_curs = Cursor(self.controller.buffer).last_line().end()
        if add_newline:
            prot_end_curs.insert('\n')
            self.__wrote_newline = True

        prot_end_curs.insert(self.__prompt).left()
        span = self.__protector.region = Span(Cursor(self.controller.buffer), prot_end_curs)


        self.__current_cmdline = ''

        self.controller.history.clear()

    def accept(self):
        if not self.__current_cmdline:
            self.cancelled()
            return
        

        self.__wrote_newline = False
        self.push_history_item(self.__current_cmdline)
        logging.debug('Current text: %r', self.__current_cmdline)
        self.accepted()
        #try:
        #    for error in self.accepted.errors:
        #        writer.write(''.join(traceback.format_exception(type(error), error, error.__traceback__)))
        #except Exception as exc:
        #    logging.exception(exc)
        if not self.__wrote_newline:
            self.__next_line()

        if self.accepted.errors:
            error = self.accepted.errors[0]
            from ..core import notification_center
            def error_shower():
                self.show_error('{} [{}]'.format(str(error), type(error).__name__))

            notification_center.post(error_shower)




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

    @Signal
    def accepted(self):
        pass

    @Signal
    def cancelled(self):
        pass
    
    
