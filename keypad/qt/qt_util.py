
from PyQt4.Qt import *
from collections import namedtuple
import contextlib


from ..core.key import SimpleKeySequence
from ..core.color import Color
from ..abstract.textview import KeyEvent
from ..core.responder import Responder
from .. import api

import abc
import math

def set_tab_order(parent, widgets):
    for first, second in zip(widgets, widgets[1:]):
        parent.setTabOrder(first, second)

def qsizef_ceil(size):
    '''
    Converts a QSizeF to a QSize, rounding up.
    :type size: PyQr4.Qt.QSizeF
    '''
    
    return QSize(
        math.ceil(size.width()),
        math.ceil(size.height())
    ) 

class CloseEvent(object):
    def __init__(self):
        self.is_intercepted = False

    def intercept(self):
        self.is_intercepted = True



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


class AutoresponderMixin:


    @property
    def next_responders(self):

        pw = self.parentWidget()
        while pw is not None and not isinstance(pw, Responder):
            pw = pw.parentWidget()

        if pw is not None and isinstance(pw, Responder):
            return [pw] + super().next_responders
        else:
            return super().next_responders

class Autoresponder(AutoresponderMixin, Responder):
    pass


