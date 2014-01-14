

from PyQt4.Qt import *

from .. import presentation, buffers
from . import view


class TextWidget(view.TextView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.buffer = buffers.Buffer()
        
        manip = buffers.BufferManipulator(self.buffer)
        self.manip = manip
        self.presenter = presentation.Presenter(self, self.buffer)
        self.presenter.canonical_cursor = buffers.Cursor(manip)
        self.presenter.anchor_cursor = None
        self.interaction_mode = presentation.CUAInteractionMode(self.presenter)
        

    def show_modeline(self, text):
        self.interaction_mode.show_modeline(text)

    

    




if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    widget = TextWidget()
    widget.show()
    widget.raise_()
    app.exec_()
    


