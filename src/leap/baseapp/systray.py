from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui import mainwindow_rc


class StatusAwareTrayIcon(object):
    """
    a mix of several functions needed
    to create a systray and make it
    get updated from conductor status
    polling.
    """
    states = {
        "disconnected": 0,
        "connecting": 1,
        "connected": 2}

    iconpath = {
        "disconnected": ':/images/conn_error.png',
        "connecting": ':/images/conn_connecting.png',
        "connected": ':/images/conn_connected.png'}

    Icons = {
        'disconnected': lambda self: QtGui.QIcon(
            self.iconpath['disconnected']),
        'connecting': lambda self: QtGui.QIcon(
            self.iconpath['connecting']),
        'connected': lambda self: QtGui.QIcon(
            self.iconpath['connected'])
    }

    def __init__(self, *args, **kwargs):
        self.createIconGroupBox()
        self.createActions()
        self.createTrayIcon()
        self.trayIcon.show()

        # not sure if this really belongs here, but...
        self.timer = QtCore.QTimer()

    def createIconGroupBox(self):
        """
        dummy icongroupbox
        (to be removed from here -- reference only)
        """
        con_widgets = {
            'disconnected': QtGui.QLabel(),
            'connecting': QtGui.QLabel(),
            'connected': QtGui.QLabel(),
        }
        con_widgets['disconnected'].setPixmap(
            QtGui.QPixmap(
                self.iconpath['disconnected']))
        con_widgets['connecting'].setPixmap(
            QtGui.QPixmap(
                self.iconpath['connecting']))
        con_widgets['connected'].setPixmap(
            QtGui.QPixmap(
                self.iconpath['connected'])),
        self.ConnectionWidgets = con_widgets

        self.statusIconBox = QtGui.QGroupBox("Connection Status")
        statusIconLayout = QtGui.QHBoxLayout()
        statusIconLayout.addWidget(self.ConnectionWidgets['disconnected'])
        statusIconLayout.addWidget(self.ConnectionWidgets['connecting'])
        statusIconLayout.addWidget(self.ConnectionWidgets['connected'])
        statusIconLayout.itemAt(1).widget().hide()
        statusIconLayout.itemAt(2).widget().hide()
        self.statusIconBox.setLayout(statusIconLayout)

    def createTrayIcon(self):
        """
        creates the tray icon
        """
        self.trayIconMenu = QtGui.QMenu(self)

        self.trayIconMenu.addAction(self.connectVPNAction)
        self.trayIconMenu.addAction(self.dis_connectAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.minimizeAction)
        self.trayIconMenu.addAction(self.maximizeAction)
        self.trayIconMenu.addAction(self.restoreAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)

        self.trayIcon = QtGui.QSystemTrayIcon(self)
        self.setIcon('disconnected')
        self.trayIcon.setContextMenu(self.trayIconMenu)

    def createActions(self):
        """
        creates actions to be binded to tray icon
        """
        self.connectVPNAction = QtGui.QAction("Connect to &VPN", self,
                                              triggered=self.hide)
        # XXX change action name on (dis)connect
        self.dis_connectAction = QtGui.QAction(
            "&(Dis)connect", self,
            triggered=lambda: self.start_or_stopVPN())
        self.minimizeAction = QtGui.QAction("Mi&nimize", self,
                                            triggered=self.hide)
        self.maximizeAction = QtGui.QAction("Ma&ximize", self,
                                            triggered=self.showMaximized)
        self.restoreAction = QtGui.QAction("&Restore", self,
                                           triggered=self.showNormal)
        self.quitAction = QtGui.QAction("&Quit", self,
                                        triggered=self.cleanupAndQuit)

    def setConnWidget(self, icon_name):
        oldlayout = self.statusIconBox.layout()

        for i in range(3):
            oldlayout.itemAt(i).widget().hide()
        new = self.states[icon_name]
        oldlayout.itemAt(new).widget().show()

    def setIcon(self, name):
        icon = self.Icons.get(name)(self)
        self.trayIcon.setIcon(icon)
        self.setWindowIcon(icon)

    def getIcon(self, icon_name):
        return self.states.get(icon_name, None)

    def setIconToolTip(self):
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
        if reason in (QtGui.QSystemTrayIcon.Trigger,
                      QtGui.QSystemTrayIcon.DoubleClick):
            self.trayIconMenu.show()

    @QtCore.pyqtSlot()
    def onTimerTick(self):
        self.statusUpdate()

    @QtCore.pyqtSlot(object)
    def onStatusChange(self, status):
        """
        slot for status changes. triggers new signals for
        updating icon, status bar, etc.
        """
        icon_name = self.conductor.get_icon_name()
        self.setIcon(icon_name)
        # change connection pixmap widget
        self.setConnWidget(icon_name)
