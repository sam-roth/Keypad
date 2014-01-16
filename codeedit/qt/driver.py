


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

        self.open('/Users/Sam/Desktop/Projects/codeedit2/test2.py')

    
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
            
            path = pathlib.Path(path)

            with tw.controller.history.ignoring():
                tw.controller.replace_from_path(path)
            
            
            mw = self.mdi.addSubWindow(tw)
            mw.setWindowState(Qt.WindowMaximized)
            mw.setWindowTitle(path.name)

            self.setWindowFilePath(path.as_posix())
            
            return True
            

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
