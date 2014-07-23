

from PyQt4 import Qt as qt

from ..abstract.asyncmsg import MessageBar
import collections
import platform

def _get_keyboard_hint():
    if platform.system() == 'Darwin':
        return '\N{PLACE OF INTEREST SIGN}B'
    else:
        return 'Ctrl+B'


class MessageBarView(qt.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(qt.Qt.WA_MacSmallSize)
        self._shortcut = qt.QShortcut(qt.QKeySequence('Ctrl+B'), self)
        self._shortcut.activated.connect(self._on_shortcut)

        self._q = collections.deque()
        self._layout = qt.QHBoxLayout(self)
        self._msg = None
        self._title = qt.QLabel(self)

        self._close_button = qt.QToolButton(self)
        self._close_button.setIcon(self.style().standardIcon(qt.QStyle.SP_TitleBarCloseButton))
        self._close_button.setStyleSheet('border: none')
        self._close_button.setFocusPolicy(qt.Qt.NoFocus)
        self._close_button.clicked.connect(self._on_close)

        self._layout.addWidget(self._close_button)
        self._layout.addWidget(self._title)
        self._layout.addStretch()
        lbl = qt.QLabel('({})'.format(_get_keyboard_hint()), self)
        lbl.setStyleSheet('font-size: 10pt; font-style: italic;')
        self._layout.addWidget(lbl)


        self._widgets = []
        self.hide()

    def _on_shortcut(self):
        if self._widgets:
            self._widgets[0].setFocus()

    def _on_close(self):
        self._msg.done(None)
        self._show_next()

    def _on_click(self):
        b = self.sender()
        self._msg.done(b.text())
        self._show_next()

    def _show_next(self):
        pw = self.parentWidget()
        if pw is not None:
            pw.setFocus()
        if not self._q:
            self._msg = None
            for w in self._widgets:
                w.deleteLater()
            self._title.setText('')
            self._widgets.clear()
            self.hide()

            if pw is not None:
                pw.setFocus()

            return

        msg = self._q.popleft()
        assert isinstance(msg, MessageBar)
        self._msg = msg
        for widget in self._widgets:
            widget.deleteLater()

        self._widgets.clear()

        self._title.setText(msg.title)

        for choice in msg.choices:
            b = qt.QPushButton(self)
            b.setText(choice)
            self._layout.addWidget(b)
            self._widgets.append(b)
            b.clicked.connect(self._on_click)

        self.show()


    def enqueue(self, msg):
        assert isinstance(msg, MessageBar)
        self._q.append(msg)
        if self._msg is None:
            self._show_next()


if __name__ == '__main__':
    app = qt.QApplication([])

    mbv = MessageBarView()
    mbv.show()
    mbv.raise_()
    mbv.enqueue(MessageBar(title='Foo', 
                           choices=['Bar', 'Baz'])
                .add_callback(lambda r: print(r)))
    mbv.enqueue(MessageBar(title='Bar',
                           choices=['Baz', 'Quux'])
                .add_callback(lambda r: app.quit()))
    app.exec()




