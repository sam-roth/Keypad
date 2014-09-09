

from keypad.abstract.editor import AbstractEditor
from keypad.abstract.asyncmsg import AbstractMessageBarTarget
from keypad.abstract.application import app
from .textlayout.widget import CodeView, CodeViewProxy
from .qt_util import *
from .find import FindWidget
from .asyncmsg import MessageBarView
from keypad.core.signal import Signal
from keypad.api import run_in_main_thread
from keypad import api
from .textview import TextViewProxy

class Editor(AbstractEditor, AbstractMessageBarTarget, 
             Autoresponder, QWidget, metaclass=ABCWithQtMeta):

    def __init__(self, config):
        QWidget.__init__(self)
        self.__config = config.derive()
        self.__prox = TextViewProxy(self.__config)
        self.__view = self.__prox.peer
        
#         self.__view = CodeView(config=self.__config)
#         self.__prox = CodeViewProxy(self.__view)


        AbstractEditor.__init__(self, self.__prox, self.__config)
        Responder.__init__(self)

        self.__find_widget = FindWidget()
        self.__find_widget.hide()
        self.__msgbar = MessageBarView(self)
        self.__view.setParent(self)
        self.__layout = QVBoxLayout(self)
        self.__layout.addWidget(self.__msgbar)
        self.__layout.addWidget(self.__view)
        self.__layout.addWidget(self.__find_widget)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(0)
        self.__guard = True
        self.next_responder = self.buffer_controller

        self.__view.installEventFilter(self)
        self.__view.viewport().installEventFilter(self)

        self.setFocusProxy(self.__view)

    def open_find_panel(self):
        self.__find_widget.show()
        self.__find_widget.setFocus()

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
        app()._unregister_editor(self)


    def closeEvent(self, event):
        if self.__guard:
            event.ignore()
            # Have to return from function before calling again.
            run_in_main_thread(lambda: app().close(self))
        else:
            event.accept()


    def activate(self):
        self.raise_()
        self.__view.setFocus()

    def eventFilter(self, obj, ev):
        if (obj is self.__view or obj is self.__view.viewport()) and ev.type() == QEvent.FocusIn:
            self.editor_activated()
        return super().eventFilter(obj, ev)

    def show_message_bar(self, bar):
        self.__msgbar.enqueue(bar)

@api.interactive('gui_find')
def gui_find(ed: Editor):
    ed.open_find_panel()

api.menu(5, 'Edit/Find', 'gui_find', keybinding=api.Keys.ctrl.f)

