
from .basic_view import BasicTextView
from ..abstract.code import AbstractCallTip
from ..core import AttributedString
from ..control.interactive import interactive
from .text_rendering import text_size

from PyQt4 import Qt

class CallTipView(BasicTextView):

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.Qt.ToolTip)
        
        self.setVerticalScrollBarPolicy(Qt.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.Qt.ScrollBarAlwaysOff)
        
        self.__model = None
            
        
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