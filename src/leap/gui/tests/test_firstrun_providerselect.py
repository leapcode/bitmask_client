import sys
import unittest

import mock

from leap.testing import qunittest
#from leap.testing import pyqt

from PyQt4 import QtGui
#from PyQt4 import QtCore
#import PyQt4.QtCore  # some weirdness with mock module

from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from leap.gui import firstrun

try:
    from collections import OrderedDict
except ImportError:
    # We must be in 2.6
    from leap.util.dicts import OrderedDict


class TestPage(firstrun.providerselect.SelectProviderPage):
    pass


class SelectProviderPageLogicTestCase(qunittest.TestCase):

    # XXX can spy on signal connections

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.page = TestPage(None)
        self.page.wizard = mock.MagicMock()

        mocknetchecker = mock.Mock()
        self.page.wizard().netchecker.return_value = mocknetchecker
        self.mocknetchecker = mocknetchecker

        mockpcertchecker = mock.Mock()
        self.page.wizard().providercertchecker.return_value = mockpcertchecker
        self.mockpcertchecker = mockpcertchecker

        mockeipconfchecker = mock.Mock()
        self.page.wizard().eipconfigchecker.return_value = mockeipconfchecker
        self.mockeipconfchecker = mockeipconfchecker

    def tearDown(self):
        QtGui.qApp = None
        self.app = None
        self.page = None

    def test__do_checks(self):
        eq = self.assertEqual

        self.page.providerNameEdit.setText('test_provider1')

        checks = [x for x in self.page._do_checks()]
        eq(len(checks), 5)
        labels = [str(x) for (x, y), z in checks]
        eq(labels, ['head_sentinel', 'checking domain name',
                    'checking https connection',
                    'fetching provider info', 'end_sentinel'])
        progress = [y for (x, y), z in checks]
        eq(progress, [0, 20, 40, 80, 100])

        # normal run, ie, no exceptions

        checkfuns = [z for (x, y), z in checks]
        namecheck, httpscheck, fetchinfo = checkfuns[1:-1]

        self.assertTrue(namecheck())
        self.mocknetchecker.check_name_resolution.assert_called_with(
            'test_provider1')

        self.assertTrue(httpscheck())
        self.mockpcertchecker.is_https_working.assert_called_with(
            "https://test_provider1", verify=True)

        self.assertTrue(fetchinfo())
        self.mockeipconfchecker.fetch_definition.assert_called_with(
            domain="test_provider1")

        # XXX missing: inject failing exceptions
        # XXX TODO make it break


class SelectProviderPageUITestCase(qunittest.TestCase):

    # XXX can spy on signal connections
    __name__ = "Select Provider Page UI tests"

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app

        self.pagename = "providerselection"
        pages = OrderedDict((
            (self.pagename, TestPage),
            ('providerinfo',
             firstrun.providerinfo.ProviderInfoPage)))
        self.wizard = firstrun.wizard.FirstRunWizard(None, pages_dict=pages)
        self.page = self.wizard.page(self.wizard.get_page_index(self.pagename))

        self.page.do_checks = mock.Mock()

        # wizard would do this for us
        self.page.initializePage()

    def tearDown(self):
        QtGui.qApp = None
        self.app = None
        self.wizard = None

    def fill_provider(self):
        """
        fills provider line edit
        """
        keyp = QTest.keyPress
        pedit = self.page.providerNameEdit
        pedit.setFocus(True)
        for c in "testprovider":
            keyp(pedit, c)
        self.assertEqual(pedit.text(), "testprovider")

    def del_provider(self):
        """
        deletes entried provider in
        line edit
        """
        keyp = QTest.keyPress
        pedit = self.page.providerNameEdit
        for c in range(len("testprovider")):
            keyp(pedit, Qt.Key_Backspace)
        self.assertEqual(pedit.text(), "")

    def test_buttons_disabled_until_textentry(self):
        nextbutton = self.wizard.button(QtGui.QWizard.NextButton)
        checkbutton = self.page.providerCheckButton

        self.assertFalse(nextbutton.isEnabled())
        self.assertFalse(checkbutton.isEnabled())

        self.fill_provider()
        # checkbutton should be enabled
        self.assertTrue(checkbutton.isEnabled())
        self.assertFalse(nextbutton.isEnabled())

        self.del_provider()
        # after rm provider checkbutton disabled again
        self.assertFalse(checkbutton.isEnabled())
        self.assertFalse(nextbutton.isEnabled())

    def test_check_button_triggers_tests(self):
        checkbutton = self.page.providerCheckButton
        self.assertFalse(checkbutton.isEnabled())
        self.assertFalse(self.page.do_checks.called)

        self.fill_provider()

        self.assertTrue(checkbutton.isEnabled())
        mclick = QTest.mouseClick
        # click!
        mclick(checkbutton, Qt.LeftButton)
        self.waitFor(seconds=0.1)
        self.assertTrue(self.page.do_checks.called)

        # XXX
        # can play with different side_effects for do_checks mock...
        # so we can see what happens with errors and so on

    def test_page_completed_after_checks(self):
        nextbutton = self.wizard.button(QtGui.QWizard.NextButton)
        self.assertFalse(nextbutton.isEnabled())

        self.assertFalse(self.page.isComplete())
        self.fill_provider()
        # simulate checks done
        self.page.done = True
        self.page.on_checks_validation_ready()
        self.assertTrue(self.page.isComplete())
        # cannot test for nexbutton enabled
        # cause it's the the wizard loop
        # that would do that I think

    def test_validate_page(self):
        self.assertTrue(self.page.validatePage())

    def test_next_id(self):
        self.assertEqual(self.page.nextId(), 1)

    def test_paint_event(self):
        self.page.populateErrors = mock.Mock()
        self.page.paintEvent(None)
        self.page.populateErrors.assert_called_with()

if __name__ == "__main__":
    unittest.main()
