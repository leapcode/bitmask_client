"""
Connecting Page, used in First Run Wizard
"""
# XXX FIXME
# DEPRECATED. All functionality moved to regvalidation
# This file should be removed after checking that one is ok.
# XXX

import logging

from PyQt4 import QtGui

logger = logging.getLogger(__name__)

from leap.base import auth

from leap.gui.constants import APP_LOGO
from leap.gui.styles import ErrorLabelStyleSheet


class ConnectingPage(QtGui.QWizardPage):

    # XXX change to a ValidationPage

    def __init__(self, parent=None):
        super(ConnectingPage, self).__init__(parent)

        self.setTitle("Connecting")
        self.setSubTitle('Connecting to provider.')

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        self.status = QtGui.QLabel("")
        self.status.setWordWrap(True)
        self.progress = QtGui.QProgressBar()
        self.progress.setMaximum(100)
        self.progress.hide()

        # for pre-checks
        self.status_line_1 = QtGui.QLabel()
        self.status_line_2 = QtGui.QLabel()
        self.status_line_3 = QtGui.QLabel()
        self.status_line_4 = QtGui.QLabel()

        # for connecting signals...
        self.status_line_5 = QtGui.QLabel()

        layout = QtGui.QGridLayout()
        layout.addWidget(self.status, 0, 1)
        layout.addWidget(self.progress, 5, 1)
        layout.addWidget(self.status_line_1, 8, 1)
        layout.addWidget(self.status_line_2, 9, 1)
        layout.addWidget(self.status_line_3, 10, 1)
        layout.addWidget(self.status_line_4, 11, 1)

        # XXX to be used?
        #self.validation_status = QtGui.QLabel("")
        #self.validation_status.setStyleSheet(
            #ErrorLabelStyleSheet)
        #self.validation_msg = QtGui.QLabel("")

        self.setLayout(layout)

        self.goto_login_again = False

    def set_status(self, status):
        self.status.setText(status)
        self.status.setWordWrap(True)

    def set_status_line(self, line, status):
        line = getattr(self, 'status_line_%s' % line)
        if line:
            line.setText(status)

    def set_validation_status(self, status):
        # Do not remember if we're using
        # status lines > 3 now...
        # if we are, move below
        self.status_line_3.setStyleSheet(
            ErrorLabelStyleSheet)
        self.status_line_3.setText(status)

    def set_validation_message(self, message):
        self.status_line_4.setText(message)
        self.status_line_4.setWordWrap(True)

    def get_donemsg(self, msg):
        return "%s ... done" % msg

    def run_eip_checks_for_provider_and_connect(self, domain):
        wizard = self.wizard()
        conductor = wizard.conductor
        start_eip_signal = getattr(
            wizard,
            'start_eipconnection_signal', None)

        if conductor:
            conductor.set_provider_domain(domain)
            conductor.run_checks()
            self.conductor = conductor
            errors = self.eip_error_check()
            if not errors and start_eip_signal:
                start_eip_signal.emit()

        else:
            logger.warning(
                "No conductor found. This means that "
                "probably the wizard has been launched "
                "in an stand-alone way")

    def eip_error_check(self):
        """
        a version of the main app error checker,
        but integrated within the connecting page of the wizard.
        consumes the conductor error queue.
        pops errors, and add those to the wizard page
        """
        logger.debug('eip error check from connecting page')
        errq = self.conductor.error_queue
        # XXX missing!

    def fetch_and_validate(self):
        # XXX MOVE TO validate function in register-validation
        import time
        domain = self.field('provider_domain')
        wizard = self.wizard()
        #pconfig = wizard.providerconfig
        eipconfigchecker = wizard.eipconfigchecker()
        pCertChecker = wizard.providercertchecker(
            domain=domain)

        # username and password are in different fields
        # if they were stored in log_in or sign_up pages.
        from_login = self.wizard().from_login
        unamek_base = 'userName'
        passwk_base = 'userPassword'
        unamek = 'login_%s' % unamek_base if from_login else unamek_base
        passwk = 'login_%s' % passwk_base if from_login else passwk_base

        username = self.field(unamek)
        password = self.field(passwk)
        credentials = username, password

        self.progress.show()

        fetching_eip_conf_msg = 'Fetching eip service configuration'
        self.set_status(fetching_eip_conf_msg)
        self.progress.setValue(30)

        # Fetching eip service
        eipconfigchecker.fetch_eip_service_config(
            domain=domain)

        self.status_line_1.setText(
            self.get_donemsg(fetching_eip_conf_msg))

        getting_client_cert_msg = 'Getting client certificate'
        self.set_status(getting_client_cert_msg)
        self.progress.setValue(66)

        # Download cert
        try:
            pCertChecker.download_new_client_cert(
                credentials=credentials,
                # FIXME FIXME FIXME
                # XXX FIX THIS!!!!!
                # BUG #638. remove verify
                # FIXME FIXME FIXME
                verify=False)
        except auth.SRPAuthenticationError as exc:
            self.set_validation_status(
                "Authentication error: %s" % exc.message)
            return False

        time.sleep(2)
        self.status_line_2.setText(
            self.get_donemsg(getting_client_cert_msg))

        validating_clientcert_msg = 'Validating client certificate'
        self.set_status(validating_clientcert_msg)
        self.progress.setValue(90)
        time.sleep(2)
        self.status_line_3.setText(
            self.get_donemsg(validating_clientcert_msg))

        self.progress.setValue(100)
        time.sleep(3)

        # here we go! :)
        self.run_eip_checks_for_provider_and_connect(domain)

        #self.validation_block = self.wait_for_validation_block()

        # XXX signal timeout!
        return True

    #
    # wizardpage methods
    #

    def nextId(self):
        wizard = self.wizard()
        # XXX this does not work because
        # page login has already been met
        #if self.goto_login_again:
            #next_ = "login"
        #else:
            #next_ = "lastpage"
        next_ = "lastpage"
        return wizard.get_page_index(next_)

    def initializePage(self):
        # XXX if we're coming from signup page
        # we could say something like
        # 'registration successful!'
        self.status.setText(
            "We have "
            "all we need to connect with the provider.<br><br> "
            "Click <i>next</i> to continue. ")
        self.progress.setValue(0)
        self.progress.hide()
        self.status_line_1.setText('')
        self.status_line_2.setText('')
        self.status_line_3.setText('')

    def validatePage(self):
        # XXX remove
        validated = self.fetch_and_validate()
        return validated
