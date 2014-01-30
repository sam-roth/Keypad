

from .buffer            import Buffer, TextModification
from .buffer_history    import BufferHistory
from ..core             import Signal
from ..core.signal      import Intercepter

class BufferManipulator(object):
    def __init__(self, buff):
        assert isinstance(buff, Buffer)
        self._buffer = buff
        self._history = BufferHistory(buff)
    
    @property
    def buffer(self):
        return self._buffer

    @property
    def history(self):
        return self._history

    def execute(self, change):
        intercept = Intercepter()
        self.will_execute_change(change, intercept)
        if not intercept.intercepted:
            self.buffer.execute(change)
            self.executed_change(change)

    @Signal
    def will_execute_change(self, change, intercept):
        pass

    @Signal
    def executed_change(self, change):
        '''
        Called from within a history transaction when a BufferManipulator executes
        a change. Not called when undoing or redoing a change, or when the buffer 
        is edited directly,

        Possible uses include a hook to automatically perform indentation after
        every newline is inserted. 
        
        Warning: Do not attempt to use BufferManipulator.execute() from within 
        a signal handler. Instead, directly modify the buffer.

        Warning: Do not begin a new history transaction during a handler for this signal.
        A transaction is already open.
        '''


def main():
    import re

    buff = Buffer()
    manip = BufferManipulator(buff)

    
    @manip.executed_change.connect
    def autoindent(chg):
        if chg.insert.endswith('\n'):
            cy, cx = chg.pos
            match = re.match('^\s*', buff.lines[cy].text)
            if match is not None:
                buff.insert(chg.insert_end_pos, match.group(0))

    with manip.history.transaction():
        manip.execute(TextModification(pos=(0, 0), insert='    Hello,\n'))
        manip.execute(TextModification(pos=buff.end_pos, insert='world!!!'))

    
    print(buff.dump())
    manip.history.undo()
    print(buff.dump())
    manip.history.redo()
    print(buff.dump())


        





if __name__ == '__main__':
    main()
