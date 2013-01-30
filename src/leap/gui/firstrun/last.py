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

        self.setTitle(self.tr(
            "Connecting to Encrypted Internet Proxy service..."))

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        #self.setPixmap(
            #QtGui.QWizard.WatermarkPixmap,
            #QtGui.QPixmap(':/images/watermark2.png'))

        self.label = QtGui.QLabel()
        self.label.setWordWrap(True)

        self.wizard_done = False

        # XXX REFACTOR to a Validating Page...
        self.status_line_1 = QtGui.QLabel()
        self.status_line_2 = QtGui.QLabel()
        self.status_line_3 = QtGui.QLabel()
        self.status_line_4 = QtGui.QLabel()
        self.status_line_5 = QtGui.QLabel()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)

        # make loop
        layout.addWidget(self.status_line_1)
        layout.addWidget(self.status_line_2)
        layout.addWidget(self.status_line_3)
        layout.addWidget(self.status_line_4)
        layout.addWidget(self.status_line_5)

        self.setLayout(layout)

    def isComplete(self):
        return self.wizard_done

    def set_status_line(self, line, status):
        statusline = getattr(self, 'status_line_%s' % line)
        if statusline:
            statusline.setText(status)

    def set_finished_status(self):
        self.setTitle(self.tr('You are now using an encrypted connection!'))
        finishText = self.wizard().buttonText(
            QtGui.QWizard.FinishButton)
        finishText = finishText.replace('&', '')
        self.label.setText(self.tr(
            "Click '<i>%s</i>' to end the wizard and "
            "save your settings." % finishText))
        self.wizard_done = True
        self.completeChanged.emit()

    @coroutine
    def eip_status_handler(self):
        # XXX this can be changed to use
        # signals. See progress.py
        logger.debug('logging status in last page')
        self.validation_done = False
        status_count = 1
        try:
            while True:
                status = (yield)
                status_count += 1
                # XXX add to line...
                logger.debug('status --> %s', status)
                self.set_status_line(status_count, status)
                if status == "connected":
                    self.set_finished_status()
                    self.completeChanged.emit()
                    break
                self.completeChanged.emit()
        except GeneratorExit:
            pass
        except StopIteration:
            pass

    def initializePage(self):
        super(LastPage, self).initializePage()
        wizard = self.wizard()
        wizard.button(QtGui.QWizard.FinishButton).setDisabled(True)

        handler = self.eip_status_handler()

        # get statuses done in prev page
        for st in wizard.openvpn_status:
            self.send_status(handler.send, st)

        # bind signal for events yet to come
        eip_statuschange_signal = wizard.eip_statuschange_signal
        if eip_statuschange_signal:
            eip_statuschange_signal.connect(
                lambda status: self.send_status(
                    handler.send, status))
        self.completeChanged.emit()

    def send_status(self, cb, status):
        try:
            cb(status)
        except StopIteration:
            pass
