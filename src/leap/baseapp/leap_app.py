from PyQt4 import QtGui

from leap.gui import mainwindow_rc


class MainWindow(object):

    def __init__(self, *args, **kwargs):
        # XXX set initial visibility
        # debug = no visible

        widget = QtGui.QWidget()
        self.setCentralWidget(widget)

        self.createWindowHeader()

        # add widgets to layout
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.headerBox)
        mainLayout.addWidget(self.statusIconBox)
        if self.debugmode:
            mainLayout.addWidget(self.statusBox)
            mainLayout.addWidget(self.loggerBox)
        widget.setLayout(mainLayout)

        self.setWindowTitle("LEAP Client")
        self.resize(400, 300)
        self.set_statusbarMessage('ready')

    def createWindowHeader(self):
        """
        description lines for main window
        """
        self.headerBox = QtGui.QGroupBox()
        self.headerLabel = QtGui.QLabel("<font size=40><b>E</b>ncryption \
<b>I</b>nternet <b>P</b>roxy</font>")
        self.headerLabelSub = QtGui.QLabel("<i>trust your \
technolust</i>")

        pixmap = QtGui.QPixmap(':/images/leapfrog.jpg')
        frog_lbl = QtGui.QLabel()
        frog_lbl.setPixmap(pixmap)

        headerLayout = QtGui.QHBoxLayout()
        headerLayout.addWidget(frog_lbl)
        headerLayout.addWidget(self.headerLabel)
        headerLayout.addWidget(self.headerLabelSub)
        headerLayout.addStretch()
        self.headerBox.setLayout(headerLayout)

    def set_statusbarMessage(self, msg):
        self.statusBar().showMessage(msg)

    def closeEvent(self, event):
        """
        redefines close event (persistent window behaviour)
        """
        if self.trayIcon.isVisible() and not self.debugmode:
            QtGui.QMessageBox.information(
                self, "Systray",
                "The program will keep running "
                "in the system tray. To "
                "terminate the program, choose "
                "<b>Quit</b> in the "
                "context menu of the system tray entry.")
            self.hide()
            event.ignore()
        if self.debugmode:
            self.cleanupAndQuit()

    def cleanupAndQuit(self):
        """
        cleans state before shutting down app.
        """
        # TODO:make sure to shutdown all child process / threads
        # in conductor
        # XXX send signal instead?
        self.conductor.cleanup()
        QtGui.qApp.quit()
