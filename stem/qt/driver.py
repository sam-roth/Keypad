


from PyQt4.Qt import *
from ..control import behavior # module contains autoconnects

import pathlib

from ..core import notification_queue
from ..control.buffer_set import BufferSetController
from .buffer_set import BufferSetView

from ..abstract.application import Application as AbstractApplication

from .qt_util import ABCWithQtMeta
from ..control.interactive import interactive
import logging

class _ProcessPosted(QEvent):
    '''
    Distributes `notification_center` messages. Do not post this manually.
    Instead use ``notification_center.post(msg)``.

    '''
    ProcessPostedType = QEvent.registerEventType()
    
    def __init__(self):
        super().__init__(_ProcessPosted.ProcessPostedType)


class Application(AbstractApplication, QApplication, metaclass=ABCWithQtMeta):

    def __init__(self, args):
        try:
            mversion = QSysInfo.MacintoshVersion
        except AttributeError:
            pass
        else:
            if mversion > QSysInfo.MV_10_8:
                # Workaround for QTBUG-32789
                QFont.insertSubstitution('.Lucida Grande UI', 'Lucida Grande')

        
        logging.debug('init app')
        super().__init__(args)
        logging.debug('init done')


    @property
    def clipboard_value(self):
        '''
        The current system clipboard value, or an internal clipboard's
        value if there is no access to the system clipboard, or it does not
        exist.
        '''
        return self.clipboard().text()

    @clipboard_value.setter
    def clipboard_value(self, value):
        self.clipboard().setText(value)

    def exec_(self):
        
        self.setWheelScrollLines(10)

        controller = BufferSetController(BufferSetView())
        controller.view.show()
        controller.view.raise_()

        #mw = MainWindow()
        #mw.show()
        #mw.raise_()
        
        

        notification_queue.register_post_handler(self._on_post)

        return super().exec_()

    
    def event(self, evt):
        if evt.type() == _ProcessPosted.ProcessPostedType:
            notification_queue.process_events()
            return True
        else:
            return super().event(evt)

    

    def _on_post(self):
        self.postEvent(self, _ProcessPosted())


def _driver_main():
    import sys
    import logging
    logfmt = '[%(asctime)s|%(module)s:%(lineno)d|%(levelname)s]\n  %(message)s'

    logging.basicConfig(level=logging.DEBUG,
                        format=logfmt)

    global config
    from .. import config
    sys.exit(Application(sys.argv).exec_())


#@interactive('reload')
def reload_all(app: Application):
    '''
    WARNING: Don't use this. It will screw up typechecks.
    '''
    import imp
    import stem
    import IPython.lib.deepreload
    import pkgutil
    import importlib
    for mldr, name, is_pkg in pkgutil.walk_packages(stem.__path__, 'stem.'):
        try:
            mod = importlib.import_module(name)
            IPython.lib.deepreload.reload(mod)
        except:
            logging.exception('error reloading %r', name)


    


if __name__ == '__main__':
    _driver_main()
