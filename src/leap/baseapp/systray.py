import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap import __branding as BRANDING
from leap import __version__ as VERSION

from leap.gui import mainwindow_rc

logger = logging.getLogger(__name__)


class StatusAwareTrayIconMixin(object):
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

        self.statusIconBox = QtGui.QGroupBox("EIP Connection Status")
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

        self.trayIconMenu.addAction(self.connAct)
        #self.trayIconMenu.addAction(self.minimizeAction)
        #self.trayIconMenu.addAction(self.maximizeAction)
        #self.trayIconMenu.addAction(self.restoreAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.detailsAct)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.aboutAct)
        self.trayIconMenu.addAction(self.aboutQtAct)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)

        self.trayIcon = QtGui.QSystemTrayIcon(self)
        self.setIcon('disconnected')
        self.trayIcon.setContextMenu(self.trayIconMenu)

    def bad(self):
        logger.error('this should not be called')

    def createActions(self):
        """
        creates actions to be binded to tray icon
        """
        # XXX change action name on (dis)connect
        self.connAct = QtGui.QAction("Encryption ON     turn &off", self,
                                     triggered=lambda: self.start_or_stopVPN())

        self.detailsAct = QtGui.QAction("&Details...",
                                        self,
                                        triggered=self.detailsWin)
        #self.minimizeAction = QtGui.QAction("Mi&nimize", self,
                                            #triggered=self.hide)
        #self.maximizeAction = QtGui.QAction("Ma&ximize", self,
                                            #triggered=self.showMaximized)
        #self.restoreAction = QtGui.QAction("&Restore", self,
                                           #triggered=self.showNormal)
        self.aboutAct = QtGui.QAction("&About", self,
                                      triggered=self.about)
        self.aboutQtAct = QtGui.QAction("About Q&t", self,
                                        triggered=QtGui.qApp.aboutQt)
        self.quitAction = QtGui.QAction("&Quit", self,
                                        triggered=self.cleanupAndQuit)

    def toggleEIPAct(self):
        # this is too simple by now.
        # XXX We need to get the REAL info for Encryption state.
        # (now is ON as soon as vpn launched)
        if self.eip_service_started is True:
            self.connAct.setText('Encryption ON    turn o&ff')
        else:
            self.connAct.setText('Encryption OFF   turn &on')

    def detailsWin(self):
        visible = self.isVisible()
        if visible:
            self.hide()
        else:
            self.show()

    def about(self):
        # move to widget
        flavor = BRANDING.get('short_name', None)
        content = ("LEAP client<br>"
                   "(version <b>%s</b>)<br>" % VERSION)
        if flavor:
            content = content + ('<br>Flavor: <i>%s</i><br>' % flavor)
        content = content + (
            "<br><a href='https://leap.se/'>"
            "https://leap.se</a>")
        QtGui.QMessageBox.about(self, "About", content)

    def setConnWidget(self, icon_name):
        oldlayout = self.statusIconBox.layout()

        for i in range(3):
            oldlayout.itemAt(i).widget().hide()
        new = self.states[icon_name]
        oldlayout.itemAt(new).widget().show()

    def setIcon(self, name):
        icon = self.Icons.get(name)(self)
        self.trayIcon.setIcon(icon)
        #self.setWindowIcon(icon)

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
