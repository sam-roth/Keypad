

from codeedit.api import autoextend
from codeedit.options import UserConfigHome
from codeedit.api import BufferController
from codeedit.control.command_line_interaction import CommandLineInteractionMode

@autoextend(BufferController, 
            lambda tags: tags.get('cmdline'))
class HistoryWatcher(object):

    def __init__(self, buf_ctl):
        self.buf_ctl = buf_ctl
        self.imode = buf_ctl.interaction_mode       
        self.imode.accepted.connect(self.__after_cmdline_accepted)
        
        self.buf_ctl.add_tags(history_watcher=self)

        histpath = self.histpath = UserConfigHome / 'cmdline_history'

        try:
            with histpath.open('r') as f:
                for line in f:
                    self.imode.push_history_item(line)
        except IOError:
            pass

        self.file = histpath.open('w+')
    
    def __after_cmdline_accepted(self):
        hist = self.imode.command_history
        if hist:
            with self.histpath.open('w+') as f:
                f.write(hist[-1])

