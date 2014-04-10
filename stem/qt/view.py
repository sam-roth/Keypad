




from .basic_view import BasicTextView, TextViewSettings

from PyQt4 import Qt


class TextView(BasicTextView):
    def __init__(self, *args, **kw):
#         self.__cursor_pos = None
        super().__init__(*args, **kw)
        from .call_tip_view import CallTipView
        self.__call_tip_view = CallTipView(self.settings, self)
    
    @property
    def call_tip_model(self):
        return self.__call_tip_view.model
        
    @call_tip_model.setter
    def call_tip_model(self, value):
        self.__call_tip_view.model = value
        self.__move_call_tip_view()
        
    @property
    def cursor_pos(self):
        return self.__cursor_pos    
        
    @cursor_pos.setter
    def cursor_pos(self, value):
        if value is not None and self.cursor_pos is not None:
            if value[0] != self.cursor_pos[0] and self.call_tip_model is not None:
                self.call_tip_model = None
        
        self.__cursor_pos = value
        
        
    def __move_call_tip_view(self):
        try:
            self.__call_tip_view.move(self.__aux_view_pos(self.__call_tip_view.size()))
        except IndexError:
            pass
    
    def __aux_view_pos(self, size):
        x,y = self.map_from_plane(*self.cursor_pos)
        corner = self.mapToGlobal(Qt.QPoint(x, y - self.line_height))
        normal_compl_rect = Qt.QRect(corner, 
                                     size)
        normal_compl_rect.moveBottomLeft(corner)
        
        intersect = Qt.QApplication.desktop().screenGeometry().intersected(normal_compl_rect)
        if intersect != normal_compl_rect:
            normal_compl_rect.moveTopLeft(
                self.mapToGlobal(
                    Qt.QPoint(x, y + self.line_height)))
        
        
        return normal_compl_rect.topLeft()
