from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui import mainwindow_rc


class StatusAwareTrayIcon(object):

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
            'disconnected': QtGui.QLabel(),
            'connecting': QtGui.QLabel(),
            'connected': QtGui.QLabel(),
        }
        con_widgets['disconnected'].setPixmap(
            QtGui.QPixmap(icons['disconnected']))
        con_widgets['connecting'].setPixmap(
            QtGui.QPixmap(icons['connecting']))
        con_widgets['connected'].setPixmap(
            QtGui.QPixmap(icons['connected'])),
        self.ConnectionWidgets = con_widgets

        con_icons = {
            'disconnected': QtGui.QIcon(icons['disconnected']),
            'connecting': QtGui.QIcon(icons['connecting']),
            'connected': QtGui.QIcon(icons['connected'])
        }
        self.Icons = con_icons

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

    def setIcon(self, name):
        icon = self.Icons.get(name)
        self.trayIcon.setIcon(icon)
        self.setWindowIcon(icon)

    def getIcon(self, icon_name):
        # XXX get from connection dict
        icons = {'disconnected': 0,
                 'connecting': 1,
                 'connected': 2}
        return icons.get(icon_name, None)

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

        #print('STATUS CHANGED! (on Qt-land)')
        #print('%s -> %s' % (status.previous, status.current))
        icon_name = self.conductor.get_icon_name()
        self.setIcon(icon_name)
        #print 'icon = ', icon_name

        # change connection pixmap widget
        self.setConnWidget(icon_name)
