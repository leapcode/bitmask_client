import sys
import unittest
import Queue

import mock

from leap.testing import qunittest
from leap.testing import pyqt

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from leap.gui import progress


class ProgressStepTestCase(unittest.TestCase):

    def test_step_attrs(self):
        ps = progress.ProgressStep
        step = ps('test', False, 1)
        # instance
        self.assertEqual(step.index, 1)
        self.assertEqual(step.name, "test")
        self.assertEqual(step.done, False)
        step = ps('test2', True, 2)
        self.assertEqual(step.index, 2)
        self.assertEqual(step.name, "test2")
        self.assertEqual(step.done, True)

        # class methods and attrs
        self.assertEqual(ps.columns(), ('name', 'done'))
        self.assertEqual(ps.NAME, 0)
        self.assertEqual(ps.DONE, 1)


class ProgressStepContainerTestCase(unittest.TestCase):
    def setUp(self):
        self.psc = progress.ProgressStepContainer()

    def addSteps(self, number):
        Step = progress.ProgressStep
        for n in range(number):
            self.psc.addStep(Step("%s" % n, False, n))

    def test_attrs(self):
        self.assertEqual(self.psc.columns,
                         ('name', 'done'))

    def test_add_steps(self):
        Step = progress.ProgressStep
        self.assertTrue(len(self.psc) == 0)
        self.psc.addStep(Step('one', False, 0))
        self.assertTrue(len(self.psc) == 1)
        self.psc.addStep(Step('two', False, 1))
        self.assertTrue(len(self.psc) == 2)

    def test_del_all_steps(self):
        self.assertTrue(len(self.psc) == 0)
        self.addSteps(5)
        self.assertTrue(len(self.psc) == 5)
        self.psc.removeAllSteps()
        self.assertTrue(len(self.psc) == 0)

    def test_del_step(self):
        Step = progress.ProgressStep
        self.addSteps(5)
        self.assertTrue(len(self.psc) == 5)
        self.psc.removeStep(self.psc.step(4))
        self.assertTrue(len(self.psc) == 4)
        self.psc.removeStep(self.psc.step(4))
        self.psc.removeStep(Step('none', False, 5))
        self.psc.removeStep(self.psc.step(4))

    def test_iter(self):
        self.addSteps(10)
        self.assertEqual(
            [x.index for x in self.psc],
            [x for x in range(10)])


class StepsTableWidgetTestCase(unittest.TestCase):

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.stw = progress.StepsTableWidget()

    def tearDown(self):
        QtGui.qApp = None
        self.app = None

    def test_defaults(self):
        self.assertTrue(isinstance(self.stw, QtGui.QTableWidget))
        self.assertEqual(self.stw.focusPolicy(), 0)


class TestWithStepsClass(QtGui.QWidget, progress.WithStepsMixIn):

    def __init__(self):
        self.setupStepsProcessingQueue()
        self.statuses = []
        self.current_page = "testpage"

    def onStepStatusChanged(self, *args):
        """
        blank out this gui method
        that will add status lines
        """
        self.statuses.append(args)


