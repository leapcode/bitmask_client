import logging

import sip
sip.setapi('QVariant', 2)

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui import mainwindow_rc

logger = logging.getLogger(name=__name__)


APP_LOGO = ':/images/leap-color-small.png'


class MainWindowMixin(object):
    """
    create the main window
    for leap app
    """

    def __init__(self, *args, **kwargs):
        # XXX set initial visibility
        # debug = no visible

        widget = QtGui.QWidget()
        self.setCentralWidget(widget)

        mainLayout = QtGui.QVBoxLayout()
        # add widgets to layout
        #self.createWindowHeader()
        #mainLayout.addWidget(self.headerBox)

        # created in systray
        mainLayout.addWidget(self.statusIconBox)
        if self.debugmode:
            mainLayout.addWidget(self.statusBox)
            mainLayout.addWidget(self.loggerBox)
        widget.setLayout(mainLayout)

        self.createMainActions()
        self.createMainMenus()

        self.setWindowTitle("LEAP Client")
        self.set_app_icon()
        self.set_statusbarMessage('ready')

    def createMainActions(self):
        #self.openAct = QtGui.QAction("&Open...", self, shortcut="Ctrl+O",
                #triggered=self.open)

        self.firstRunWizardAct = QtGui.QAction(
            "&First run wizard...", self,
            triggered=self.launch_first_run_wizard)
        self.aboutAct = QtGui.QAction("&About", self, triggered=self.about)

        #self.aboutQtAct = QtGui.QAction("About &Qt", self,
                #triggered=QtGui.qApp.aboutQt)

    def createMainMenus(self):
        self.connMenu = QtGui.QMenu("&Connections", self)
        #self.viewMenu.addSeparator()
        self.connMenu.addAction(self.quitAction)

        self.settingsMenu = QtGui.QMenu("&Settings", self)
        self.settingsMenu.addAction(self.firstRunWizardAct)

        self.helpMenu = QtGui.QMenu("&Help", self)
        self.helpMenu.addAction(self.aboutAct)
        #self.helpMenu.addAction(self.aboutQtAct)

        self.menuBar().addMenu(self.connMenu)
        self.menuBar().addMenu(self.settingsMenu)
        self.menuBar().addMenu(self.helpMenu)

    def launch_first_run_wizard(self):
        settings = QtCore.QSettings()
        settings.setValue('FirstRunWizardDone', False)
        logger.debug('should run first run wizard again...')

        from leap.gui.firstrunwizard import FirstRunWizard
        wizard = FirstRunWizard(
            parent=self,
            success_cb=self.initReady.emit)
        wizard.show()

    def set_app_icon(self):
        icon = QtGui.QIcon(APP_LOGO)
        self.setWindowIcon(icon)

    #def createWindowHeader(self):
        #"""
        #description lines for main window
        #"""
        #self.headerBox = QtGui.QGroupBox()
        #self.headerLabel = QtGui.QLabel(
            #"<font size=40>LEAP Encryption Access Project</font>")
        #self.headerLabelSub = QtGui.QLabel(
            #"<br><i>your internet encryption toolkit</i>")
#
        #pixmap = QtGui.QPixmap(APP_LOGO)
        #leap_lbl = QtGui.QLabel()
        #leap_lbl.setPixmap(pixmap)
#
        #headerLayout = QtGui.QHBoxLayout()
        #headerLayout.addWidget(leap_lbl)
        #headerLayout.addWidget(self.headerLabel)
        #headerLayout.addWidget(self.headerLabelSub)
        #headerLayout.addStretch()
        #self.headerBox.setLayout(headerLayout)

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
            return
        self.cleanupAndQuit()

    def cleanupAndQuit(self):
        """
        cleans state before shutting down app.
        """
        # save geometry for restoring
        settings = QtCore.QSettings()
        geom_key = "DebugGeometry" if self.debugmode else "Geometry"
        settings.setValue(geom_key, self.saveGeometry())

        # TODO:make sure to shutdown all child process / threads
        # in conductor
        # XXX send signal instead?
        logger.info('Shutting down')
        self.conductor.cleanup()
        logger.info('Exiting. Bye.')
        QtGui.qApp.quit()
