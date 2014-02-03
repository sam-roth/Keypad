
from PyQt4.Qt import *
from collections import namedtuple
import contextlib


from ..core.key import SimpleKeySequence
from ..core.color import Color

import abc



class CloseEvent(object):
    def __init__(self):
        self.is_intercepted = False

    def intercept(self):
        self.is_intercepted = True

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




def to_q_key_sequence(key_seq):
    return QKeySequence(key_seq.keycode | key_seq.modifiers)


def to_q_color(color):
    if isinstance(color, QColor):
        return color
    r,g,b,a = Color.from_hex(color)
    return QColor.fromRgb(r,g,b,a)

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

        return Color.from_rgb(color.red(),
                              color.green(),
                              color.blue(),
                              color.alpha())

    def fset(self, value):
        setattr(self, attrname, to_q_color(value))
    
    return property(fget, fset)



class ABCWithQtMeta(pyqtWrapperType, abc.ABCMeta):
    pass
    #def __new__(cls, *args, **kw):
    #    return super().__new__(cls, *args, **kw)

