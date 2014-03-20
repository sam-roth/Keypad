


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
from ..core.processmgr.client import AsyncServerProxy

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

        result = super().exec_()
        AsyncServerProxy.shutdown_all()        
        

    
    def event(self, evt):
        if evt.type() == _ProcessPosted.ProcessPostedType:
            notification_queue.process_events()
            return True
        else:
            return super().event(evt)

    

    def _on_post(self):
        self.postEvent(self, _ProcessPosted())
        
        
    def timer(self, time_s, callback):
        QTimer.singleShot(int(time_s * 1000), callback)

def _fatal_handler(*args, **kw):
    import os
    logging.fatal(*args, **kw)
    os.abort()

def _decode_if_needed(s):
    if isinstance(s, bytes):
        try:
            return s.decode()
        except:
            return str(s)
    else:
        return str(s)


def _message_handler(ty, msg):
    try:
        handler = _level_handlers[ty]
    except KeyError:
        logging.exception('Unknown message type: %r. Will log as error.', ty)
        logging.error('%s', _decode_if_needed(msg))
    else:
        handler('%s', _decode_if_needed(msg))

USE_IPYTHON = True




def main():
    import sys
    import logging

    logfmt = '[%(asctime)s|%(module)s:%(lineno)d|%(levelname)s]\n  %(message)s'

    logging.basicConfig(level=logging.DEBUG,
                        format=logfmt)
    

        
    global config
    from .. import config
    
    global _level_handlers
    _level_handlers = {
        QtDebugMsg:    logging.debug,
        QtWarningMsg:  logging.warning,
        QtCriticalMsg: logging.critical,
        QtFatalMsg:    _fatal_handler
    }
        
    
    qInstallMsgHandler(_message_handler)    
#   

 
    if USE_IPYTHON:
        from ..control import BufferController
        @interactive('embedipython')
        def embed_ipython(bc: BufferController):
            import IPython
            IPython.embed()
#         import threading
#         def target():
#             import IPython
#             IPython.embed()
#         thd = threading.Thread(target=target)
#         thd.start()
#         
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
    main()
