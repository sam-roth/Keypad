
from PyQt4.Qt import *
from collections import namedtuple
import contextlib


KeyEvent = namedtuple('KeyEvent', 'key text')

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
        return getattr(self, attrname).name()

    def fset(self, value):
        setattr(self, attrname, QColor(value))
    
    return property(fget, fset)

