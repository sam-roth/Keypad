

from PyQt4.Qt import *

from .. import control, buffers
from . import view


class TextWidget(view.TextView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.buffer = buffers.Buffer()
        self.presenter = control.Controller(self, self.buffer)

    def show_modeline(self, text):
        self.interaction_mode.show_modeline(text)

    

    




if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    widget = TextWidget()
    widget.show()
    widget.raise_()
    app.exec_()
    


