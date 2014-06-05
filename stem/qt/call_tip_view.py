
from .textlayout.viewport import TextViewport

from .basic_view import BasicTextView, TextViewSettings
from ..abstract.code import AbstractCallTip
from ..core import AttributedString
from ..control.interactive import interactive
from .text_rendering import text_size
from ..options import CallTipSettings
from ..core.nconfig import Config

from stem.buffers.cursor import Cursor

from PyQt4 import Qt

class CallTipView(TextViewport): #BasicTextView):

    def __init__(self, settings, parent=None):
        '''
        :type settings: TextViewSettings
        '''
        super().__init__(parent, config=settings.config)

        self.setWindowFlags(Qt.Qt.ToolTip)
        
#         self.setVerticalScrollBarPolicy(Qt.Qt.ScrollBarAlwaysOff)
#         self.setHorizontalScrollBarPolicy(Qt.Qt.ScrollBarAlwaysOff)

        self.origin = Qt.QPointF(2, 2)
        self.right_margin = 0
        
        config = settings.config
        self.__settings = settings
        
        self.ct_settings = CallTipSettings.from_config(settings.config)
        self.ct_settings.value_changed += self.__reload_conf
        self.__reload_conf()
        
        self.__model = None
        
        
    def __reload_conf(self, *args):
        self.setWindowOpacity(self.ct_settings.view_opacity)
        
    @property
    def model(self):
        '''
        :rtype: AbstractCallTip
        '''
        return self.__model
    
    @model.setter
    def model(self, value):
        '''
        :type value: AbstractCallTip
        '''
        
        self.__model = value
        
        if value is not None:

            c = Cursor(self.buffer)
            c.remove_to(c.clone().last_line().end())
            self.buffer.insert((0, 0), value.to_astring(None))

#             self.lines = [value.to_astring(None)]
            tsz = text_size(self.buffer.lines[0], self.__settings).toSize()
            tsz.setWidth(tsz.width() + 10)
            tsz.setHeight(tsz.height() + 10)
            self.resize(tsz)
#             self.full_redraw()
            self.show()
        else:
            self.hide()
        
        
    def keyPressEvent(self, event):
        event.ignore()
        
class MockCallTip(AbstractCallTip):    
    def to_astring(self, arg=None):
        return AttributedString('foo(bar, baz)')

