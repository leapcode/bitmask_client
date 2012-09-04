# vim: set fileencoding=utf-8 :
#!/usr/bin/env python
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.baseapp.eip import EIPConductorApp
from leap.baseapp.log import LogPane
from leap.baseapp.systray import StatusAwareTrayIcon
from leap.baseapp.leap_app import MainWindow

logger = logging.getLogger(name=__name__)


class LeapWindow(QtGui.QMainWindow,
                 MainWindow, EIPConductorApp,
                 StatusAwareTrayIcon,
                 LogPane):
    """
    main window for the leap app.
    Initializes all of its base classes
    We keep here some signal initialization
    that gets tricky otherwise.
    """

    newLogLine = QtCore.pyqtSignal([str])
    statusChange = QtCore.pyqtSignal([object])

    def __init__(self, opts):
        logger.debug('init leap window')
        self.debugmode = getattr(opts, 'debug', False)

        super(LeapWindow, self).__init__()
        if self.debugmode:
            self.createLogBrowser()
        EIPConductorApp.__init__(self, opts=opts)
        StatusAwareTrayIcon.__init__(self)
        MainWindow.__init__(self)

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
