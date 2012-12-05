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


class TestPage(firstrun.providerselect.SelectProviderPage):
    pass


class SelectProviderPageTestCase(qunittest.TestCase):

    # XXX can spy on signal connections

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        QtGui.qApp = self.app
        self.page = TestPage(None)
        self.page.wizard = mock.MagicMock()
        self.page.wizard().netchecker.return_value = True

    def tearDown(self):
        QtGui.qApp = None
        self.app = None
        self.page = None

    def test__do_checks(self):
        eq = self.assertEqual
        checks = [x for x in self.page._do_checks()]
        eq(len(checks), 5)
        labels = [str(x) for (x, y), z in checks]
        eq(labels, ['head_sentinel', 'checking domain name',
                    'checking https connection',
                    'fetching provider info', 'end_sentinel'])
        progress = [y for (x, y), z in checks]
        eq(progress, [0, 20, 40, 80, 100])

        # XXX now: execute the functions
        # with proper mocks (for checkers and so on)
        # and try to cover all the exceptions
        checkfuns = [z for (x, y), z in checks]
        #import ipdb;ipdb.set_trace() 

    def test_next_button_is_disabled(self):
        pass


if __name__ == "__main__":
    unittest.main()
