
import platform
import copy

from PyQt4.Qt               import *

from .text_rendering        import TextViewSettings, draw_attr_text
from .qt_util               import KeyEvent, ABCWithQtMeta
from ..core                 import AttributedString, Signal
from ..core.key             import SimpleKeySequence, Keys, KeySequenceDict
from ..abstract.completion  import AbstractCompletionView



completion_view_stylesheet = r"""

QWidget#outer_container {{
    background-color:       {settings.completion_bgcolor};
    border-radius:          10px;
    padding-top:            10px;
    padding-bottom:         10px;
}}


TextView {{
    border:                 none;
}}

QTreeView {{

    border:                 none;
    background-color:       rgba(0,0,0,0);
    /*background-color:       {settings.completion_bgcolor};*/
    color:                  {settings.fgcolor};
    selection-background-color: {selbg};
    font:                   13pt "Menlo";

}}


QScrollBar,QScrollBar::add-page,QScrollBar::sub-page {{
    border: none;
    background: {settings.bgcolor};
}}

QScrollBar::handle {{
    background: {selbg};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}

/*
PopupSizeGrip {{
    padding-right: 5px;
    padding-bottom: 5px;
}}
*/
"""


class CompletionListItemDelegate(QItemDelegate):

    def __init__(self, settings):
        super().__init__()
        nset = self.settings = copy.copy(settings)

        sset = self.selected_settings = copy.copy(settings)
        sch = nset.scheme
        
        sset.bgcolor = sch.emphasize(nset.q_bgcolor.name(), 1)
        sset.fgcolor = sch.emphasize(nset.fgcolor, 1)

        for s in (self.settings, self.selected_settings):
            s.q_font = QFont(s.q_font)
            s.q_font.setPointSize(13)

    def paint(self, painter, option, index):
        
        display = index.model().data(index, Qt.DisplayRole)
        
        if not isinstance(display, AttributedString):
            display = AttributedString(display)

        settings = self.selected_settings if option.state & QStyle.State_Selected \
                   else self.settings
        display.caches.clear()
        draw_attr_text(painter,
                       option.rect,
                       display,
                       settings)



class CompletionListModel(QAbstractTableModel):

    def __init__(self):
        from ..control.colors import scheme
        super().__init__()

        self._completions = ()
        
    @property
    def columns(self):
        if self._completions:
            return len(self._completions[0])
        else:
            return 1


    @property
    def completions(self):
        return self._completions

    @completions.setter
    def completions(self, val):
        self.beginResetModel()
        self._completions = tuple(val)
        self.endResetModel()


    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        else:
            return len(self.completions)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        else:
            return self.columns

    def data(self, index, role=Qt.DisplayRole):
        if (not index.parent().isValid()) and \
                role == Qt.DisplayRole and index.column() < self.columns:
            return self.completions[index.row()][index.column()]
        else:
            return None


def qt_prop(getter, setter):


    def fget(self):
        return getattr(self, getter)()

    def fset(self, val):
        getattr(self, setter)(val)

    return property(fget, fset)





class PopupSizeGrip(QWidget):
    '''
    QSizeGrip doesn't work correctly on popups. This should.
    '''

    def __init__(self, parent=None):
        super().__init__(parent)
        curs = self.cursor()
        curs.setShape(Qt.SizeFDiagCursor)
        self.setCursor(curs)


        self.setMinimumSize(10, 10)
        
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

    def mouseDownEvent(self, event):
        event.accept()

    def mouseMoveEvent(self, event):
        win = self.window()

        geom = win.frameGeometry()
        geom.setBottomRight(event.globalPos())
        win.resize(geom.size())

