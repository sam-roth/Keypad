
.. _signal-howto:

Signal HOWTO
************

:author: Sam Roth

.. topic:: Abstract

    This document defines signals and summarizes their interface.


Introduction
============

    "Don't call us, we'll call you."

    -- Unknown


Signals are conceptually the opposite of methods. They act like a list of
callbacks that are invoked when some event happens. For those familiar with the
Qt framework, these signals work in the same way as the construct of the same
name in Qt.

Observing a Signal
==================

.. py:currentmodule:: keypad.core.signal

You may start observing a signal by using its `~InstanceSignal.connect` method.
The argument to this method is the function that should be called upon emission
of the signal. You may stop observing a signal by using its
`~InstanceSignal.disconnect` method. Pass the same function to this method as
you did the first.

If you need a reference to the sender of the signal, set the keyword argument
``add_sender`` to ``True`` in your call to `~InstanceSignal.connect`. Doing so
will add a reference to the sender as the first argument to the signal handler.

.. warning:: 
    Never call a signal from outside of its class. Doing so will emit the signal,
    which probably wasn't what you wanted to do.
    
.. note::
    The argument passed to `~InstanceSignal.connect` is held by :py:mod:`weak
    reference <weakref>`. This means that if the observer is garbage-collected,
    the signal will disconnect from it automatically. Simply connecting a
    signal to an object **does not** keep it from being garbage collected. You
    **must** retain a strong reference to it elsewhere.

Declaring a Signal
==================

You declare a signal using the `~Signal` decorator on a method of a class.
Here's an example::

    from keypad.core import Signal

    class Spam:
    
        def __init__(self):
            self.__ham = None

        @property
        def ham(self):
            return self.__ham

        @ham.setter
        def ham(self, value):
            old_ham = self.__ham
            self.__ham = value
            self.ham_changed(old_ham, value)

        @Signal
        def ham_changed(self, old_ham, new_ham):
            '''
            This signal is emitted when the ham is replaced.

            :type old_ham: IHammable
            :type new_ham: IHammable
            '''


Currently, the method only lends its signature and docstring to the signal; it
is never called. This behavior may change in the future, so, for now, either
put a docstring or the ``pass`` statement in the method body.

Emitting Signals
================

To emit a signal, simply call it, providing the same number of parameters as
the prototype specifies.

.. warning::

    By convention, you **should not** use keyword arguments when emitting a
    signal, as this will make the names of the arguments a part of the signal's
    interface.



Exceptions During Signal Handling
=================================

By default, if an exception occurs during signal handling, it is logged and
stored in the `~InstanceSignal.errors` attribute of the signal. This is usally
the behavior you want, since propagating an exception from a signal handler
would interrupt the emission of the signal: some signal handlers would not be
called. The `~InstanceSignal.errors` list is cleared every time the signal is
emitted.


Further Reading
===============

* `Qt 4.8 Documentation: Signals & Slots <http://qt-project.org/doc/qt-4.8/signalsandslots.html>`_
