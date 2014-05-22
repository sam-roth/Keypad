


from PyQt4.Qt import *
from ..control import behavior # module contains autoconnects

import pathlib

from ..core import notification_queue, errors
from ..control.buffer_set import BufferSetController
from .buffer_set import BufferSetView

from ..abstract.application import Application as AbstractApplication, SaveResult

from .qt_util import ABCWithQtMeta
from ..control.interactive import interactive
import logging
from ..core.nconfig import Config

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
        
        QApplication.setApplicationName('Stem')
        super().__init__(args)



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
        notification_queue.register_post_handler(self._on_post)

        mw = self.new_window()
        ed = self.new_editor()
        mw.add_editor(ed)


        result = super().exec_()
        AsyncServerProxy.shutdown_all()        
        
    
    def _queue_exc_handler(self, exc):
        if isinstance(exc, errors.UserError):
            interactive.run('show_error', exc)
    
    def event(self, evt):
        if evt.type() == _ProcessPosted.ProcessPostedType:
            notification_queue.process_events(self._queue_exc_handler)
            return True
        else:
            return super().event(evt)

    def _on_post(self):
        self.postEvent(self, _ProcessPosted())
        
    def timer(self, time_s, callback):
        QTimer.singleShot(int(time_s * 1000), callback)

    def save_prompt(self, editor):
        editor.setFocus()
        mb = QMessageBox(editor)
        mb.setWindowFlags(Qt.Sheet)
        mb.setWindowModality(Qt.WindowModal)
        mb.setText('This buffer has been modified. Do you want to save your changes?')
        mb.addButton(mb.Cancel)
        mb.addButton(mb.Discard)
        mb.addButton(mb.Save)

        result = mb.exec_()
        if result == mb.Discard:
            return SaveResult.discard
        elif result == mb.Save:
            return SaveResult.save
        else:
            return SaveResult.cancel

    def get_save_path(self, editor):
        save_path = QFileDialog.getSaveFileName(editor, 'Save')
        if save_path:
            return save_path
        else:
            return None

    def new_window(self):
        from .main_window import MainWindow
        w = MainWindow()
        w.show()
        w.raise_()
        return w

    def new_editor(self):
        from .editor import Editor
        return Editor(Config.root)

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
    sys.exit(Application(sys.argv).exec_())
    
        
if __name__ == '__main__':
    main()