class CompletionView(QWidget, AbstractCompletionView, metaclass=ABCWithQtMeta):

    
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        from . import view

        if settings is None:
            settings = TextViewSettings()
        else:
            settings = copy.copy(settings)


        settings.q_bgcolor = settings.q_completion_bgcolor
        scheme = settings.scheme
        
        self._outer_layout = QVBoxLayout(self)

        self._outer_container = QWidget(self)
        self._outer_container.setObjectName('outer_container')
        self._outer_container_layout = QVBoxLayout(self._outer_container)
        self._outer_container_layout.setContentsMargins(0,10,0,0)
        self._container = QSplitter(Qt.Vertical, self._outer_container)
        self._container.setObjectName('container')
        self._container.setContentsMargins(0,0,0,0)
        self._outer_layout.addWidget(self._outer_container)
        self._outer_layout.setContentsMargins(0,0,0,0)
        self._outer_container_layout.addWidget(self._container)

        self._listWidget = QTreeView(self._container)
        self._docs = view.TextView(self._container)
        self._docs.update_plane_size()
        self._docs.disable_partial_update = True
        self._docs.settings = settings

        self._container.addWidget(self._listWidget)
        self._container.addWidget(self._docs)

        #self._layout = QVBoxLayout(self._container)
        #self._layout.addWidget(self._listWidget)
        #self._layout.addWidget(self._docs)

        self._size_grip = PopupSizeGrip(self._outer_container)
        
        self._sg_sublayout = QHBoxLayout()
        self._outer_container_layout.addLayout(self._sg_sublayout)
        self._sg_sublayout.addStretch()
        self._sg_sublayout.addWidget(self._size_grip)
        

        self._outer_container_layout.addWidget(self._size_grip)
        

        self.setWindowFlags(Qt.Popup)
        
        #self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        #self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        self._listWidget.setAttribute(Qt.WA_MacShowFocusRect, False)
        self._listWidget.setHeaderHidden(True)

        #self._docs.scrolled.connect(self._on_scroll)
        

        self.setStyleSheet(completion_view_stylesheet.format(
            settings=settings,
            selbg=scheme.emphasize(scheme.bg, 1)
        ))

        self.model = CompletionListModel()
        self._listWidget.setModel(self.model)
        self._listWidget.setItemDelegate(CompletionListItemDelegate(settings))
        self._listWidget.selectionModel().currentRowChanged.connect(self.after_current_row_change)
        self._listWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setFocusProxy(self._listWidget)
        self._listWidget.installEventFilter(self)
        #self._docs.installEventFilter(self)
        self._docs.setFocusProxy(self._listWidget)
        
        self.done       += self._close

        self.model.modelReset.connect(self.on_model_reset)

        self.resize(400, 400)
        self._pos_locked = self.pos()

    #def _on_scroll(self, start_line):
    #    self._docs.start_line = start_line
    #    self._docs.full_redraw()


    
    visible = qt_prop('isVisible', 'setVisible')

    def move_(self, *args, **kw):
        try:
            self._pos_locked = None
            self.move(*args, **kw)
        finally:
            self._pos_locked = self.pos()


    def moveEvent(self, event):
        print('moved', event.pos(), event.oldPos(), self._pos_locked)
        if self._pos_locked is not None and event.pos() != self._pos_locked:
            self.move(self._pos_locked)
        else:
            super().moveEvent(event)

    @property
    def current_row(self): 
        return self._listWidget.selectionModel().currentIndex().row()
    

    @property
    def completions(self): 
        return self.model.completions
    
    @completions.setter
    def completions(self, value): 
        self.model.completions = value

    
    @property
    def anchor(self): 
        return self._anchor
    
    @anchor.setter
    def anchor(self, value): 
        self._anchor = value


    @Signal
    def key_press(self, event):
        pass


    @property
    def doc_view_visible(self): 
        return self._docs.isVisible()
    
    @doc_view_visible.setter
    def doc_view_visible(self, value): 
        self._docs.setVisible(value)

    
    @property
    def doc_view(self): return self._docs


    @property
    def doc_lines(self):
        return self._docs.lines

    @doc_lines.setter
    def doc_lines(self, val):
        self._docs.lines = val
        self._docs.full_redraw()

    @property
    def doc_plane_size(self):
        return self._docs.plane_size

    def _close(self, comp_idx):
        self.close()

    def showEvent(self, evt):
        super().showEvent(evt)

    def on_model_reset(self):
        self._listWidget.resizeColumnToContents(0)
        self._listWidget.selectionModel().setCurrentIndex(
            self.model.index(0,0), 
            QItemSelectionModel.ClearAndSelect |
            QItemSelectionModel.Rows)

    def after_current_row_change(self, current, previous):
        self.row_changed(current.row())

    def _event_filter_check(self, receiver):
        return receiver is self._listWidget or receiver is self._docs

    def eventFilter(self, receiver, event):

        if event.type() == QEvent.KeyPress and self._event_filter_check(receiver):
            
            ignored_keys = [
                Qt.Key_Down, Qt.Key_Up,
                Qt.Key_PageUp, Qt.Key_PageDown,
                Qt.Key_Home, Qt.Key_End
            ]

            if event.key() in ignored_keys:
                return False
            elif event.key() in (Qt.Key_Enter, Qt.Key_Return): 
                indices = self._listWidget.selectedIndexes()
                self.done(indices[0].row() if indices else None)
                return True
            elif event.key() == Qt.Key_Escape:
                self.done(None)
                return True
            else:
                self.filter_key_press(event)
                return True
        else:
            return super().eventFilter(receiver, event)

    def filter_key_press(self, event):
        event.accept()
        self.key_press(
                KeyEvent(
                    key=SimpleKeySequence(
                        modifiers=event.modifiers() & ~Qt.KeypadModifier,
                        keycode=event.key()),
                    text=event.text().replace('\r', '\n')))




__all__ = ['CompletionView']


def main():
    import os
    import sys
    import difflib
    import keyword
    import re
    app = QApplication(sys.argv)

    primary = QWidget()
    layout = QVBoxLayout(primary)
    button = QPushButton('complete', primary)

    layout.addWidget(button)
    
    from .widget    import TextWidget
    from ..buffers  import Cursor

    textw = TextWidget(parent=primary)
    layout.addWidget(textw)

    

    primary.show()
    primary.raise_()

    cv = CompletionView(parent=primary)

    @cv.done.connect
    def done_handler(idx):
        print('done: selected', idx)

    annot = AttributedString('keyword', italic=True)
    annot2 = AttributedString('value', italic=True)


    cv.model.completions = [(x, annot) for x in keyword.kwlist] + [(x, annot2) for x in vars(os).keys()]

    all_comps = cv.model.completions

    origin_curs = Cursor(textw.buffer)


    @textw.presenter.manipulator.executed_change.connect
    def key_press_handler(evt):
        origin_curs.move(0, 0)
        filter_text = origin_curs.text_to(textw.presenter.canonical_cursor).lower()
        print(filter_text)
        filter_exp = '.*?'.join(filter_text)


        cv.model.completions = sorted([c for c in all_comps if re.match(filter_exp, c[0].lower()) is not None], key=lambda x: len(x[0]))

    
    cv.show()
    cv.resize(cv.width() * 2, cv.height())
    @button.clicked.connect
    def click_handler():
        cv.move(primary.mapToGlobal(textw.rect().bottomLeft()))
        cv.show()

    cv.key_press.connect(textw.key_press)
    

    app.exec_()


if __name__ == '__main__':
    main()