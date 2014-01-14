


from PyQt4.Qt import *
from .widget import TextWidget




class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUnifiedTitleAndToolBarOnMac(True)
        m = self.mdi = QMdiArea(self)
        m.setViewMode(QMdiArea.TabbedView)
        m.setTabsClosable(True)
        m.setTabsMovable(True)
        m.setDocumentMode(True)

        
        self.setCentralWidget(self.mdi)

        menu_bar = QMenuBar()
        file_menu = QMenu('&File', menu_bar)
        file_menu.addAction('Open', self.open, 'Ctrl+O')


        menu_bar.addMenu(file_menu)
        menu_bar.show()
        
        self.menu_bar = menu_bar

        self.open(__file__)

        
    
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
            with tw.manip.history.ignoring(), open(path, 'r') as f:
                tw.presenter.canonical_cursor.insert(f.read()).move(0,0)
                tw.presenter.refresh_view(full=True)
            
            mw = self.mdi.addSubWindow(tw)
            mw.setWindowState(Qt.WindowMaximized)
            
            return True
            


    


class Application(QApplication):

    def exec_(self):
        
        mw = MainWindow()
        mw.show()
        mw.raise_()
        
        return super().exec_()





if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(Application(sys.argv).exec_())
