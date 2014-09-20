'''
Find/Replace UI for Qt.

This UI is not necessary for using find and replace: You may use the :find and
:substitute commands instead.
'''
import re
from PyQt4 import Qt as qt
from keypad import api
from . import qt_util

class FindWidget(qt.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(qt.Qt.WA_MacSmallSize)
        layout = qt.QHBoxLayout(self)

        self._close_button = qt.QToolButton()
        self._close_button.setIcon(self.style().standardIcon(qt.QStyle.SP_TitleBarCloseButton))

        self._edit = qt.QLineEdit()
        self._edit.setFixedWidth(300)
        self._next = qt.QPushButton('Find Next')
        self._next.setDefault(True)
        self._prev = qt.QPushButton('Find Prev')
        self._err = qt.QLabel()
        self._replace_button = qt.QPushButton('Replace...')

        layout.addWidget(self._close_button)
        layout.addWidget(self._edit)
        layout.addWidget(self._prev)
        layout.addWidget(self._next)
        layout.addWidget(self._err)
        layout.addStretch()
        layout.addWidget(self._replace_button)

        self._close_button.clicked.connect(self.hide)
        self._edit.textChanged.connect(self._on_text_change)
        self._next.clicked.connect(self._find_next)
        self._edit.editingFinished.connect(self._on_editing_finished)
        self._edit.returnPressed.connect(self._find_next)
        self._prev.clicked.connect(self._find_prev)
        self._replace_button.clicked.connect(self._replace)

        self._dirty = True

        self._edit_invalid_stylesheet = '''
            background-color: #FAA;
        '''

        close_button_stylesheet = '''
            QToolButton {
                border: none;
            }
        '''
        self._close_button.setStyleSheet(close_button_stylesheet)
        self._edit.installEventFilter(self)

        self.setFocusProxy(self._edit)

        self.setProperty('find_widget_panel', True)
        stylesheet = '''
        QWidget[find_widget_panel=true] {
            border-top: 1px solid palette(dark);
        }
        '''
        self.setStyleSheet(stylesheet)
        

    def paintEvent(self, event):
        # provide support for stylesheets
        opt = qt.QStyleOption()
        opt.init(self)
        painter = qt.QPainter(self)
        with qt_util.ending(painter):
            self.style().drawPrimitive(qt.QStyle.PE_Widget, opt, painter, self)

    def eventFilter(self, obj, event):
        if obj is self._edit:
            if event.type() == qt.QEvent.KeyPress:
                if event.key() == qt.Qt.Key_Return and event.modifiers() & qt.Qt.ShiftModifier:
                    self._find_prev()
                    return True
                elif event.key() == qt.Qt.Key_Escape:
                    # FIXME: figure out why this doesn't get delivered
                    # api.interactive.run('findclear')

                    self.hide()
                    return True
            return False
        else:
            super().eventFilter(obj, event)

    def _find_all(self, timeout=300):
        try:
            api.interactive.run('findall_timeout', self._edit.text(), timeout)
        except re.error as exc:
            self._edit.setStyleSheet(self._edit_invalid_stylesheet)
            self._err.setText(str(exc))
        else:
            self._edit.setStyleSheet('')
            self._err.setText('')


    def _on_text_change(self):
        self._find_all()
        self._dirty = True

    def _on_editing_finished(self):
        if self._dirty:
            self._find_all(timeout=5000)
            self._dirty = False

    def _find_next(self):
        try:
            api.interactive.run('find', self._edit.text())
        except api.errors.UserError:
            api.interactive.run('line', 0)
            self._err.setText('No more matches. Continuing at top.')
            try:
                api.interactive.run('find', self._edit.text())
            except api.errors.UserError as exc:
                self._err.setText(str(exc))
        else:
            self._err.setText('')


    def _find_prev(self):
        try:
            api.interactive.run('findprev', self._edit.text())
        except api.errors.UserError:
            self._err.setText('No more matches.')
        else:
            self._err.setText('')


    def _replace(self):
        r, ok = qt.QInputDialog.getText(self, 'Replacement String',
                                        'Enter regular expression replacement string.')

        if ok:
            api.interactive.run('raw_substitute', self._edit.text(), r)

