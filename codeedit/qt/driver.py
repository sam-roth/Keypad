


from PyQt4.Qt import *
from ..control import behavior # module contains autoconnects

import pathlib

from ..core import notification_center
from ..control.buffer_set import BufferSetController
from .buffer_set import BufferSetView

from .. import config


class _ProcessPosted(QEvent):
    '''
    Distributes `notification_center` messages. Do not post this manually.
    Instead use ``notification_center.post(msg)``.

    '''
    ProcessPostedType = QEvent.registerEventType()
    
    def __init__(self):
        super().__init__(_ProcessPosted.ProcessPostedType)


class Application(QApplication):

    def __init__(self, args):
        try:
            mversion = QSysInfo.MacintoshVersion
        except AttributeError:
            pass
        else:
            if mversion > QSysInfo.MV_10_8:
                # Workaround for QTBUG-32789
                QFont.insertSubstitution('.Lucida Grande UI', 'Lucida Grande')

        super().__init__(args)

    def exec_(self):
        
        self.setWheelScrollLines(10)

        controller = BufferSetController(BufferSetView())
        controller.view.show()
        controller.view.raise_()

        #mw = MainWindow()
        #mw.show()
        #mw.raise_()
        
        print('font family: %r' % QFont().lastResortFamily())
        

        notification_center.register_post_handler(self._on_post)

        return super().exec_()

    
    def event(self, evt):
        if evt.type() == _ProcessPosted.ProcessPostedType:
            notification_center.process_events()
            return True
        else:
            return super().event(evt)

    

    def _on_post(self):
        self.postEvent(self, _ProcessPosted())






if __name__ == '__main__':
    import sys
    import logging
    
    logfmt = '[%(asctime)s|%(module)s:%(lineno)d|%(levelname)s]\n  %(message)s'

    logging.basicConfig(level=logging.DEBUG,
                        format=logfmt)
    sys.exit(Application(sys.argv).exec_())
