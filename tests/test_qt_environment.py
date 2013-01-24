import sys
import unittest

import sip
#sip.setapi('QVariant', 2)

from PyQt4 import QtGui


class TestWin(QtGui.QMainWindow):
    """
    a _really_ minimal test window,
    with only one tray icon
    """
    def __init__(self):
        super(TestWin, self).__init__()
        self.trayIcon = QtGui.QSystemTrayIcon(self)


class QtEnvironTest(unittest.TestCase):
    """
    Test we're running a proper qt environment
    """

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        self.win = TestWin()

    def tearDown(self):
        del(self.win)
        del(self.app)

    def test_system_has_systray(self):
        """
        does system have systray available?
        """
        self.assertEqual(
            self.win.trayIcon.isSystemTrayAvailable(),
            True)


if __name__ == "__main__":
    unittest.main()
