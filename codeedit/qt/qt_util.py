
from PyQt4.Qt import *
from collections import namedtuple
import contextlib



import abc

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

