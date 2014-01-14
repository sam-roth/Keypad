

from PyQt4.Qt import *

from .view import TextViewSettings, draw_attr_text, KeyEvent
from ..key import SimpleKeySequence, key, KeySequenceDict
from ..attributed_string import AttributedString
from ..signal import Signal

import platform


completion_view_stylesheet = r"""

QTreeView {{

    border-radius:          10px;
    padding-top:            10px;
    padding-bottom:         10px;
    background-color:       {settings.bgcolor};
    color:                  {settings.fgcolor};
    selection-background-color: {selbg};
    font:                   13pt "Menlo";

}}

"""


class CompletionListItemDelegate(QItemDelegate):

    def __init__(self):
        super().__init__()
        nset = self.settings = TextViewSettings()
        sset = self.selected_settings = TextViewSettings()
        sch = nset.scheme
        
        sset.bgcolor = sch.emphasize(nset.bgcolor, 1)
        sset.fgcolor = sch.emphasize(nset.fgcolor, 1)

        for s in (self.settings, self.selected_settings):
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
        from ..colors import scheme
        super().__init__()
        self.columns = 2

        self._completions = ()
        

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




class CompletionView(QWidget):

    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._listWidget = QTreeView(self)
        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self._listWidget)

        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setAttribute(Qt.WA_QuitOnClose) # TODO: remove this line

        self._listWidget.setAttribute(Qt.WA_MacShowFocusRect, False)
        self._listWidget.setHeaderHidden(True)
        
        from ..colors import scheme

        self.setStyleSheet(completion_view_stylesheet.format(
            settings=TextViewSettings(),
            selbg=scheme.emphasize(scheme.bg, 1)
        ))

        self._completion_model = CompletionListModel()
        self._listWidget.setModel(self._completion_model)
        self._listWidget.setItemDelegate(CompletionListItemDelegate())

        self.setFocusProxy(self._listWidget)
        self._listWidget.installEventFilter(self)
        
        self.key_press.connect(self.on_key_press)
        self.done.connect(self._close)

        self._completion_model.modelReset.connect(self.on_model_reset)


    @Signal
    def key_press(self, event):
        pass

    @Signal
    def done(self, comp_idx):
        pass


    def _close(self, comp_idx):
        self.close()

    def showEvent(self, evt):
        super().showEvent(evt)

    def on_key_press(self, event):
        if key.esc.matches(event.key):
            self.done(None)
        elif key.return_.matches(event.key) or \
                key.enter.matches(event.key):
            
            idxs = self._listWidget.selectedIndexes()
            idx = None
            if idxs:
                idx = idxs[0].row()

            self.done(idx)
        

    def on_model_reset(self):
        self._listWidget.resizeColumnToContents(0)

    def eventFilter(self, receiver, event):
        if event.type() == QEvent.KeyPress and receiver is self._listWidget:
            
            ignored_keys = [
                Qt.Key_Down, Qt.Key_Up,
                Qt.Key_PageUp, Qt.Key_PageDown
               # Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape
            ]

            if event.key() in ignored_keys:
                return False
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
    
    from .widget import TextWidget
    from ..cursor import Cursor

    textw = TextWidget(primary)
    layout.addWidget(textw)

    

    primary.show()
    primary.raise_()

    cv = CompletionView(primary)

    @cv.done.connect
    def done_handler(idx):
        print('done: selected', idx)

    annot = AttributedString('keyword', italic=True)
    annot2 = AttributedString('value', italic=True)


    cv._completion_model.completions = [(x, annot) for x in keyword.kwlist] + [(x, annot2) for x in vars(os).keys()]

    all_comps = cv._completion_model.completions

    origin_curs = Cursor(textw.buffer)


    @textw.manip.executed_change.connect
    def key_press_handler(evt):
        origin_curs.move(0, 0)
        filter_text = origin_curs.text_to(textw.presenter.canonical_cursor).lower()
        print(filter_text)
        filter_exp = '.*?'.join(filter_text)


        cv._completion_model.completions = sorted([c for c in all_comps if re.match(filter_exp, c[0].lower()) is not None], key=lambda x: len(x[0]))

    
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
