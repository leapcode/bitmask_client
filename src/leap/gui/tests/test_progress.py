from collections import namedtuple
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

    def __init__(self, parent=None):
        super(TestWithStepsClass, self).__init__(parent=parent)
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
        s.set_error('fooerror', 'barerror')
        self.assertEqual(s.errors, {'fooerror': 'barerror'})
        s.set_error('2', 42)
        self.assertEqual(s.errors, {'fooerror': 'barerror', '2': 42})
        fe = s.pop_first_error()
        self.assertEqual(fe, ('fooerror', 'barerror'))
        self.assertEqual(s.errors, {'2': 42})
        s.clean_errors()
        self.assertEqual(s.errors, {})

    def test_launch_chechs_slot(self):
        s = self.stepy
        s.do_checks = mock.Mock()
        s.launch_checks()
        s.do_checks.assert_called_with()

    def test_clean_wizard_errors(self):
        s = self.stepy
        s.wizard = mock.Mock()
        wizard = s.wizard.return_value
        wizard.set_validation_error.return_value = True
        s.clean_wizard_errors(pagename="foopage")
        wizard.set_validation_error.assert_called_with("foopage", None)

    def test_clear_table(self):
        s = self.stepy
        s.stepsTableWidget = mock.Mock()
        s.stepsTableWidget.clearContents.return_value = True
        s.clearTable()
        s.stepsTableWidget.clearContents.assert_called_with()

    def test_populate_steps_table(self):
        s = self.stepy
        Step = namedtuple('Step', ['name', 'done'])

        class Steps(object):
            columns = ("name", "done")
            _items = (Step('step1', False), Step('step2', False))

            def __len__(self):
                return 2

            def __iter__(self):
                for i in self._items:
                    yield i

        s.steps = Steps()

        s.stepsTableWidget = mock.Mock()
        s.stepsTableWidget.setItem.return_value = True
        s.resizeTable = mock.Mock()
        s.update = mock.Mock()
        s.populateStepsTable()
        s.update.assert_called_with()
        s.resizeTable.assert_called_with()

        # assert stepsTableWidget.setItem called ...
        # we do not want to get into the actual
        # <QTableWidgetItem object at 0x92a565c>
        call_list = s.stepsTableWidget.setItem.call_args_list
        indexes = [(y, z) for y, z, xx in [x[0] for x in call_list]]
        self.assertEqual(indexes,
                         [(0, 0), (0, 1), (1, 0), (1, 1)])

    def test_add_status_line(self):
        s = self.stepy
        s.steps = progress.ProgressStepContainer()
        s.stepsTableWidget = mock.Mock()
        s.stepsTableWidget.width.return_value = 100
        s.set_item = mock.Mock()
        s.set_item_icon = mock.Mock()
        s.add_status_line("new status")
        s.set_item_icon.assert_called_with(current=False)

    def test_set_item_icon(self):
        s = self.stepy
        s.steps = progress.ProgressStepContainer()
        s.stepsTableWidget = mock.Mock()
        s.stepsTableWidget.setCellWidget.return_value = True
        s.stepsTableWidget.width.return_value = 100
        #s.set_item = mock.Mock()
        #s.set_item_icon = mock.Mock()
        s.add_status_line("new status")
        s.add_status_line("new 2 status")
        s.add_status_line("new 3 status")
        call_list = s.stepsTableWidget.setCellWidget.call_args_list
        indexes = [(y, z) for y, z, xx in [x[0] for x in call_list]]
        self.assertEqual(
            indexes,
            [(0, 1), (-1, 1), (1, 1), (0, 1), (2, 1), (1, 1)])


class TestInlineValidationPage(progress.InlineValidationPage):
    pass


class InlineValidationPageTestCase(unittest.TestCase):

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.page = TestInlineValidationPage()

    def tearDown(self):
        QtGui.qApp = None
        self.app = None

    def test_defaults(self):
        self.assertFalse(self.page.done)
        # if setupProcessingQueue was  called
        self.assertTrue(isinstance(self.page.stepscheck_timer, QtCore.QTimer))
        self.assertTrue(isinstance(self.page.steps_queue, Queue.Queue))

    def test_validation_frame(self):
        # test frame creation
        self.page.stepsTableWidget = progress.StepsTableWidget(
            parent=self.page)
        self.page.setupValidationFrame()
        self.assertTrue(isinstance(self.page.valFrame, QtGui.QFrame))

        # test show steps calls frame.show
        self.page.valFrame = mock.Mock()
        self.page.valFrame.show.return_value = True
        self.page.showStepsFrame()
        self.page.valFrame.show.assert_called_with()


class TestValidationPage(progress.ValidationPage):
    pass


class ValidationPageTestCase(unittest.TestCase):

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.page = TestValidationPage()

    def tearDown(self):
        QtGui.qApp = None
        self.app = None

    def test_defaults(self):
        self.assertFalse(self.page.done)
        # if setupProcessingQueue was  called
        self.assertTrue(isinstance(self.page.timer, QtCore.QTimer))
        self.assertTrue(isinstance(self.page.stepscheck_timer, QtCore.QTimer))
        self.assertTrue(isinstance(self.page.steps_queue, Queue.Queue))

    def test_is_complete(self):
        self.assertFalse(self.page.isComplete())
        self.page.done = True
        self.assertTrue(self.page.isComplete())
        self.page.done = False
        self.assertFalse(self.page.isComplete())

    def test_show_hide_progress(self):
        p = self.page
        p.progress = mock.Mock()
        p.progress.show.return_code = True
        p.show_progress()
        p.progress.show.assert_called_with()
        p.progress.hide.return_code = True
        p.hide_progress()
        p.progress.hide.assert_called_with()

    def test_initialize_page(self):
        p = self.page
        p.timer = mock.Mock()
        p.timer.singleShot.return_code = True
        p.initializePage()
        p.timer.singleShot.assert_called_with(0, p.do_checks)


if __name__ == "__main__":
    unittest.main()
