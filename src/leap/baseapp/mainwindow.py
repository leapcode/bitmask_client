# vim: set fileencoding=utf-8 :
#!/usr/bin/env python
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.baseapp.eip import EIPConductorAppMixin
from leap.baseapp.log import LogPaneMixin
from leap.baseapp.systray import StatusAwareTrayIconMixin
from leap.baseapp.network import NetworkCheckerAppMixin
from leap.baseapp.leap_app import MainWindowMixin

logger = logging.getLogger(name=__name__)


class LeapWindow(QtGui.QMainWindow,
                 MainWindowMixin, EIPConductorAppMixin,
                 StatusAwareTrayIconMixin,
                 NetworkCheckerAppMixin,
                 LogPaneMixin):
    """
    main window for the leap app.
    Initializes all of its base classes
    We keep here some signal initialization
    that gets tricky otherwise.
    """

    newLogLine = QtCore.pyqtSignal([str])
    statusChange = QtCore.pyqtSignal([object])
    networkError = QtCore.pyqtSignal([object])

    def __init__(self, opts):
        logger.debug('init leap window')
        self.debugmode = getattr(opts, 'debug', False)

        super(LeapWindow, self).__init__()
        if self.debugmode:
            self.createLogBrowser()
        EIPConductorAppMixin.__init__(self, opts=opts)
        StatusAwareTrayIconMixin.__init__(self)
        NetworkCheckerAppMixin.__init__(self)
        MainWindowMixin.__init__(self)

        # bind signals
        # XXX move to parent classes init??
        self.trayIcon.activated.connect(self.iconActivated)
        self.newLogLine.connect(
            lambda line: self.onLoggerNewLine(line))
        self.statusChange.connect(
            lambda status: self.onStatusChange(status))
        self.timer.timeout.connect(
            lambda: self.onTimerTick())

        # ... all ready. go!

        # could send "ready" signal instead
        # eipapp should catch that
        if self.conductor.autostart:
            self.start_or_stopVPN()

    #TODO: Put all Dialogs in one place
    @QtCore.pyqtSlot()
    def raise_Network_Error(self, exc):
        message = exc.message

        # XXX
        # check headless = False before
        # launching dialog.
        # (so Qt tests can assert stuff)
        
        dialog = ErrorDialog()
        dialog.warningMessage(message, 'error')
