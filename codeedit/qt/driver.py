


from PyQt4.Qt import *
from .widget import TextWidget
from ..control import behavior # module contains autoconnects
from queue import Queue 

import pathlib

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUnifiedTitleAndToolBarOnMac(True)
        m = self.mdi = QMdiArea(self)
        m.setViewMode(QMdiArea.TabbedView)
        m.setTabsClosable(True)
        m.setTabsMovable(True)
        m.setDocumentMode(True)
        m.subWindowActivated.connect(self._after_tab_change)

        
        self.setCentralWidget(self.mdi)

        menu_bar = QMenuBar()
        file_menu = QMenu('&File', menu_bar)
        file_menu.addAction('Open', self.open, 'Ctrl+O')
        file_menu.addAction('Save', self.save, 'Ctrl+S')
        file_menu.addAction('Save As', self.save_as, 'Ctrl+Shift+S')
        



        menu_bar.addMenu(file_menu)
        menu_bar.show()
        
        self.menu_bar = menu_bar

        
        self._current_tab_controller = None

        self.open('/Users/Sam/Desktop/Projects/codeedit2/test2.py')
    


    def _after_tab_change(self, window):

        try:
            controller = window.widget().controller    
            self._current_tab_controller = controller
        except AttributeError:
            self._current_tab_controller = None
            return

        try:
            path = controller.tags['path']
        except KeyError:
            return

        self.setWindowFilePath(path.as_posix())
        self.setWindowModified(window.widget().controller.is_modified)


    def _after_modified_changed(self, sender, modified):
        if sender is self._current_tab_controller:
            self.setWindowModified(modified)


        
    
    def open(self, path=None):
        if path is None:
            path = QFileDialog.getOpenFileName(
                self, 
                self.tr("Open")
            )

        if not path:
            return False
        else:
            tw = TextWidget()
            
            path = pathlib.Path(path)

            tw.controller.modified_was_changed.connect(
                self._after_modified_changed, 
                add_sender=True
            )

            with tw.controller.history.ignoring():
                tw.controller.replace_from_path(path)
            
            
            mw = self.mdi.addSubWindow(tw)
            mw.setWindowState(Qt.WindowMaximized)
            mw.setWindowTitle(path.name)

            tw.controller.add_tags(qt_subwindow=mw)
            self.setWindowFilePath(path.as_posix())

            tw.controller.is_modified = False
            self._after_tab_change(mw)
            
            return True


    Save_RequestPath = object()
    Save_BufferPath = object()

    def save(self, path=Save_BufferPath):
        controller = self._current_tab_controller

        if controller is None:
            return False
        
        if path is self.Save_BufferPath:
            path = controller.tags.get('path')
        elif path is self.Save_RequestPath:
            path = None

        if path is None:
            path = QFileDialog.getSaveFileName(
                self,
                self.tr('Save')
            )
        
        if not path:
            return False

        path = pathlib.Path(path)

        controller.write_to_path(path)
        self._after_tab_change(controller.tags.get('qt_subwindow'))

    def save_as(self):
        self.save(path=self.Save_RequestPath)



            

from ..core import notification_center


class _ProcessPosted(QEvent):
    ProcessPostedType = QEvent.registerEventType()
    
    def __init__(self):
        super().__init__(_ProcessPosted.ProcessPostedType)


class Application(QApplication):

    def exec_(self):
        # Workaround for QTBUG-32789
        QFont.insertSubstitution('.Lucida Grande UI', 'Lucida Grande')
        
        self.setWheelScrollLines(10)


        mw = MainWindow()
        mw.show()
        mw.raise_()
        
        

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
