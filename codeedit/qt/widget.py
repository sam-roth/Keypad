

from PyQt4.Qt import *

from .. import presenter, buffer, cursor, buffer_manipulator
from . import view


class TextWidget(view.TextView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.buffer = buffer.Buffer()
        
        manip = buffer_manipulator.BufferManipulator(self.buffer)
        self.manip = manip
        self.presenter = presenter.Presenter(self, self.buffer)
        self.presenter.canonical_cursor = cursor.Cursor(manip)
        self.presenter.anchor_cursor = None
        self.interaction_mode = presenter.CUAInteractionMode(self.presenter)
        

    def show_modeline(self, text):
        self.interaction_mode.show_modeline(text)

    

    




if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    widget = TextWidget()
    widget.show()
    widget.raise_()
    app.exec_()
    


