# vim: set fileencoding=utf-8 :
#!/usr/bin/env python
import logging
import time
logger = logging.getLogger(name=__name__)

from PyQt4.QtGui import (QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                         QSystemTrayIcon, QGroupBox, QLabel, QPixmap,
                         QHBoxLayout, QIcon,
                         QPushButton, QGridLayout, QAction, QMenu,
                         QTextBrowser, qApp)
from PyQt4.QtCore import (pyqtSlot, pyqtSignal, QTimer)

from leap.baseapp.dialogs import ErrorDialog
from leap.eip.conductor import EIPConductor, EIPNoCommandError
from leap.gui import mainwindow_rc


class LeapWindow(QMainWindow):
    #XXX tbd: refactor into model / view / controller
    #and put in its own modules...

    newLogLine = pyqtSignal([str])
    statusChange = pyqtSignal([object])

    def __init__(self, opts):
        super(LeapWindow, self).__init__()
        self.debugmode = getattr(opts, 'debug', False)

        self.vpn_service_started = False

        self.createWindowHeader()
        self.createIconGroupBox()

        self.createActions()
        self.createTrayIcon()
        if self.debugmode:
            self.createLogBrowser()

        # create timer
        self.timer = QTimer()

        # bind signals

        self.trayIcon.activated.connect(self.iconActivated)
        self.newLogLine.connect(self.onLoggerNewLine)
        self.statusChange.connect(self.onStatusChange)
        self.timer.timeout.connect(self.onTimerTick)

        widget = QWidget()
        self.setCentralWidget(widget)

        # add widgets to layout
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.headerBox)
        mainLayout.addWidget(self.statusIconBox)
        if self.debugmode:
            mainLayout.addWidget(self.statusBox)
            mainLayout.addWidget(self.loggerBox)
        widget.setLayout(mainLayout)

        self.trayIcon.show()
        config_file = getattr(opts, 'config_file', None)

        #
        # conductor is in charge of all
        # vpn-related configuration / monitoring.
        # we pass a tuple of signals that will be
        # triggered when status changes.
        #

        self.conductor = EIPConductor(
            watcher_cb=self.newLogLine.emit,
            config_file=config_file,
            status_signals=(self.statusChange.emit, ),
            debug=self.debugmode)

        print('debugmode:%s' % self.debugmode)

        if self.conductor.missing_pkexec is True:
            dialog = ErrorDialog()
            dialog.warningMessage(
                'We could not find <b>pkexec</b> in your '
                'system.<br/> Do you want to try '
                '<b>setuid workaround</b>? '
                '(<i>DOES NOTHING YET</i>)',
                'error')

        self.setWindowTitle("LEAP Client")
        self.resize(400, 300)

        self.set_statusbarMessage('ready')

        if self.conductor.autostart:
            self.start_or_stopVPN()

    def closeEvent(self, event):
        """
        redefines close event (persistent window behaviour)
        """
        if self.trayIcon.isVisible() and not self.debugmode:
            QMessageBox.information(self, "Systray",
                                    "The program will keep running "
                                    "in the system tray. To "
                                    "terminate the program, choose "
                                    "<b>Quit</b> in the "
                                    "context menu of the system tray entry.")
            self.hide()
            event.ignore()
        if self.debugmode:
            self.cleanupAndQuit()

    def setIcon(self, name):
        icon = self.Icons.get(name)
        self.trayIcon.setIcon(icon)
        self.setWindowIcon(icon)

    def setToolTip(self):
        """
        get readable status and place it on systray tooltip
        """
        status = self.conductor.status.get_readable_status()
        self.trayIcon.setToolTip(status)

    def iconActivated(self, reason):
        """
        handles left click, left double click
        showing the trayicon menu
        """
        #XXX there's a bug here!
        #menu shows on (0,0) corner first time,
        #until double clicked at least once.
        if reason in (QSystemTrayIcon.Trigger,
                      QSystemTrayIcon.DoubleClick):
            self.trayIconMenu.show()

    def createWindowHeader(self):
        """
        description lines for main window
        """
        #XXX good candidate to refactor out! :)
        self.headerBox = QGroupBox()
        self.headerLabel = QLabel("<font size=40><b>E</b>ncryption \
<b>I</b>nternet <b>P</b>roxy</font>")
        self.headerLabelSub = QLabel("<i>trust your \
technolust</i>")

        pixmap = QPixmap(':/images/leapfrog.jpg')
        frog_lbl = QLabel()
        frog_lbl.setPixmap(pixmap)

        headerLayout = QHBoxLayout()
        headerLayout.addWidget(frog_lbl)
        headerLayout.addWidget(self.headerLabel)
        headerLayout.addWidget(self.headerLabelSub)
        headerLayout.addStretch()
        self.headerBox.setLayout(headerLayout)

    def getIcon(self, icon_name):
        # XXX get from connection dict
        icons = {'disconnected': 0,
                 'connecting': 1,
                 'connected': 2}
        return icons.get(icon_name, None)

    def createIconGroupBox(self):
        """
        dummy icongroupbox
        (to be removed from here -- reference only)
        """
        icons = {
            'disconnected': ':/images/conn_error.png',
            'connecting': ':/images/conn_connecting.png',
            'connected': ':/images/conn_connected.png'
        }
        con_widgets = {
            'disconnected': QLabel(),
            'connecting': QLabel(),
            'connected': QLabel(),
        }
        con_widgets['disconnected'].setPixmap(
            QPixmap(icons['disconnected']))
        con_widgets['connecting'].setPixmap(
            QPixmap(icons['connecting']))
        con_widgets['connected'].setPixmap(
            QPixmap(icons['connected'])),
        self.ConnectionWidgets = con_widgets

        con_icons = {
            'disconnected': QIcon(icons['disconnected']),
            'connecting': QIcon(icons['connecting']),
            'connected': QIcon(icons['connected'])
        }
        self.Icons = con_icons

        self.statusIconBox = QGroupBox("Connection Status")
        statusIconLayout = QHBoxLayout()
        statusIconLayout.addWidget(self.ConnectionWidgets['disconnected'])
        statusIconLayout.addWidget(self.ConnectionWidgets['connecting'])
        statusIconLayout.addWidget(self.ConnectionWidgets['connected'])
        statusIconLayout.itemAt(1).widget().hide()
        statusIconLayout.itemAt(2).widget().hide()
        self.statusIconBox.setLayout(statusIconLayout)

    def createActions(self):
        """
        creates actions to be binded to tray icon
        """
        self.connectVPNAction = QAction("Connect to &VPN", self,
                                        triggered=self.hide)
        # XXX change action name on (dis)connect
        self.dis_connectAction = QAction("&(Dis)connect", self,
                                         triggered=self.start_or_stopVPN)
        self.minimizeAction = QAction("Mi&nimize", self,
                                      triggered=self.hide)
        self.maximizeAction = QAction("Ma&ximize", self,
                                      triggered=self.showMaximized)
        self.restoreAction = QAction("&Restore", self,
                                     triggered=self.showNormal)
        self.quitAction = QAction("&Quit", self,
                                  triggered=self.cleanupAndQuit)

    def createTrayIcon(self):
        """
        creates the tray icon
        """
        self.trayIconMenu = QMenu(self)

        self.trayIconMenu.addAction(self.connectVPNAction)
        self.trayIconMenu.addAction(self.dis_connectAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.minimizeAction)
        self.trayIconMenu.addAction(self.maximizeAction)
        self.trayIconMenu.addAction(self.restoreAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)

        self.trayIcon = QSystemTrayIcon(self)
        self.setIcon('disconnected')
        self.trayIcon.setContextMenu(self.trayIconMenu)

    def createLogBrowser(self):
        """
        creates Browser widget for displaying logs
        (in debug mode only).
        """
        self.loggerBox = QGroupBox()
        logging_layout = QVBoxLayout()
        self.logbrowser = QTextBrowser()

        startStopButton = QPushButton("&Connect")
        startStopButton.clicked.connect(self.start_or_stopVPN)
        self.startStopButton = startStopButton

        logging_layout.addWidget(self.logbrowser)
        logging_layout.addWidget(self.startStopButton)
        self.loggerBox.setLayout(logging_layout)

        # status box

        self.statusBox = QGroupBox()
        grid = QGridLayout()

        self.updateTS = QLabel('')
        self.status_label = QLabel('Disconnected')
        self.ip_label = QLabel('')
        self.remote_label = QLabel('')

        tun_read_label = QLabel("tun read")
        self.tun_read_bytes = QLabel("0")
        tun_write_label = QLabel("tun write")
        self.tun_write_bytes = QLabel("0")

        grid.addWidget(self.updateTS, 0, 0)
        grid.addWidget(self.status_label, 0, 1)
        grid.addWidget(self.ip_label, 1, 0)
        grid.addWidget(self.remote_label, 1, 1)
        grid.addWidget(tun_read_label, 2, 0)
        grid.addWidget(self.tun_read_bytes, 2, 1)
        grid.addWidget(tun_write_label, 3, 0)
        grid.addWidget(self.tun_write_bytes, 3, 1)

        self.statusBox.setLayout(grid)

    @pyqtSlot(str)
    def onLoggerNewLine(self, line):
        """
        simple slot: writes new line to logger Pane.
        """
        if self.debugmode:
            self.logbrowser.append(line[:-1])

    def set_statusbarMessage(self, msg):
        self.statusBar().showMessage(msg)

    @pyqtSlot(object)
    def onStatusChange(self, status):
        """
        slot for status changes. triggers new signals for
        updating icon, status bar, etc.
        """

        print('STATUS CHANGED! (on Qt-land)')
        print('%s -> %s' % (status.previous, status.current))
        icon_name = self.conductor.get_icon_name()
        self.setIcon(icon_name)
        print 'icon = ', icon_name

        # change connection pixmap widget
        self.setConnWidget(icon_name)

    def setConnWidget(self, icon_name):
        #print 'changing icon to %s' % icon_name
        oldlayout = self.statusIconBox.layout()

        # XXX reuse with icons
        # XXX move states to StateWidget
        states = {"disconnected": 0,
                  "connecting": 1,
                  "connected": 2}

        for i in range(3):
            oldlayout.itemAt(i).widget().hide()
        new = states[icon_name]
        oldlayout.itemAt(new).widget().show()

    @pyqtSlot()
    def start_or_stopVPN(self):
        """
        stub for running child process with vpn
        """
        if self.vpn_service_started is False:
            try:
                self.conductor.connect()
            except EIPNoCommandError:
                dialog = ErrorDialog()
                dialog.warningMessage(
                    'No suitable openvpn command found. '
                    '<br/>(Might be a permissions problem)',
                    'error')
            if self.debugmode:
                self.startStopButton.setText('&Disconnect')
            self.vpn_service_started = True

            # XXX what is optimum polling interval?
            # too little is overkill, too much
            # will miss transition states..

            self.timer.start(250.0)
            return
        if self.vpn_service_started is True:
            self.conductor.disconnect()
            # FIXME this should trigger also
            # statuschange event. why isn't working??
            if self.debugmode:
                self.startStopButton.setText('&Connect')
            self.vpn_service_started = False
            self.timer.stop()
            return

    @pyqtSlot()
    def onTimerTick(self):
        self.statusUpdate()

    @pyqtSlot()
    def statusUpdate(self):
        """
        called on timer tick
        polls status and updates ui with real time
        info about transferred bytes / connection state.
        """
        # XXX it's too expensive to poll
        # continously. move to signal events instead.

        if not self.vpn_service_started:
            return

        # XXX remove all access to manager layer
        # from here.
        if self.conductor.manager.with_errors:
            #XXX how to wait on pkexec???
            #something better that this workaround, plz!!
            time.sleep(10)
            print('errors. disconnect.')
            self.start_or_stopVPN()  # is stop

        state = self.conductor.poll_connection_state()
        if not state:
            return

        ts, con_status, ok, ip, remote = state
        self.set_statusbarMessage(con_status)
        self.setToolTip()

        ts = time.strftime("%a %b %d %X", ts)
        if self.debugmode:
            self.updateTS.setText(ts)
            self.status_label.setText(con_status)
            self.ip_label.setText(ip)
            self.remote_label.setText(remote)

        # status i/o

        status = self.conductor.manager.get_status_io()
        if status and self.debugmode:
            #XXX move this to systray menu indicators
            ts, (tun_read, tun_write, tcp_read, tcp_write, auth_read) = status
            ts = time.strftime("%a %b %d %X", ts)
            self.updateTS.setText(ts)
            self.tun_read_bytes.setText(tun_read)
            self.tun_write_bytes.setText(tun_write)

    def cleanupAndQuit(self):
        """
        cleans state before shutting down app.
        """
        # TODO:make sure to shutdown all child process / threads
        # in conductor
        self.conductor.cleanup()
        qApp.quit()
