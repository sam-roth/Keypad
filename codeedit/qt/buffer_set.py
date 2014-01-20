

from PyQt4.Qt import *
import pathlib
from .view import TextView

from ..core import Signal
from ..core.command import Command
from ..core.responder import Responder, responds

import logging

class BufferSetView(Responder, QMainWindow):

    def __init__(self):
        super().__init__()
        
        self._menus_by_hier = {}
        self._command_for_action = {}

        m = self._mdi = QMdiArea(self)
        self.setCentralWidget(m)
        m.setViewMode(QMdiArea.TabbedView)
        m.setTabsClosable(True)
        m.setTabsMovable(True)
        m.setDocumentMode(True)
        m.subWindowActivated.connect(self._on_subwindow_activated)
    
        self.responder_chain_changed.connect(self.rebuild_menus)

    def show_input_dialog(self, prompt):
        result, ok = QInputDialog.getText(self, prompt, prompt)
        if ok:
            return result
        else:
            return None

    def rebuild_menus(self):
        logging.debug('rebuilding menus')

        for menu in self._menus_by_hier.values():
            menu.setParent(None)

        self._menus_by_hier.clear()

        for cmd in self.responder_known_commands:
            menu = self._get_menu(cmd.menu_hier)
            
            action = QAction(cmd.name, menu)
            if cmd.keybinding is not None:
                action.setShortcut(QKeySequence(str(cmd.keybinding)))
            action.triggered.connect(self._on_action_triggered)
            menu.addAction(action)
            self._command_for_action[action] = cmd
   

                     
    def _on_action_triggered(self):
        self.perform_or_forward(self._command_for_action[self.sender()])

    def _on_subwindow_activated(self, window):
        self.active_tab_changed(window.widget() if window is not None else None)

    @property
    def active_view(self): 
        return self._mdi.activeSubWindow().widget()
    
    @active_view.setter
    def active_view(self, value): 
        for win in self._mdi.subWindowList():
            if win.widget() is value:
                self._mdi.setActiveSubWindow(win)
                self._on_subwindow_activated(win)
                return

    @property
    def path(self):
        return pathlib.Path(self.windowFilePath())

    
    @path.setter
    def path(self, val):
        self.setWindowFilePath(str(val))


    @property
    def modified(self): 
        return self.isWindowModified()
    
    @modified.setter
    def modified(self, value): 
        self.setWindowModified(value)

    @Signal
    def active_tab_changed(self, view):
        pass
    
    def _get_menu(self, hier):
        if isinstance(hier, str):
            hier = tuple(hier.split('.'))
        else:
            hier = tuple(hier)

        try:
            return self._menus_by_hier[hier]
        except KeyError:
            collected = []

            menu = self.menuBar()
            for part in hier:
                collected.append(part)
                key = tuple(collected)
                if key not in self._menus_by_hier:
                    last_menu = menu
                    self._menus_by_hier[key] = menu = QMenu(part, self)
                    last_menu.addMenu(menu)
                else:
                    menu = self._menus_by_hier[key]

            return menu
                

    def run_open_dialog(self):
        file_name = QFileDialog.getOpenFileName(self, 'Open File')

        if file_name:
            return pathlib.Path(file_name)
        else:
            return None
    
    def add_buffer_view(self):
        view = TextView()
        win = self._mdi.addSubWindow(view)
        win.setWindowState(Qt.WindowMaximized)
        self._on_subwindow_activated(win)
        return view
        
