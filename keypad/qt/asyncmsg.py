

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
        self._text_box = qt.QLineEdit(self)

        self._close_button = qt.QToolButton(self)
        self._close_button.setIcon(self.style().standardIcon(qt.QStyle.SP_TitleBarCloseButton))
        self._close_button.setStyleSheet('border: none')
        self._close_button.setFocusPolicy(qt.Qt.NoFocus)
        self._close_button.clicked.connect(self._on_close)

        self._layout.addWidget(self._close_button)
        self._layout.addWidget(self._title)
        self._layout.addStretch()
        self._layout.addWidget(self._text_box)

        self._text_box.hide()
        self._text_box.textEdited.connect(self._on_text_change)

        self._edit_invalid_stylesheet = '''
            background-color: #FAA;
        '''


        lbl = qt.QLabel('({})'.format(_get_keyboard_hint()), self)
        lbl.setStyleSheet('font-size: 10pt; font-style: italic;')
        self._layout.addWidget(lbl)


        self._widgets = []
        self.hide()

    def _on_is_valid_changed(self):
        is_valid = self._msg.is_valid
        if is_valid:
            self._text_box.setStyleSheet('')
        else:
            self._text_box.setStyleSheet(self._edit_invalid_stylesheet)

        for w in self._widgets:
            w.setEnabled(is_valid)


    def _on_text_change(self):
        self._msg.emit_text_changed(self._text_box.text())

    def _on_shortcut(self):
        if self._widgets:
            self._widgets[0].setFocus()

    def _get_result(self, choice):
        if self._msg.text_box:
            return choice, self._text_box.text()
        else:
            return choice

    def _on_close(self):
        self._msg.done(self._get_result(None))
        self._show_next()

    def _on_click(self):
        b = self.sender()
        self._msg.done(self._get_result(b.text()))
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

        if self._msg is not None:
            self._msg.is_valid_changed.disconnect(self._on_is_valid_changed)

        msg = self._q.popleft()
        assert isinstance(msg, MessageBar)
        msg.is_valid_changed.connect(self._on_is_valid_changed)
        self._msg = msg
        for widget in self._widgets:
            widget.deleteLater()

        self._widgets.clear()

        self._title.setText(msg.title)
        self._text_box.setVisible(msg.text_box is not None)
        self._text_box.setText(msg.text_box or '')

        for choice in msg.choices:
            b = qt.QPushButton(self)
            b.setText(choice)
            self._layout.addWidget(b)
            self._widgets.append(b)
            b.clicked.connect(self._on_click)

        self._on_is_valid_changed()

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


    def validator(sender, text):
        sender.is_valid = len(text) > 5

    def callback(r):
        print(r)
        app.quit()
        
    mbv.enqueue(MessageBar(title='Baz',
                           choices=['Done'],
                           text_box='', 
                           is_valid=False)
                .add_callback(lambda r: print(r))
                .add_text_changed_callback(validator,
                                           add_sender=True))

    mbv.enqueue(MessageBar(title='Foo', 
                           choices=['Bar', 'Baz'])
                .add_callback(lambda r: print(r)))

    mbv.enqueue(MessageBar(title='Bar',
                           choices=['Baz', 'Quux'])
                .add_callback(lambda r: print(r)))

    mbv.enqueue(MessageBar(title='Baz',
                           choices=['Done'],
                           text_box='')
                .add_callback(callback))
    app.exec()




