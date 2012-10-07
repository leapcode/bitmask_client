# vim: set fileencoding=utf-8 :
#!/usr/bin/env python
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.baseapp.eip import EIPConductorAppMixin
from leap.baseapp.log import LogPaneMixin
from leap.baseapp.systray import StatusAwareTrayIconMixin
from leap.baseapp.leap_app import MainWindowMixin

logger = logging.getLogger(name=__name__)


class LeapWindow(QtGui.QMainWindow,
                 MainWindowMixin, EIPConductorAppMixin,
                 StatusAwareTrayIconMixin,
                 LogPaneMixin):
    """
    main window for the leap app.
    Initializes all of its base classes
    We keep here some signal initialization
    that gets tricky otherwise.
    """

    newLogLine = QtCore.pyqtSignal([str])
    statusChange = QtCore.pyqtSignal([object])
    mainappReady = QtCore.pyqtSignal([])
    initReady = QtCore.pyqtSignal([])

    def __init__(self, opts):
        logger.debug('init leap window')
        self.debugmode = getattr(opts, 'debug', False)
        super(LeapWindow, self).__init__()
        if self.debugmode:
            self.createLogBrowser()

        EIPConductorAppMixin.__init__(self, opts=opts)
        StatusAwareTrayIconMixin.__init__(self)
        MainWindowMixin.__init__(self)

        settings = QtCore.QSettings()
        geom = settings.value("Geometry")
        if geom:
            self.restoreGeometry(geom)
        self.wizard_done = settings.value("FirstRunWizardDone")

        self.initchecks = InitChecksThread(self.run_eip_checks)

        # bind signals
        self.initchecks.finished.connect(
            lambda: logger.debug('Initial checks finished'))
        self.trayIcon.activated.connect(self.iconActivated)
        self.newLogLine.connect(
            lambda line: self.onLoggerNewLine(line))
        self.statusChange.connect(
            lambda status: self.onStatusChange(status))
        self.timer.timeout.connect(
            lambda: self.onTimerTick())

        # do frwizard and init signals
        self.mainappReady.connect(self.do_first_run_wizard_check)
        self.initReady.connect(self.runchecks_and_eipconnect)

        # ... all ready. go!
        # calls do_first_run_wizard_check
        self.mainappReady.emit()

    def do_first_run_wizard_check(self):
        logger.debug('first run wizard check...')
        if self.wizard_done:
            self.initReady.emit()
        else:
            # need to run first-run-wizard
            logger.debug('running first run wizard')
            from leap.gui.firstrunwizard import FirstRunWizard
            wizard = FirstRunWizard(
                parent=self,
                success_cb=self.initReady.emit)
            wizard.show()

    def runchecks_and_eipconnect(self):
        self.initchecks.begin()


class InitChecksThread(QtCore.QThread):

    def __init__(self, fun, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.fun = fun

    def run(self):
        self.fun()

    def begin(self):
        self.start()
