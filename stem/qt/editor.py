

from stem.abstract.editor import AbstractEditor
from stem.core.responder import Responder
from stem.abstract.application import app
# from .view import TextView
from .textlayout.widget import CodeView, CodeViewProxy
from .qt_util import *
from stem.core.signal import Signal

class Editor(AbstractEditor, Responder, QWidget, metaclass=ABCWithQtMeta):

    def __init__(self, config):
        self.__view = CodeView()
        self.__prox = CodeViewProxy(self.__view)
        self.__config = config.derive()

        AbstractEditor.__init__(self, self.__prox, self.__config)
        Responder.__init__(self)
        QWidget.__init__(self)

        self.__view.setParent(self)
        self.__layout = QVBoxLayout(self)
        self.__layout.addWidget(self.__view)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__guard = True
        self.next_responder = self.buffer_controller

        self.__view.installEventFilter(self)
        self.__view.viewport().installEventFilter(self)
        
    @Signal
    def window_should_kill_editor(self, editor):
        pass

    def kill(self):
        '''
        Immediately close the editor without prompting the user.
        '''
        self.__guard = False
        self.__view.close()
        self.buffer_controller.dispose()
        self.window_should_kill_editor(self)


    def closeEvent(self, event):
        if self.__guard:
            event.ignore()
            app().close(self)
        else:
            event.accept()


    def activate(self):
        self.raise_()
        self.__view.setFocus()

    def eventFilter(self, obj, ev):
        if (obj is self.__view or obj is self.__view.viewport()) and ev.type() == QEvent.FocusIn:
            self.editor_activated()
        return super().eventFilter(obj, ev)