class WithStepsMixInTestCase(qunittest.TestCase):

    TIMER_WAIT = 2 * progress.WithStepsMixIn.STEPS_TIMER_MS / 1000.0

    # XXX can spy on signal connections

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.stepy = TestWithStepsClass()
        #self.connects = []
        #pyqt.enableSignalDebugging(
            #connectCall=lambda *args: self.connects.append(args))
        #self.assertEqual(self.connects, [])
        #self.stepy.stepscheck_timer.timeout.disconnect(
            #self.stepy.processStepsQueue)

    def tearDown(self):
        QtGui.qApp = None
        self.app = None

    def test_has_queue(self):
        s = self.stepy
        self.assertTrue(hasattr(s, 'steps_queue'))
        self.assertTrue(isinstance(s.steps_queue, Queue.Queue))
        self.assertTrue(isinstance(s.stepscheck_timer, QtCore.QTimer))

    def test_do_checks_delegation(self):
        s = self.stepy

        _do_checks = mock.Mock()
        _do_checks.return_value = (
            (("test", 0), lambda: None),
            (("test", 0), lambda: None))
        s._do_checks = _do_checks
        s.do_checks()
        self.waitFor(seconds=self.TIMER_WAIT)
        _do_checks.assert_called_with()
        self.assertEqual(len(s.statuses), 2)

        # test that a failed test interrupts the run

        s.statuses = []
        _do_checks = mock.Mock()
        _do_checks.return_value = (
            (("test", 0), lambda: None),
            (("test", 0), lambda: False),
            (("test", 0), lambda: None))
        s._do_checks = _do_checks
        s.do_checks()
        self.waitFor(seconds=self.TIMER_WAIT)
        _do_checks.assert_called_with()
        self.assertEqual(len(s.statuses), 2)

    def test_process_queue(self):
        s = self.stepy
        q = s.steps_queue
        s.set_failed_icon = mock.MagicMock()
        with self.assertRaises(AssertionError):
            q.put('foo')
            self.waitFor(seconds=self.TIMER_WAIT)
            s.set_failed_icon.assert_called_with()
        q.put("failed")
        self.waitFor(seconds=self.TIMER_WAIT)
        s.set_failed_icon.assert_called_with()

    def test_on_checks_validation_ready_called(self):
        s = self.stepy
        s.on_checks_validation_ready = mock.MagicMock()

        _do_checks = mock.Mock()
        _do_checks.return_value = (
            (("test", 0), lambda: None),)
        s._do_checks = _do_checks
        s.do_checks()

        self.waitFor(seconds=self.TIMER_WAIT)
        s.on_checks_validation_ready.assert_called_with()

    def test_fail(self):
        s = self.stepy

        s.wizard = mock.Mock()
        wizard = s.wizard.return_value
        wizard.set_validation_error.return_value = True
        s.completeChanged = mock.Mock()
        s.completeChanged.emit.return_value = True

        self.assertFalse(s.fail(err="foo"))
        self.waitFor(seconds=self.TIMER_WAIT)
        wizard.set_validation_error.assert_called_with('testpage', 'foo')
        s.completeChanged.emit.assert_called_with()

        # with no args
        s.wizard = mock.Mock()
        wizard = s.wizard.return_value
        wizard.set_validation_error.return_value = True
        s.completeChanged = mock.Mock()
        s.completeChanged.emit.return_value = True

        self.assertFalse(s.fail())
        self.waitFor(seconds=self.TIMER_WAIT)
        with self.assertRaises(AssertionError):
            wizard.set_validation_error.assert_called_with()
        s.completeChanged.emit.assert_called_with()

    def test_done(self):
        s = self.stepy
        s.done = False

        s.completeChanged = mock.Mock()
        s.completeChanged.emit.return_value = True

        self.assertFalse(s.is_done())
        s.set_done()
        self.assertTrue(s.is_done())
        s.completeChanged.emit.assert_called_with()

        s.completeChanged = mock.Mock()
        s.completeChanged.emit.return_value = True
        s.set_undone()
        self.assertFalse(s.is_done())

    def test_back_and_next(self):
        s = self.stepy
        s.wizard = mock.Mock()
        wizard = s.wizard.return_value
        wizard.back.return_value = True
        wizard.next.return_value = True
        s.go_back()
        wizard.back.assert_called_with()
        s.go_next()
        wizard.next.assert_called_with()

    def test_on_step_statuschanged_slot(self):
        s = self.stepy
        s.onStepStatusChanged = progress.WithStepsMixIn.onStepStatusChanged
        s.add_status_line = mock.Mock()
        s.set_checked_icon = mock.Mock()
        s.progress = mock.Mock()
        s.progress.setValue.return_value = True
        s.progress.update.return_value = True

        s.onStepStatusChanged(s, "end_sentinel")
        s.set_checked_icon.assert_called_with()

        s.onStepStatusChanged(s, "foo")
        s.add_status_line.assert_called_with("foo")

        s.onStepStatusChanged(s, "bar", 42)
        s.progress.setValue.assert_called_with(42)
        s.progress.update.assert_called_with()

    def test_steps_and_errors(self):
        s = self.stepy
        s.setupSteps()
        self.assertTrue(isinstance(s.steps, progress.ProgressStepContainer))
        self.assertEqual(s.errors, {})



class InlineValidationPageTestCase(unittest.TestCase):
    pass


class ValidationPage(unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
