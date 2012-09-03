# vim: set fileencoding=utf-8 :
#!/usr/bin/env python
import logging
logging.basicConfig()
logger = logging.getLogger(name=__name__)
logger.setLevel(logging.DEBUG)

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.baseapp.eip import EIPConductorApp
from leap.baseapp.log import LogPane
from leap.baseapp.systray import StatusAwareTrayIcon
from leap.baseapp.leap_app import MainWindow

from leap.gui import mainwindow_rc


class LeapWindow(QtGui.QMainWindow,
                 MainWindow, EIPConductorApp,
                 StatusAwareTrayIcon,
                 LogPane):

    # move to log
    newLogLine = QtCore.pyqtSignal([str])

    # move to icons
    statusChange = QtCore.pyqtSignal([object])

    def __init__(self, opts):
        logger.debug('init leap window')
        super(LeapWindow, self).__init__()

        self.debugmode = getattr(opts, 'debug', False)
        self.eip_service_started = False

        # create timer ##############################
        # move to Icons init??
        self.timer = QtCore.QTimer()
        #############################################

        if self.debugmode:
            self.createLogBrowser()
        EIPConductorApp.__init__(self, opts=opts)

        # LeapWindow init
        self.createWindowHeader()

        # StatusAwareTrayIcon init ###################
        self.createIconGroupBox()
        self.createActions()
        self.createTrayIcon()
        ##############################################

        # move to MainWindow init ####################
        widget = QtGui.QWidget()
        self.setCentralWidget(widget)

        # add widgets to layout
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.headerBox)
        mainLayout.addWidget(self.statusIconBox)
        if self.debugmode:
            mainLayout.addWidget(self.statusBox)
            mainLayout.addWidget(self.loggerBox)
        widget.setLayout(mainLayout)
        ###############################################

        # move to icons?
        self.trayIcon.show()
        self.setWindowTitle("LEAP Client")
        self.resize(400, 300)
        self.set_statusbarMessage('ready')

        # bind signals
        # XXX move to parent classes init??
        self.trayIcon.activated.connect(self.iconActivated)
        self.newLogLine.connect(lambda line: self.onLoggerNewLine(line))
        self.statusChange.connect(lambda status: self.onStatusChange(status))
        self.timer.timeout.connect(lambda: self.onTimerTick())

        # move to eipconductor init?
        if self.debugmode:
            self.startStopButton.clicked.connect(
                lambda: self.start_or_stopVPN())
