

from PyQt4.Qt import *
import pathlib
from .view import TextView
from .qt_util import *

from ..core import Signal
from ..core.command import Command
from ..core.responder import Responder


import logging


class CloseEvent(object):
    def __init__(self):
        self.is_intercepted = False

    def intercept(self):
        self.is_intercepted = True

class BufferSetView(Responder, QMainWindow):

    def __init__(self):
        super().__init__()
        
        self.setAttribute(Qt.WA_QuitOnClose, False)
        
        self._menus_by_hier = {}
        self._command_for_action = {}
        self._item_for_action = {}
        self._active_view = None
        self._active_tab = None

        self._split = split = QSplitter(Qt.Vertical, self)

        m = self._mdi = QMdiArea(split)
        m.setViewMode(QMdiArea.TabbedView)
        m.setTabsClosable(True)
        m.setTabsMovable(True)
        m.setDocumentMode(True)
        m.subWindowActivated.connect(self._on_subwindow_activated)

        split.addWidget(m)

        self.setCentralWidget(split)
    
        #self.responder_chain_changed.connect(self.rebuild_menus)
        self._command_line_view = None
        qApp.focusChanged.connect(self.__app_focus_change)

        self.rebuild_menus()
    

    @property
    def active_tab(self):
        return self._active_tab


    def next_tab(self, n_tabs=1):
        if n_tabs > 0:
            for _ in range(n_tabs):
                self._mdi.activateNextSubWindow()
        else:
            for _ in range(-n_tabs):
                self._mdi.activatePreviousSubWindow()
                

    
    def __app_focus_change(self, old, new):

        active_tab = self._mdi.activeSubWindow()
        active_tab_view = active_tab.widget() if active_tab else None
        
        if new is active_tab_view or new is self._command_line_view:
            self._active_view = new
            self.active_view_changed(new)


    @Signal
    def will_close(self, event):
        pass

    def closeEvent(self, event):
        ce = CloseEvent()
        self.will_close(ce)
        if ce.is_intercepted:
            event.ignore()
            return

        # prevents SIGSEGV on window close
        # (This object doesn't exist when subviews are destroyed normally, but
        # Python doesn't know that.)
        for win in self._mdi.subWindowList():
            win.close()

        super().closeEvent(event)

    def close_subview(self, view):
        for win in self._mdi.subWindowList():
            if win.widget() is view:
                self._mdi.removeSubWindow(win)
                break
            

    def show_save_all_prompt(self, unsaved_list, n_untitled):
        msgbox = QMessageBox(self)
        msgbox.setWindowFlags(Qt.Sheet)
        msgbox.setWindowModality(Qt.WindowModal)
        msgbox.setText('There are {} unsaved buffers.'.format(n_untitled + len(unsaved_list)))
        msgbox.setInformativeText("Do you want to save your changes?")
        
        def gen():
            yield 'The following buffers are unsaved:\n'
            if n_untitled:
                yield '- {} untitled documents\n'.format(n_untitled)
            for item in unsaved_list:
                yield str(item) + '\n'

        msgbox.setDetailedText('\n'.join(gen()))
        msgbox.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel)
        review_chgs = msgbox.addButton('Review Changes…', QMessageBox.AcceptRole)
        msgbox.setDefaultButton(review_chgs)
        ret = msgbox.exec_()

        if msgbox.defaultButton() is review_chgs:
            return 'review'
        elif ret == QMessageBox.Discard:
            return 'discard-all'
        else:
            return None


    def show_save_prompt(self, path=None):
        msgbox = QMessageBox(self)
        if path:
            msgbox.setText('This buffer contains unsaved changes to {!r}.'.format(path.as_posix()))
        else:
            msgbox.setText('This buffer is unsaved.')

        msgbox.setWindowFlags(Qt.Sheet)
        msgbox.setWindowModality(Qt.WindowModal)
        msgbox.setInformativeText('Do you want to save your changes?')
        msgbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

        ret = msgbox.exec_()

        outcomes = {
            QMessageBox.Save: 'save',
            QMessageBox.Cancel: 'cancel',
            QMessageBox.Discard: 'discard'
        }

        return outcomes.get(ret, 'cancel')


    def show_internal_failure_msg(self):
        
        msgbox = QMessageBox(self)
        msgbox.setText('This application was not able to quit because of a problem.')
        msgbox.setInformativeText(
            'If you intended to exit the application, please save and close buffers manually and then close the application.\n'
            'If this message occurs after buffers are saved, click "Terminate Application". For debugging '
            'details, click "Show Details...".'
        )

        import traceback

        msgbox.setIcon(QMessageBox.Warning)

        try:
            logging.exception('Internal failure message presented to user.')
            msgbox.setDetailedText(traceback.format_exc())
        except:
            msgbox.setDetailedText(traceback.format_exc())


        ret_to_app = msgbox.addButton('Return to Application', QMessageBox.AcceptRole)
        term_app = msgbox.addButton('Terminate Application', QMessageBox.DestructiveRole)
        
        msgbox.setDefaultButton(ret_to_app)

        result = msgbox.exec_()



        if msgbox.clickedButton() == term_app:
            import os
            logging.fatal('User terminated application from internal failure message.')
            os._exit(10)
        else:
            logging.warning('User returned to application from internal failure message.')
            







    @property 
    def command_line_view(self):
        if self._command_line_view is None:
            self._command_line_view = TextView(self)
            self._split.addWidget(self._command_line_view)

        return self._command_line_view

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

    def _on_subwindow_activated(self, window):
        self.active_view_changed(window.widget() if window is not None else None)
        if window:
            window.setWindowState(Qt.WindowMaximized)
        self._active_tab = window.widget() if window else None

    @property
    def active_view(self): 
        return self._active_view
    
    @active_view.setter
    def active_view(self, value): 
        if value is self._command_line_view:
            value.setFocus(Qt.OtherFocusReason)
        else:
            for win in self._mdi.subWindowList():
                if win.widget() is value:
                    self._mdi.setActiveSubWindow(win)
                    self._on_subwindow_activated(win)
                    win.widget().setFocus(Qt.OtherFocusReason)
                    return

    @property
    def path(self):
        return pathlib.Path(self.windowFilePath())

    
    @path.setter
    def path(self, val):
        if self._mdi.activeSubWindow():
            if val:
                self._mdi.activeSubWindow().setWindowTitle(val.name)
            else:
                self._mdi.activeSubWindow().setWindowTitle('[unsaved]')
        self.setWindowFilePath(str(val) if val else None)


    @property
    def modified(self): 
        return self.isWindowModified()
    
    @modified.setter
    def modified(self, value): 
        self.setWindowModified(value)


    @Signal
    def active_view_changed(self, view):
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

    def run_save_dialog(self, initial):
        initial = pathlib.Path(initial) if initial else None
        if initial is not None and not initial.is_dir:
            initial = initial.parent
        file_name = QFileDialog.getSaveFileName(self, 'Save File', initial.as_posix() if initial is not None else None)
        
        if file_name:
            return pathlib.Path(file_name)
        else:
            return None
    
    def add_buffer_view(self):
        view = TextView(self)
        win = self._mdi.addSubWindow(view)
        win.setWindowState(Qt.WindowMaximized)
        self._on_subwindow_activated(win)
        return view
        
