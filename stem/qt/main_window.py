
from stem.abstract.application import AbstractWindow, app
from stem.abstract import ui

from stem.core.responder import Responder
from stem.core.nconfig import Config
from .qt_util import *
from ..core.notification_queue import in_main_thread
from ..control import interactive
import logging

class CommandLineWidget(Responder, QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Popup)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        from .view import TextView
        from ..control import BufferController
        from ..control.command_line_interaction import CommandLineInteractionMode
        from ..control.command_line_interpreter import CommandLineInterpreter

        from ..plugins.cmdline_completer import CmdlineCompleter

        from ..buffers import Buffer

        self.__view = TextView(self)
        self.__controller = BufferController(None, self.__view,
                                             Buffer(), False,
                                             Config.root)
        
        self.__imode = imode = self.__controller.interaction_mode = CommandLineInteractionMode(self.__controller)
        self.__completer = CmdlineCompleter(self.__controller)
        self.add_next_responders(self.__completer, self.__controller)
        self.__interpreter = CommandLineInterpreter()


        self.cancelled = imode.cancelled
        self.accepted = imode.accepted

        imode.accepted.connect(self.__run_command)

        self.__view.modelines = []

        layout.addWidget(self.__view)
        self.setFocusProxy(self.__view)
        
        self.setMaximumHeight(40)
    
    def __run_command(self):
        try:
            self.__interpreter.exec(app(), self.__imode.current_cmdline)
        except RuntimeError as exc:
            self.hide()
            interactive.run('show_error', exc)
        else:
            self.hide()



    def set_cmdline(self, text):
        self.__imode.current_cmdline = text

    def showEvent(self, event):
        event.accept()
        
        self.anim = anim = QPropertyAnimation(self, 'windowOpacity')
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(0.9)
        anim.setEasingCurve(QEasingCurve.InOutQuart)
        anim.start()

class MainWindow(AbstractWindow, QMainWindow, metaclass=ABCWithQtMeta):
    def __init__(self):
        super().__init__()
        self.__cmdline = CommandLineWidget()
        self.__cmdline.cancelled.connect(self.deactivate_cmdline)

        self.statusBar()
        self.setUnifiedTitleAndToolBarOnMac(True)

        self.__mdi = QMdiArea(self)
        self.setCentralWidget(self.__mdi)
        self.__mdi.setDocumentMode(True)
        self.__mdi.setViewMode(QMdiArea.TabbedView)
        self.__mdi.subWindowActivated.connect(self.__on_sub_window_activated)

        self._menus_by_hier = {}
        self._command_for_action = {}
        self._item_for_action = {}
        self.rebuild_menus()

        self.setStyleSheet('''
                           QStatusBar
                           {
                               font-size: 12pt;
                           }
                           ''')

    @property
    def editors(self):
        for win in self.__mdi.subWindowList():
            yield win.widget()

    def closeEvent(self, event):
        for editor in self.editors:
            if not app().close(editor):
                event.ignore()
                break
        else:
            event.accept()



    def next_tab(self):
        self.__mdi.activateNextSubWindow()

    def prev_tab(self):
        self.__mdi.activatePreviousSubWindow()

    def activate_cmdline(self):

        self.__cmdline.show()
        self.__cmdline.setFocus()

        r = self.__cmdline.rect()
        r.moveBottomLeft(self.statusBar().mapToGlobal(self.statusBar().rect().topLeft()))
        self.__cmdline.move(r.topLeft())
        self.__cmdline.setFixedWidth(self.width())

        nr = self.next_responder
        self.clear_next_responders()
        asw = self.__mdi.activeSubWindow()
        if asw is not None:
            self.add_next_responders(asw.widget())
        self.add_next_responders(self.__cmdline)

    def deactivate_cmdline(self):
        self.__cmdline.hide()
        asw = self.__mdi.activeSubWindow()
        if asw is not None:
            self.next_responder = asw.widget()

    def set_cmdline(self, text):
        self.activate_cmdline()
        self.__cmdline.set_cmdline(text)

    def __kill_editor(self, editor):
        for sw in self.__mdi.subWindowList():
            if sw.widget() is editor:
                editor.deleteLater()
                sw.deleteLater()
                return

    def add_editor(self, editor):
        '''
        Add an editor to this window.
        '''

        sw = self.__mdi.addSubWindow(editor)
        editor.show()
        editor.window_should_kill_editor.connect(self.__kill_editor)
        editor.is_modified_changed.connect(self.__child_modified_changed, add_sender=True)
        
    def focusInEvent(self, event):
        app().next_responder = self

    def __child_modified_changed(self, sender):
        if sender is self.__mdi.activeSubWindow().widget():
            self.setWindowModified(sender.is_modified)

    def __on_sub_window_activated(self, win):
        if win is not None:
            editor = win.widget()
            self.next_responder = editor
            self.setWindowModified(editor.is_modified)

    def rebuild_menus(self):
        logging.debug('rebuilding menus')

        for menu in self._menus_by_hier.values():
            menu.setParent(None)

        self._menus_by_hier.clear()

        from ..control import interactive
        
        def create_menu(qt_menu, ce_menu):
            for name, item in ce_menu:
                if isinstance(item, interactive.MenuItem):
                    action = qt_menu.addAction(name)
                    action.setShortcut(to_q_key_sequence(item.keybinding))
                    self._item_for_action[action] = item
                    action.triggered.connect(self._on_action_triggered)
                else:
                    submenu = qt_menu.addMenu(name)
                    create_menu(submenu, item)
            
        create_menu(self.menuBar(), interactive.root_menu)
    
    def _on_action_triggered(self):
        from ..control import interactive
        item = self._item_for_action[self.sender()]

        try:
            interactive.dispatcher.dispatch(self, item.interactive_name, *item.interactive_args)
        except Exception as exc:
            interactive.dispatcher.dispatch(self, 'show_error', exc)


@interactive.interactive('set_cmdline')
def set_cmdline(win: MainWindow, *text):
    win.set_cmdline(' '.join(text))


@interactive.interactive('show_error')
def show_error(win: MainWindow, msg):
    sb = win.statusBar()
    app().beep()
    sb.showMessage(str(msg) + ' [' + type(msg).__name__ + ']', 2500)

@interactive.interactive('activate_cmdline')
def activate_cmdline(win: MainWindow):
    @in_main_thread
    def update():
        win.activate_cmdline()
        app().next_responder = win
#         app().next_responder = win.cmdline
#         win.next_responder = win.cmdline
#         win.cmdline.show()
    update()
#     win.cmdline.raise_()
