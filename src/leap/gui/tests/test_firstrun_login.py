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


class TestPage(firstrun.login.LogInPage):
    pass


class LogInPageLogicTestCase(qunittest.TestCase):

    # XXX can spy on signal connections
    __name__ = "register user page logic tests"

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.page = TestPage(None)
        self.page.wizard = mock.MagicMock()

    def tearDown(self):
        QtGui.qApp = None
        self.app = None
        self.page = None

    def test__do_checks(self):
        eq = self.assertEqual

        self.page.userNameLineEdit.setText('testuser@domain')
        self.page.userPasswordLineEdit.setText('testpassword')

        # fake register process
        with mock.patch('leap.base.auth.LeapSRPRegister') as mockAuth:
            mockSignup = mock.MagicMock()

            reqMockup = mock.Mock()
            # XXX should inject bad json to get error
            reqMockup.content = '{"errors": null}'
            mockSignup.register_user.return_value = (True, reqMockup)
            mockAuth.return_value = mockSignup
            checks = [x for x in self.page._do_checks()]

            eq(len(checks), 4)
            labels = [str(x) for (x, y), z in checks]
            eq(labels, ['head_sentinel',
                        'Resolving domain name',
                        'Validating credentials',
                        'end_sentinel'])
            progress = [y for (x, y), z in checks]
            eq(progress, [0, 20, 60, 100])

            # normal run, ie, no exceptions

            checkfuns = [z for (x, y), z in checks]
            checkusername, resolvedomain, valcreds = checkfuns[:-1]

            self.assertTrue(checkusername())
            #self.mocknetchecker.check_name_resolution.assert_called_with(
                #'test_provider1')

            self.assertTrue(resolvedomain())
            #self.mockpcertchecker.is_https_working.assert_called_with(
                #"https://test_provider1", verify=True)

            self.assertTrue(valcreds())

        # XXX missing: inject failing exceptions
        # XXX TODO make it break


class RegisterUserPageUITestCase(qunittest.TestCase):

    # XXX can spy on signal connections
    __name__ = "Register User Page UI tests"

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app

        self.pagename = "signup"
        pages = OrderedDict((
            (self.pagename, TestPage),
            ('providersetupvalidation',
             firstrun.connect.ConnectionPage)))
        self.wizard = firstrun.wizard.FirstRunWizard(None, pages_dict=pages)
        self.page = self.wizard.page(self.wizard.get_page_index(self.pagename))

        self.page.do_checks = mock.Mock()

        # wizard would do this for us
        self.page.initializePage()

    def tearDown(self):
        QtGui.qApp = None
        self.app = None
        self.wizard = None

    # XXX refactor out
    def fill_field(self, field, text):
        """
        fills a field (line edit) that is passed along
        :param field: the qLineEdit
        :param text: the text to be filled
        :type field: QLineEdit widget
        :type text: str
        """
        keyp = QTest.keyPress
        field.setFocus(True)
        for c in text:
            keyp(field, c)
        self.assertEqual(field.text(), text)

    def del_field(self, field):
        """
        deletes entried text in
        field line edit
        :param field: the QLineEdit
        :type field: QLineEdit widget
        """
        keyp = QTest.keyPress
        for c in range(len(field.text())):
            keyp(field, Qt.Key_Backspace)
        self.assertEqual(field.text(), "")

    def test_buttons_disabled_until_textentry(self):
        # it's a commit button this time
        nextbutton = self.wizard.button(QtGui.QWizard.CommitButton)

        self.assertFalse(nextbutton.isEnabled())

        f_username = self.page.userNameLineEdit
        f_password = self.page.userPasswordLineEdit

        self.fill_field(f_username, "testuser")
        self.fill_field(f_password, "testpassword")

        # commit should be enabled
        # XXX Need a workaround here
        # because the isComplete is not being evaluated...
        # (no event loop running??)
        #import ipdb;ipdb.set_trace()
        #self.assertTrue(nextbutton.isEnabled())
        self.assertTrue(self.page.isComplete())

        self.del_field(f_username)
        self.del_field(f_password)

        # after rm fields commit button
        # should be disabled again
        #self.assertFalse(nextbutton.isEnabled())
        self.assertFalse(self.page.isComplete())

    def test_validate_page(self):
        self.assertFalse(self.page.validatePage())
        # XXX TODO MOAR CASES...
        # add errors, False
        # change done, False
        # not done, do_checks called
        # click confirm, True
        # done and do_confirm, True

    def test_next_id(self):
        self.assertEqual(self.page.nextId(), 1)

    def test_paint_event(self):
        self.page.populateErrors = mock.Mock()
        self.page.paintEvent(None)
        self.page.populateErrors.assert_called_with()

    def test_validation_ready(self):
        f_username = self.page.userNameLineEdit
        f_password = self.page.userPasswordLineEdit

        self.fill_field(f_username, "testuser")
        self.fill_field(f_password, "testpassword")

        self.page.done = True
        self.page.on_checks_validation_ready()
        self.assertFalse(f_username.isEnabled())
        self.assertFalse(f_password.isEnabled())

        self.assertEqual(self.page.validationMsg.text(),
                         "Credentials validated.")
        self.assertEqual(self.page.do_confirm_next, True)

    def test_regex(self):
        # XXX enter invalid username with key presses
        # check text is not updated
        pass


if __name__ == "__main__":
    unittest.main()
