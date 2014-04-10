
from .basic_view import BasicTextView, TextViewSettings
from ..abstract.code import AbstractCallTip
from ..core import AttributedString
from ..control.interactive import interactive
from .text_rendering import text_size
from ..options import CallTipSettings
from ..core.nconfig import Config

from PyQt4 import Qt

class CallTipView(BasicTextView):

    def __init__(self, settings, parent=None):
        '''
        :type settings: TextViewSettings
        '''
        super().__init__(parent)

        self.setWindowFlags(Qt.Qt.ToolTip)
        
        self.setVerticalScrollBarPolicy(Qt.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.Qt.ScrollBarAlwaysOff)
        
        config = settings.config
        self.settings = settings
        
        self.ct_settings = CallTipSettings.from_config(settings.config)
        self.ct_settings.value_changed += self.__reload_conf
        self.__reload_conf()
        
        self.__model = None
        
        
    def __reload_conf(self, *args):
#         s = self.ct_settings
#         if s.view_opacity < 0.95:
#             self.setAttribute(Qt.Qt.WA_TranslucentBackground, True)
#         else:
#             self.setAttribute(Qt.Qt.WA_TranslucentBackground, False)
            
#             self.setWindowFlags(self.windowFlags() | Qt

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
            self.lines = [value.to_astring(None)]
            tsz = text_size(self.lines[0], self.settings).toSize()
            tsz.setWidth(tsz.width() + 10)
            tsz.setHeight(tsz.height() + 10)
            self.resize(tsz)
            self.full_redraw()
            self.show()
        else:
            self.hide()
        
        
    def keyPressEvent(self, event):
        event.ignore()
        
class MockCallTip(AbstractCallTip):    
    def to_astring(self, arg=None):
        return AttributedString('foo(bar, baz)')
# 
# show_mocktip = None
# 
# @interactive('add_mocktip')
# def add_mocktip(_: object):
#     global show_mocktip
#     if show_mocktip is not None:
#         return
#     
#     from ..control import BufferController
#     
#     @interactive('mocktip')
#     def show_mocktip(bc: BufferController):
#         show_mocktip_impl(bc.view)
#     
#     
# def show_mocktip_impl(tv):
#     t = CallTipView(tv.settings, tv)
#     t.setFocusProxy(tv)
#     t.move(tv.rect().center())
#     t.model = MockCallTip()
#     t.show()
# 
# 
# @interactive('domt')
# def do_mocktip(_: object):
#     interactive.run('add_mocktip')
#     interactive.run('mocktip')
# 
# @interactive('mt2')
# def mt2(