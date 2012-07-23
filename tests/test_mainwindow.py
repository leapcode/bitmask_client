# vim: set fileencoding=utf-8 :
from argparse import Namespace
import logging
logger = logging.getLogger(name=__name__)

import sys
import unittest

# black magic XXX ??
import sip
sip.setapi('QVariant', 2)

from PyQt4 import QtGui
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt

from eip_client import eipcmainwindow, conductor


class MainWindowTest(unittest.TestCase):
    """
    Test our mainwindow GUI
    """

    ##################################################
    # FIXME
    # To be moved to BaseEIPTestCase

    def setUp(self):
        '''Create the GUI'''
        self.app = QtGui.QApplication(sys.argv)
        opts = Namespace(config=None,
                debug=False)
        self.win = eipcmainwindow.EIPCMainWindow(opts)

    def tearDown(self):
        """
        cleanup
        """
        # we have to delete references, otherwise
        # we get nice segfaults :)
        del(self.win)
        del(self.app)

    ##################################################

    def test_system_has_systray(self):
        """
        does this system has a systray?
        not the application response to that.
        """
        self.assertEqual(
                self.win.trayIcon.isSystemTrayAvailable(),
                True)

    def test_defaults(self):
        """
        test that the defaults are those expected
        """
        self.assertEqual(self.win.windowTitle(), "EIP")
        #self.assertEqual(self.win.durationSpinBox.value(), 15)
        #logger.debug('durationSpinBox: %s' % self.win.durationSpinBox.value())

    def test_main_window_has_conductor_instance(self):
        """
        test main window instantiates conductor class
        """
        self.assertEqual(hasattr(self.win, 'conductor'), True)
        self.assertEqual(isinstance(self.win.conductor,
            conductor.EIPConductor), True)

    # Let's roll... let's test serious things
    # ... better to have a different TestCase for this?
    # plan is:
    # 1) we signal to the app that we are running from the
    #    testrunner -- so it knows, just in case :P
    # 2) we init the conductor with the default-for-testrunner
    #    options -- like getting a fake-output client script
    #    that mocks openvpn output to stdout.
    # 3) we check that the important things work as they
    #    expected for the output of the binaries.
    # XXX TODO:
    # get generic helper methods for the base testcase class.
    # mock_good_output
    # mock_bad_output
    # check_status

    def test_connected_status_good_output(self):
        """
        check we get 'connected' state after mocked \
good output from the fake openvpn process.
        """
        self.mock_good_output()
        # wait?
        self.check_state('connected')

    def test_unrecoverable_status_bad_output(self):
        """
        check we get 'unrecoverable' state after
        mocked bad output from the fake openvpn process.
        """
        self.mock_bad_output()
        self.check_state('unrecoverable')

    def test_icon_reflects_state(self):
        """
        test that the icon changes after an injection
        of a change-of-state event.
        """
        self.mock_status_change('connected')
        # icon == connectedIcon
        # examine: QSystemtrayIcon.MessageIcon ??
        self.mock_status_change('disconnected')
        # ico == disconnectedIcon
        self.mock_status_change('connecting')
        # icon == connectingIcon

    def test_status_signals_are_working(self):
        """
        test that status-change signals are being triggered
        """
        #???
        pass


    # sample tests below... to be removed

    #def test_show_message_button_does_show_message(self):
        #"""
        #test that clicking on main window button shows message
        #"""
        # FIXME
        #ok_show = self.win.showMessageButton
        #trayIcon = self.win.trayIcon
        # fake left click
        #QTest.mouseClick(ok_show, Qt.LeftButton)
        # how to assert that message has been shown?
        #import ipdb;ipdb.set_trace()


    #def test_do_fallback_if_not_systray(self):
        #"""
        #test that we do whatever we decide to do
        #when we detect no systray.
        #what happens with unity??
        #"""
        #pass

if __name__ == "__main__":
    unittest.main()
