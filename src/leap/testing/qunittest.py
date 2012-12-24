# -*- coding: utf-8 -*-

# **qunittest** is an standard Python `unittest` enhancement for PyQt4,
# allowing
# you to test asynchronous code using standard synchronous testing facility.
#
# The source for `qunittest` is available on [GitHub][gh], and released under
# the MIT license.
#
# Slightly modified by The Leap Project.

### Prerequisites

# Import unittest2 or unittest
try:
    import unittest2 as unittest
except ImportError:
    import unittest

# ... and some standard Python libraries
import sys
import functools
import contextlib
import re

# ... and several PyQt classes
from PyQt4.QtCore import QTimer
from PyQt4.QtTest import QTest
from PyQt4 import QtGui

### The code


# Override standard main method, by invoking it inside PyQt event loop

def main(*args, **kwargs):
    qapplication = QtGui.QApplication(sys.argv)

    QTimer.singleShot(0, unittest.main(*args, **kwargs))
    qapplication.exec_()

"""
This main substitute does not integrate with unittest.

Note about mixing the event loop and unittests:

Unittest will fail if we keep more than one reference to a QApplication.
(pyqt expects to be  and only one).
So, for the things that need a QApplication to exist, do something like:

    self.app = QApplication()
    QtGui.qApp = self.app

in the class setUp, and::

    QtGui.qApp = None
    self.app = None

in the class tearDown.

For some explanation about this, see
  http://stuvel.eu/blog/127/multiple-instances-of-qapplication-in-one-process
and
  http://www.riverbankcomputing.com/pipermail/pyqt/2010-September/027705.html
"""


# Helper returning the name of a given signal

def _signal_name(signal):
    s = repr(signal)
    name_re = "signal (\w+) of (\w+)"
    match = re.search(name_re, s, re.I)
    if not match:
        return "??"
    return "%s#%s" % (match.group(2), match.group(1))


class _SignalConnector(object):
    """ Encapsulates signal assertion testing """
    def __init__(self, test, signal, callable_):
        self.test = test
        self.callable_ = callable_
        self.called_with = None
        self.emited = False
        self.signal = signal
        self._asserted = False

        signal.connect(self.on_signal_emited)

    # Store given parameters and mark signal as `emited`
    def on_signal_emited(self, *args, **kwargs):
        self.called_with = (args, kwargs)
        self.emited = True

    def assertEmission(self):
        # Assert once wheter signal was emited or not
        was_asserted = self._asserted
        self._asserted = True

        if not was_asserted:
            if not self.emited:
                self.test.fail(
                    "signal %s not emited" % (_signal_name(self.signal)))

            # Call given callable is necessary
            if self.callable_:
                args, kwargs = self.called_with
                self.callable_(*args, **kwargs)

    def __enter__(self):
        # Assert emission when context is entered
        self.assertEmission()
        return self.called_with

    def __exit__(self, *_):
        return False

### Unit Testing

# `qunittest` does not force much abould how test should look - it just adds
# several helpers for asynchronous code testing.
#
# Common test case may look like this:
#
#     import qunittest
#     from calculator import Calculator
#
#     class TestCalculator(qunittest.TestCase):
#         def setUp(self):
#             self.calc = Calculator()
#
#         def test_should_add_two_numbers_synchronously(self):
#             # given
#             a, b = 2, 3
#
#             # when
#             r = self.calc.add(a, b)
#
#             # then
#             self.assertEqual(5, r)
#
#         def test_should_calculate_factorial_in_background(self):
#             # given
#
#             # when
#             self.calc.factorial(20)
#
#             # then
#             self.assertEmited(self.calc.done) with (args, kwargs):
#                 self.assertEqual([2432902008176640000], args)
#
#     if __name__ == "__main__":
#         main()
#
# Test can be run by typing:
#
#     python test_calculator.py
#
# Automatic test discovery is not supported now, because testing PyQt needs
# an instance of `QApplication` and its `exec_` method is blocking.
#


### TestCase class

class TestCase(unittest.TestCase):
    """
    Extends standard `unittest.TestCase` with several PyQt4 testing features
    useful for asynchronous testing.
    """
    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)

        self._clearSignalConnectors()
        self._succeeded = False
        self.addCleanup(self._clearSignalConnectors)
        self.tearDown = self._decorateTearDown(self.tearDown)

    ### Protected methods

    def _clearSignalConnectors(self):
        self._connectedSignals = []

    def _decorateTearDown(self, tearDown):
        @functools.wraps(tearDown)
        def decorator():
            self._ensureEmitedSignals()
            return tearDown()
        return decorator

    def _ensureEmitedSignals(self):
        """
        Checks if signals were acually emited. Raises AssertionError if no.
        """
        # TODO: add information about line
        for signal in self._connectedSignals:
            signal.assertEmission()

    ### Assertions

    def assertEmited(self, signal, callable_=None, timeout=1):
        """
        Asserts if given `signal` was emited. Waits 1 second by default,
        before asserts signal emission.

        If `callable_` is given, it should be a function which takes two
        arguments: `args` and `kwargs`. It will be called after blocking
        operation or when assertion about signal emission is made and
        signal was emited.

        When timeout is not `False`, method call is blocking, and ends
        after `timeout` seconds. After that time, it validates wether
        signal was emited.

        When timeout is `False`, method is non blocking, and test should wait
        for signals afterwards. Otherwise, at the end of the test, all
        signal emissions are checked if appeared.

        Function returns context, which yields to list of parameters given
        to signal. It can be useful for testing given parameters. Following
        code:

            with self.assertEmited(widget.signal) as (args, kwargs):
                self.assertEqual(1, len(args))
                self.assertEqual("Hello World!", args[0])

        will wait 1 second and test for correct parameters, is signal was
        emtied.

        Note that code:

            with self.assertEmited(widget.signal, timeout=False) as (a, k):
                # Will not be invoked

        will always fail since signal cannot be emited in the time of its
        connection - code inside the context will not be invoked at all.
        """

        connector = _SignalConnector(self, signal, callable_)
        self._connectedSignals.append(connector)
        if timeout:
            self.waitFor(timeout)
            connector.assertEmission()

        return connector

    ### Helper methods

    @contextlib.contextmanager
    def invokeAfter(self, seconds, callable_=None):
        """
        Waits given amount of time and executes the context.

        If `callable_` is given, executes it, instead of context.
        """
        self.waitFor(seconds)
        if callable_:
            callable_()
        else:
            yield

    def waitFor(self, seconds):
        """
        Waits given amount of time.

            self.widget.loadImage(url)
            self.waitFor(seconds=10)
        """
        QTest.qWait(seconds * 1000)

    def succeed(self, bool_=True):
        """ Marks test as suceeded for next `failAfter()` invocation. """
        self._succeeded = self._succeeded or bool_

    def failAfter(self, seconds, message=None):
        """
        Waits given amount of time, and fails the test if `succeed(bool)`
        is not called - in most common case, `succeed(bool)` should be called
        asynchronously (in signal handler):

            self.widget.signal.connect(lambda: self.succeed())
            self.failAfter(1, "signal not emited?")

        After invocation, test is no longer consider as succeeded.
        """
        self.waitFor(seconds)
        if not self._succeeded:
            self.fail(message)

        self._succeeded = False

### Credits
#
# * **Who is responsible:** [Dawid Fatyga][df]
# * **Source:** [GitHub][gh]
# * **Doc. generator:** [rocco][ro]
#
# [gh]: https://www.github.com/dejw/qunittest
# [df]: https://github.com/dejw
# [ro]: http://rtomayko.github.com/rocco/
#
