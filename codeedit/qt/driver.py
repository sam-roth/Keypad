


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


        menu_bar.addMenu(file_menu)
        menu_bar.show()
        
        self.menu_bar = menu_bar

        self.open(__file__)

    
    def _after_tab_change(self, window):

        try:
            controller = window.widget().controller    
        except AttributeError:
            return

        try:
            path = controller.tags['path']
        except KeyError:
            return

        self.setWindowFilePath(path.as_posix())
        
    
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
            with tw.controller.manipulator.history.ignoring(), open(path, 'r') as f:
                tw.controller.canonical_cursor.insert(f.read()).move(0,0)
                tw.controller.refresh_view(full=True)

            
            tw.controller.request_init()
            tw.controller.add_tags(path=pathlib.Path(path))

            mw = self.mdi.addSubWindow(tw)
            mw.setWindowState(Qt.WindowMaximized)

            self.setWindowFilePath(path)
            
            return True
            

from ..core import notification_center


class _ProcessPosted(QEvent):
    ProcessPostedType = QEvent.registerEventType()
    
    def __init__(self):
        super().__init__(_ProcessPosted.ProcessPostedType)


class Application(QApplication):

    def exec_(self):
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
