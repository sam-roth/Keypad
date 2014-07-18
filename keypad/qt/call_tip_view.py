
from .textlayout.viewport import TextViewport

from ..abstract.code import AbstractCallTip
from ..core import AttributedString
from ..control.interactive import interactive
from ..options import CallTipSettings
from ..core.nconfig import Config

from keypad.buffers.cursor import Cursor

from PyQt4 import Qt

class CallTipView(TextViewport):

    def __init__(self, settings, parent=None):
        '''
        :type settings: TextViewSettings
        '''
        super().__init__(parent, config=settings.config)

        self.setWindowFlags(Qt.Qt.ToolTip)
        
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
        try:

            if value is not None:
    
                c = Cursor(self.buffer)
                c.remove_to(c.clone().last_line().end())
                self.buffer.insert((0, 0), value.to_astring(None))
    
                metrics = Qt.QFontMetrics(self._settings.q_font)
                tsz = metrics.size(0, self.buffer.lines[0].text)
    
    #             tsz = text_size(self.buffer.lines[0], self.__settings).toSize()
                tsz.setWidth(tsz.width() + 10)
                tsz.setHeight(tsz.height() + 10)
                self.resize(tsz)
                self.show()
            else:
                self.hide()
            
        except:
            import logging
            logging.exception('error setting call tip model')
            raise
            
    def keyPressEvent(self, event):
        event.ignore()
        
class MockCallTip(AbstractCallTip):    
    def to_astring(self, arg=None):
        return AttributedString('foo(bar, baz)')

