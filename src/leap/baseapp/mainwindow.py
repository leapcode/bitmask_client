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

    # signals

    newLogLine = QtCore.pyqtSignal([str])
    mainappReady = QtCore.pyqtSignal([])
    initReady = QtCore.pyqtSignal([])
    networkError = QtCore.pyqtSignal([object])
    triggerEIPError = QtCore.pyqtSignal([object])
    start_eipconnection = QtCore.pyqtSignal([])

    # this is status change got from openvpn management
    openvpnStatusChange = QtCore.pyqtSignal([object])
    # this is global eip status
    eipStatusChange = QtCore.pyqtSignal([str])

    def __init__(self, opts):
        logger.debug('init leap window')
        self.debugmode = getattr(opts, 'debug', False)
        super(LeapWindow, self).__init__()
        if self.debugmode:
            self.createLogBrowser()

        settings = QtCore.QSettings()
        self.provider_domain = settings.value("provider_domain", None)
        self.eip_username = settings.value("eip_username", None)

        logger.debug('provider: %s', self.provider_domain)
        logger.debug('eip_username: %s', self.eip_username)

        EIPConductorAppMixin.__init__(
            self, opts=opts, provider=self.provider_domain)
        StatusAwareTrayIconMixin.__init__(self)
        NetworkCheckerAppMixin.__init__(self)
        MainWindowMixin.__init__(self)

        geom_key = "DebugGeometry" if self.debugmode else "Geometry"
        geom = settings.value(geom_key)
        if geom:
            self.restoreGeometry(geom)

        # XXX check for wizard
        self.wizard_done = settings.value("FirstRunWizardDone")

        self.initchecks = InitChecksThread(self.run_eip_checks)

        # bind signals
        self.initchecks.finished.connect(
            lambda: logger.debug('Initial checks thread finished'))
        self.trayIcon.activated.connect(self.iconActivated)
        self.newLogLine.connect(
            lambda line: self.onLoggerNewLine(line))
        self.timer.timeout.connect(
            lambda: self.onTimerTick())
        self.networkError.connect(
            lambda exc: self.onNetworkError(exc))
        self.triggerEIPError.connect(
            lambda exc: self.onEIPError(exc))

        if self.debugmode:
            self.startStopButton.clicked.connect(
                lambda: self.start_or_stopVPN())
        self.start_eipconnection.connect(
            lambda: self.start_or_stopVPN())

        # status change.
        # TODO unify
        self.openvpnStatusChange.connect(
            lambda status: self.onOpenVPNStatusChange(status))
        self.eipStatusChange.connect(
            lambda newstatus: self.onEIPConnStatusChange(newstatus))
        # can I connect 2 signals?
        self.eipStatusChange.connect(
            lambda newstatus: self.toggleEIPAct())

        # do first run wizard and init signals
        self.mainappReady.connect(self.do_first_run_wizard_check)
        self.initReady.connect(self.runchecks_and_eipconnect)

        # ... all ready. go!
        # connected to do_first_run_wizard_check
        self.mainappReady.emit()

    def do_first_run_wizard_check(self):
        """
        checks whether first run wizard needs to be run
        launches it if needed
        and emits initReady signal if not.
        """

        logger.debug('first run wizard check...')
        need_wizard = False

        # do checks (can overlap if wizard was interrupted)
        if not self.wizard_done:
            need_wizard = True
        if not self.provider_domain:
            need_wizard = True

        # launch wizard if needed
        if need_wizard:
            self.launch_first_run_wizard()
        else:  # no wizard needed
            logger.debug('running first run wizard')
            self.initReady.emit()

    def launch_first_run_wizard(self):
        """
        launches wizard and blocks
        """
        from leap.gui.firstrunwizard import FirstRunWizard
        wizard = FirstRunWizard(
            self.conductor,
            parent=self,
            eip_username=self.eip_username,
            start_eipconnection_signal=self.start_eipconnection,
            eip_statuschange_signal=self.eipStatusChange)
        wizard.show()

    def runchecks_and_eipconnect(self):
        self.initchecks.begin()


class FunThread(QtCore.QThread):

    def __init__(self, fun, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.fun = fun

    def run(self):
        if self.fun:
            self.fun()

    def begin(self):
        self.start()
