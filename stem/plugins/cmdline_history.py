

from stem.api import autoextend
from stem.options import UserConfigHome
from stem.api import BufferController
from stem.control.command_line_interaction import CommandLineInteractionMode

@autoextend(BufferController, 
            lambda tags: tags.get('cmdline'))
class HistoryWatcher(object):

    def __init__(self, buf_ctl):
        self.buf_ctl = buf_ctl
        self.imode = buf_ctl.interaction_mode       
        self.imode.accepted.connect(self.__after_cmdline_accepted)
        
        self.buf_ctl.add_tags(history_watcher=self)

        UserConfigHome.mkdir(parents=True)
        histpath = self.histpath = UserConfigHome / 'cmdline_history'

        try:
            histpath.mkdir
            with histpath.open('r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.imode.push_history_item(line)
        except IOError:
            pass

    
    def __after_cmdline_accepted(self):
        hist = self.imode.command_history
        if hist:
            with self.histpath.open('a') as f:
                f.write(hist[-1] + '\n')


