
from stem.abstract.application import AbstractWindow, app, AbstractApplication
from stem.abstract import ui

from stem.core.errors import UserError
from stem.core.responder import Responder
from stem.core.nconfig import Config, Settings, Field
from .qt_util import *
from ..core.notification_queue import in_main_thread
from ..control import interactive
import traceback
import logging

class CommandLineViewSettings(Settings):
    _ns_ = 'cmdline.view'

    opacity = Field(float, 0.9, 
                    docs='view opacity (0-1)')
    animation_duration_ms = Field(int, 100, 
                                  docs='popup animation duration (ms)')
    view_height = Field(int, 70, 
                        docs='view height (px)')

    max_view_height = Field(int, 300,
                            docs='height of view when expanded (px)')


def change_listener():
    print(list(app().next_responders))

@interactive.interactive('monitor')
def monitor(app: AbstractApplication):
    app.responder_chain_changed.connect(change_listener)

class CommandLineWidget(Responder, QWidget):
    def __init__(self, parent, config, prev_responder):
        super().__init__()
        self.__parent = parent
        self.setWindowFlags(Qt.Popup)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.prev_responder = prev_responder

        self.__settings = CommandLineViewSettings.from_config(config)

        from .textlayout.widget import CodeView, CodeViewProxy
        from ..control import BufferController
        from ..control.command_line_interaction import CommandLineInteractionMode
        from ..control.command_line_interpreter import CommandLineInterpreter
        from ..control.cmdline_completer import CmdlineCompleter
        from ..control.cmdline_history import HistoryWatcher

        from ..buffers import Buffer

        self.__view = CodeView(self)
        self.__proxy = CodeViewProxy(self.__view)

        self.__controller = BufferController(buffer_set=None, 
                                             view=self.__proxy,
                                             buff=Buffer(), 
                                             provide_interaction_mode=False,
                                             config=config)
        

        
        self.__imode = CommandLineInteractionMode(self.__controller)
        self.__controller.interaction_mode = self.__imode
        self.__completer = CmdlineCompleter(self.__controller)
        self.__interpreter = CommandLineInterpreter()

        self.add_next_responders(self.__completer, self.__controller)
        self.__completer.add_next_responders(self.prev_responder)


        # forward cancelled/accepted signals
        self.cancelled = self.__imode.cancelled
        self.accepted = self.__imode.accepted

        self.__imode.accepted.connect(self.__run_command)
        self.__imode.text_written.connect(self.__on_text_written)
        
        # disable modeline for this view
        self.__view.modelines = []

        layout.addWidget(self.__view)
        self.setFocusProxy(self.__view)

        self.__view.installEventFilter(self)

        # prevent flickering when first showing view
        self.setWindowOpacity(0)
        self.__view.disable_partial_update = True
        
    def __on_text_written(self):
        if not self.isVisible():
            self.show()
        self.expand()

    def __run_command(self):
        self.hide()
        app().next_responder = self.prev_responder
        try:
            self.__interpreter.exec(app(), self.__imode.current_cmdline)
        except RuntimeError as exc:
            interactive.run('show_error', exc)

    def set_cmdline(self, text):
        self.__imode.current_cmdline = text

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonRelease:
            self.expand()

        return super().eventFilter(obj, ev)

    def __calculate_bottom_left(self):
        bleft = self.__parent.statusBar().mapToGlobal(self.__parent
                                                          .statusBar()
                                                          .rect()
                                                          .topLeft())

        ay = -7
        ax = 0
        bleft.setX(bleft.x() + ax)
        bleft.setY(bleft.y() + ay)

        return bleft

    def expand(self):
        geom = self.geometry()
        geom.setWidth(self.__parent.width())
        geom.setHeight(self.__settings.max_view_height)
        geom.moveBottomLeft(self.__calculate_bottom_left())
        self.setGeometry(geom)

    def showEvent(self, event):
        geom = self.geometry()
        geom.setWidth(self.__parent.width())
        geom.setHeight(self.__settings.view_height)
        geom.moveBottomLeft(self.__calculate_bottom_left())
        self.setGeometry(geom)        

        event.accept()
        app().next_responder = self
        self.anim = anim = QPropertyAnimation(self, 'windowOpacity')
        anim.setDuration(self.__settings.animation_duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(self.__settings.opacity)
        anim.setEasingCurve(QEasingCurve.InOutQuart)
        anim.start()
        self.__controller.refresh_view(full=True)

    def hideEvent(self, event):
        event.accept()
        self.setWindowOpacity(0)

class MainWindow(AbstractWindow, QMainWindow, metaclass=ABCWithQtMeta):
    def __init__(self, config):
        super().__init__()
        self.__cmdline = CommandLineWidget(self, config, self)
        self.__cmdline.cancelled.connect(self.deactivate_cmdline)
        

        self.statusBar()
        self.setUnifiedTitleAndToolBarOnMac(True)

        self.__mdi = QMdiArea(self)
        self.setCentralWidget(self.__mdi)
        self.__mdi.setDocumentMode(True)
        self.__mdi.setViewMode(QMdiArea.TabbedView)
        self.__mdi.subWindowActivated.connect(self.__on_sub_window_activated)
        self.__mdi.setTabsMovable(True)

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

    def deactivate_cmdline(self):
        self.__cmdline.hide()

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
        
    def event(self, evt):
        if evt.type() == QEvent.WindowActivate:
            app().next_responder = self
        return super().event(evt)


    def __child_modified_changed(self, sender):
        self.__update_window_path()

    def __update_window_path(self):
        asw = self.__mdi.activeSubWindow()
        if asw is None:
            return

        editor = asw.widget()
        self.next_responder = editor
        self.setWindowModified(editor.is_modified)
        if editor.path is not None:
            self.setWindowFilePath(str(editor.path.absolute()))
            self.setWindowTitle(editor.path.name + ' [*]')
            asw.setWindowTitle(editor.path.name)
        else:
            self.setWindowFilePath(None)
            self.setWindowTitle('Untitled [*]')
            asw.setWindowTitle('Untitled')

    def __on_sub_window_activated(self, win):
        self.__update_window_path()
        asw = self.__mdi.activeSubWindow()

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


    def close(self):
        QMainWindow.close(self)

@interactive.interactive('set_cmdline')
def set_cmdline(win: MainWindow, *text):
    win.set_cmdline(' '.join(text))

@interactive.interactive('show_error')
def show_error(win: MainWindow, msg):
    sb = win.statusBar()
    app().beep()
    sb.showMessage(str(msg) + ' [' + type(msg).__name__ + ']', 2500)

    if isinstance(msg, BaseException):
        tb = ''.join(traceback.format_exception(type(msg),
                                                msg,
                                                msg.__traceback__))
        if isinstance(msg, UserError):
            logging.debug('User error passed to show_error:\n%s', tb)
        else:
            logging.error('Exception passed to show_error:\n%s', tb)

@interactive.interactive('activate_cmdline')
def activate_cmdline(win: MainWindow):
    @in_main_thread
    def update():
        win.activate_cmdline()
    update()
