

from PyQt4.Qt import *

from .. import control, buffers
from . import view


class TextWidget(view.TextView):

    def __init__(
            self, 
            parent=None, 
            provide_completion_view=True,
            provide_interaction_mode=True):
        super().__init__(parent, provide_completion_view=provide_completion_view)

        self.buffer = buffers.Buffer()
        self.controller = control.Controller(self, self.buffer, provide_interaction_mode=provide_interaction_mode)

    def show_modeline(self, text):
        self.interaction_mode.show_modeline(text)

    

    




if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    widget = TextWidget()
    widget.show()
    widget.raise_()
    app.exec_()
    


