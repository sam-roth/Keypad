

from PyQt4.Qt import *

from .. import control, buffers
from . import basic_view


class TextWidgetMixin:

    def __init__(
            self, 
            parent=None, 
            provide_interaction_mode=True):
        super().__init__(parent)

        self.buffer = buffers.Buffer()
        self.controller = control.Controller(self, self.buffer, provide_interaction_mode=provide_interaction_mode)

    def show_modeline(self, text):
        self.interaction_mode.show_modeline(text)

class BasicTextWidget(TextWidgetMixin, basic_view.TextView):
    pass
    

    




if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    widget = TextWidget()
    widget.show()
    widget.raise_()
    app.exec_()
    


