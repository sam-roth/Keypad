
from PyQt4.Qt import *
from collections import namedtuple
import contextlib


from ..core.key import SimpleKeySequence

import abc

class KeyEvent(namedtuple('KeyEvent', 'key text')):
    
    def __new__(cls, *args, **kw):
        self = super().__new__(cls, *args, **kw)
        self._is_intercepted = False
        return self
    
    @property
    def is_intercepted(self): return self._is_intercepted

    def intercept(self):
        self._is_intercepted = True



def marshal_key_event(event):
    return KeyEvent(
        key=SimpleKeySequence(
            modifiers=event.modifiers() & ~Qt.KeypadModifier,
            keycode=event.key()
        ),
        text=event.text().replace('\r', '\n')
    )





@contextlib.contextmanager
def ending(painter):
    try:
        yield painter
    finally:
        painter.end()


@contextlib.contextmanager
def restoring(painter):
    try:
        painter.save()
        yield painter
    finally:
        painter.restore()

def qcolor_marshaller(attrname):
    def fget(self):
        # QColor::name() actually returns an HTML-style hex string like
        # #AABBCC.
        color = getattr(self, attrname)
        if color.alpha() != 255:
            return 'rgba({}, {}, {}, {})'.format(
                color.red(),
                color.green(),
                color.blue(),
                color.alpha()
            )
        else:
            return color.name()

    def fset(self, value):
        setattr(self, attrname, QColor(value))
    
    return property(fget, fset)



class ABCWithQtMeta(pyqtWrapperType, abc.ABCMeta):
    pass
    #def __new__(cls, *args, **kw):
    #    return super().__new__(cls, *args, **kw)

