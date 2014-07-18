

from PyQt4.Qt import *

from .. import control, buffers
from . import basic_view


class TextWidgetMixin:

    def __init__(
            self, 
            parent=None, 
            provide_interaction_mode=True,
            **kw):
        super().__init__(parent, **kw)

        self.buffer = buffers.Buffer()
        self.controller = control.BufferController(None, self, 
                                                   self.buffer,
                                                   provide_interaction_mode=provide_interaction_mode)

    def show_modeline(self, text):
        self.interaction_mode.show_modeline(text)

class BasicTextWidget(TextWidgetMixin, basic_view.BasicTextView):
    pass
    

    




if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    widget = TextWidget()
    widget.show()
    widget.raise_()
    app.exec_()
    


