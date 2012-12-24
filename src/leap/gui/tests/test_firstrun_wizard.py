import sys
import unittest

import mock

from leap.testing import qunittest
from leap.testing import pyqt

from PyQt4 import QtGui
#from PyQt4 import QtCore
import PyQt4.QtCore  # some weirdness with mock module

from PyQt4.QtTest import QTest
#from PyQt4.QtCore import Qt

from leap.gui import firstrun


class TestWizard(firstrun.wizard.FirstRunWizard):
    pass


PAGES_DICT = dict((
    ('intro', firstrun.intro.IntroPage),
    ('providerselection',
        firstrun.providerselect.SelectProviderPage),
    ('login', firstrun.login.LogInPage),
    ('providerinfo', firstrun.providerinfo.ProviderInfoPage),
    ('providersetupvalidation',
        firstrun.providersetup.ProviderSetupValidationPage),
    ('signup', firstrun.register.RegisterUserPage),
    ('signupvalidation',
        firstrun.regvalidation.RegisterUserValidationPage),
    ('lastpage', firstrun.last.LastPage)
))


mockQSettings = mock.MagicMock()
mockQSettings().setValue.return_value = True

#PyQt4.QtCore.QSettings = mockQSettings


class FirstRunWizardTestCase(qunittest.TestCase):

    # XXX can spy on signal connections

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.wizard = TestWizard(None)

    def tearDown(self):
        QtGui.qApp = None
        self.app = None
        self.wizard = None

    def test_defaults(self):
        self.assertEqual(self.wizard.pages_dict, PAGES_DICT)

    @mock.patch('PyQt4.QtCore.QSettings', mockQSettings)
    def test_accept(self):
        """
        test the main accept method
        that gets called when user has gone
        thru all the wizard and click on finish button
        """

        self.wizard.success_cb = mock.Mock()
        self.wizard.success_cb.return_value = True

        # dummy values; we inject them in the field
        # mocks (where wizard gets them) and then
        # we check that they are passed to QSettings.setValue
        field_returns = ["testuser", "1234", "testprovider", True]

        def field_side_effects(*args):
            return field_returns.pop(0)

        self.wizard.field = mock.Mock(side_effect=field_side_effects)
        self.wizard.get_random_str = mock.Mock()
        RANDOMSTR = "thisisarandomstringTM"
        self.wizard.get_random_str.return_value = RANDOMSTR

        # mocked settings (see decorator on this method)
        mqs = PyQt4.QtCore.QSettings

        # go! call accept...
        self.wizard.accept()

        # did settings().setValue get called with the proper
        # arguments?
        call = mock.call
        calls = [call("FirstRunWizardDone", True),
                 call("provider_domain", "testprovider"),
                 call("remember_user_and_pass", True),
                 call("eip_username", "testuser@testprovider"),
                 call("testprovider_seed", RANDOMSTR)]
        mqs().setValue.assert_has_calls(calls, any_order=True)

        # assert success callback is success oh boy
        self.wizard.success_cb.assert_called_with()

    def test_random_str(self):
        r = self.wizard.get_random_str(42)
        self.assertTrue(len(r) == 42)

    def test_page_index(self):
        """
        we test both the get_page_index function
        and the correct ordering of names
        """
        # remember it's implemented as an ordered dict

        pagenames = ('intro', 'providerselection', 'login', 'providerinfo',
                     'providersetupvalidation', 'signup', 'signupvalidation',
                     'lastpage')
        eq = self.assertEqual
        w = self.wizard
        for index, name in enumerate(pagenames):
            eq(w.get_page_index(name), index)

    def test_validation_errors(self):
        """
        tests getters and setters for validation errors
        """
        page = "testpage"
        eq = self.assertEqual
        w = self.wizard
        eq(w.get_validation_error(page), None)
        w.set_validation_error(page, "error")
        eq(w.get_validation_error(page), "error")
        w.clean_validation_error(page)
        eq(w.get_validation_error(page), None)

if __name__ == "__main__":
    unittest.main()
