"""
Last Page, used in First Run Wizard
"""
import logging

from PyQt4 import QtGui

from leap.util.coroutines import coroutine
from leap.gui.constants import APP_LOGO

logger = logging.getLogger(__name__)


class LastPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(LastPage, self).__init__(parent)

        self.setTitle("Connecting to Encrypted Internet Proxy service...")

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        #self.setPixmap(
            #QtGui.QWizard.WatermarkPixmap,
            #QtGui.QPixmap(':/images/watermark2.png'))

        self.label = QtGui.QLabel()
        self.label.setWordWrap(True)

        # XXX REFACTOR to a Validating Page...
        self.status_line_1 = QtGui.QLabel()
        self.status_line_2 = QtGui.QLabel()
        self.status_line_3 = QtGui.QLabel()
        self.status_line_4 = QtGui.QLabel()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)

        # make loop
        layout.addWidget(self.status_line_1)
        layout.addWidget(self.status_line_2)
        layout.addWidget(self.status_line_3)
        layout.addWidget(self.status_line_4)

        self.setLayout(layout)

    def set_status_line(self, line, status):
        statusline = getattr(self, 'status_line_%s' % line)
        if statusline:
            statusline.setText(status)

    def set_finished_status(self):
        self.setTitle('You are now using an encrypted connection!')
        finishText = self.wizard().buttonText(
            QtGui.QWizard.FinishButton)
        finishText = finishText.replace('&', '')
        self.label.setText(
            "Click '<i>%s</i>' to end the wizard and "
            "save your settings." % finishText)
        # XXX init network checker
        # trigger signal

    @coroutine
    def eip_status_handler(self):
        # XXX this can be changed to use
        # signals. See progress.py
        logger.debug('logging status in last page')
        self.validation_done = False
        status_count = 0
        try:
            while True:
                status = (yield)
                status_count += 1
                # XXX add to line...
                logger.debug('status --> %s', status)
                self.set_status_line(status_count, status)
                if status == "connected":
                    self.set_finished_status()
                    break
        except GeneratorExit:
            pass
        except StopIteration:
            pass

    def initializePage(self):
        wizard = self.wizard()
        if not wizard:
            return
        eip_status_handler = self.eip_status_handler()
        eip_statuschange_signal = wizard.eip_statuschange_signal
        if eip_statuschange_signal:
            eip_statuschange_signal.connect(
                lambda status: eip_status_handler.send(status))
