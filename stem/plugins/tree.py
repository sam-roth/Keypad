

from PyQt4.Qt import *
from stem.api import interactive, BufferSetController
from stem.abstract.application import app
from stem.core import Signal
from stem.core.responder import Responder
from stem.control.interactive import run as run_interactive


from stem.qt.buffer_set import BufferSetView
import pathlib
import os.path

class FileTree(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self._tree_view = QTreeView(self)
        
        layout.addWidget(self._tree_view)
        
        self._fs_model = QFileSystemModel(self)
        self._tree_view.setModel(self._fs_model)
        
        here = QDir.currentPath()
        self._fs_model.setRootPath(here)
        self._tree_view.setRootIndex(self._fs_model.index(here))
        self._tree_view.activated.connect(self._on_activated)
        
    @property
    def root_path(self):
        return pathlib.Path(self._fs_model.rootPath())
        
    @root_path.setter
    def root_path(self, path):
        self._fs_model.setRootPath(str(path))
        self._tree_view.setRootIndex(self._fs_model.index(str(path)))
    
    @Signal
    def path_activated(self, path):
        pass
        
    def _on_activated(self, index):
        if index.isValid():
            self.path_activated(pathlib.Path(self._fs_model.filePath(index)))
    

class FileTreeController(Responder):
    def __init__(self, ftree):
        super().__init__()
        self.file_tree = ftree
        self.file_tree.path_activated.connect(self._on_path_activated)
        
    def _on_path_activated(self, path):
        run_interactive('edit', str(path))

@interactive('qfcd')
def qfcd(ftc: FileTreeController, p: 'Path'):
    rp = str(ftc.file_tree.root_path / pathlib.Path(os.path.expanduser(str(p))))
    print(rp)
    ftc.file_tree.root_path = rp

def find_bsc(root):
    
    if isinstance(root, BufferSetController):
        return root
    else:
        for r in root.next_responders:
            res = find_bsc(r)
            if res is not None:
                return res
        else:
            return None

@interactive('qftree')
def qftree(bufset_view: BufferSetView):
    
    ft = FileTree()
    ftc = FileTreeController(ft)
    ft.controller = ftc
        
    bsc = find_bsc(app())
    bsc.add_next_responders(ftc)
            

    dw = QDockWidget()
    dw.setWidget(ft)
    bufset_view.addDockWidget(Qt.LeftDockWidgetArea, dw)
    
    