import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

vpnlogger = logging.getLogger('leap.openvpn')


class LogPaneMixin(object):
    """
    a simple log pane
    that writes new lines as they come
    """

    def createLogBrowser(self):
        """
        creates Browser widget for displaying logs
        (in debug mode only).
        """
        self.loggerBox = QtGui.QGroupBox()
        logging_layout = QtGui.QVBoxLayout()
        self.logbrowser = QtGui.QTextBrowser()

        startStopButton = QtGui.QPushButton(self.tr("&Connect"))
        self.startStopButton = startStopButton

        logging_layout.addWidget(self.logbrowser)
        logging_layout.addWidget(self.startStopButton)
        self.loggerBox.setLayout(logging_layout)

        # status box

        self.statusBox = QtGui.QGroupBox()
        grid = QtGui.QGridLayout()

        self.updateTS = QtGui.QLabel('')
        self.status_label = QtGui.QLabel(self.tr('Disconnected'))
        self.ip_label = QtGui.QLabel('')
        self.remote_label = QtGui.QLabel('')

        tun_read_label = QtGui.QLabel("tun read")
        self.tun_read_bytes = QtGui.QLabel("0")
        tun_write_label = QtGui.QLabel("tun write")
        self.tun_write_bytes = QtGui.QLabel("0")

        grid.addWidget(self.updateTS, 0, 0)
        grid.addWidget(self.status_label, 0, 1)
        grid.addWidget(self.ip_label, 1, 0)
        grid.addWidget(self.remote_label, 1, 1)
        grid.addWidget(tun_read_label, 2, 0)
        grid.addWidget(self.tun_read_bytes, 2, 1)
        grid.addWidget(tun_write_label, 3, 0)
        grid.addWidget(self.tun_write_bytes, 3, 1)

        self.statusBox.setLayout(grid)

    @QtCore.pyqtSlot(str)
    def onLoggerNewLine(self, line):
        """
        simple slot: writes new line to logger Pane.
        """
        msg = line[:-1]
        if self.debugmode:
            self.logbrowser.append(msg)
        vpnlogger.info(msg)
