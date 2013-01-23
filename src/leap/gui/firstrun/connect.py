"""
Provider Setup Validation Page,
used in First Run Wizard
"""
import logging

from PyQt4 import QtGui

#import requests

from leap.gui.progress import ValidationPage
from leap.util.web import get_https_domain_and_port

from leap.base import auth
from leap.gui.constants import APP_LOGO

logger = logging.getLogger(__name__)


class ConnectionPage(ValidationPage):

    def __init__(self, parent=None):
        super(ConnectionPage, self).__init__(parent)
        self.current_page = "connect"

        title = self.tr("Connecting...")
        subtitle = self.tr("Setting up a encrypted "
                           "connection with the provider")

        self.setTitle(title)
        self.setSubTitle(subtitle)

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

    def _do_checks(self, update_signal=None):
        """
        executes actual checks in a separate thread

        we initialize the srp protocol register
        and try to register user.
        """
        wizard = self.wizard()
        full_domain = self.field('provider_domain')
        domain, port = get_https_domain_and_port(full_domain)

        pconfig = wizard.eipconfigchecker(domain=domain)
        # this should be persisted...
        pconfig.defaultprovider.load()
        pconfig.set_api_domain()

        pCertChecker = wizard.providercertchecker(
            domain=domain)
        pCertChecker.set_api_domain(pconfig.apidomain)

        ###########################################
        # Set Credentials.
        # username and password are in different fields
        # if they were stored in log_in or sign_up pages.
        from_login = wizard.from_login

        unamek_base = 'userName'
        passwk_base = 'userPassword'
        unamek = 'login_%s' % unamek_base if from_login else unamek_base
        passwk = 'login_%s' % passwk_base if from_login else passwk_base

        username = self.field(unamek)
        password = self.field(passwk)
        credentials = username, password

        yield(("head_sentinel", 0), lambda: None)

        ##################################################
        # 1) fetching eip service config
        ##################################################
        def fetcheipconf():
            try:
                pconfig.fetch_eip_service_config()

            # XXX get specific exception
            except Exception as exc:
                return self.fail(exc.message)

        yield((self.tr("Getting EIP configuration files"), 40),
              fetcheipconf)

        ##################################################
        # 2) getting client certificate
        ##################################################

        def fetcheipcert():
            try:
                downloaded = pCertChecker.download_new_client_cert(
                    credentials=credentials)
                if not downloaded:
                    logger.error('Could not download client cert')
                    return False

            except auth.SRPAuthenticationError as exc:
                return self.fail(self.tr(
                    "Authentication error: %s" % exc.message))

            except Exception as exc:
                return self.fail(exc.message)
            else:
                return True

        yield((self.tr("Getting EIP certificate"), 80),
              fetcheipcert)

        ################
        # end !
        ################
        self.set_done()
        yield(("end_sentinel", 100), lambda: None)

    def on_checks_validation_ready(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        # here we go! :)
        if self.is_done():
            nextbutton = self.wizard().button(QtGui.QWizard.NextButton)
            nextbutton.setFocus()

            full_domain = self.field('provider_domain')
            domain, port = get_https_domain_and_port(full_domain)
            _domain = u"%s:%s" % (
                domain, port) if port != 443 else unicode(domain)
            self.run_eip_checks_for_provider_and_connect(_domain)

    def run_eip_checks_for_provider_and_connect(self, domain):
        wizard = self.wizard()
        conductor = wizard.conductor
        start_eip_signal = getattr(
            wizard,
            'start_eipconnection_signal', None)

        if conductor:
            conductor.set_provider_domain(domain)
            # we could run some of the checks to be
            # sure everything is in order, but
            # I see no point in doing it, we assume
            # we've gone thru all checks during the wizard.
            #conductor.run_checks()
            #self.conductor = conductor
            #errors = self.eip_error_check()
            #if not errors and start_eip_signal:
            if start_eip_signal:
                start_eip_signal.emit()

        else:
            logger.warning(
                "No conductor found. This means that "
                "probably the wizard has been launched "
                "in an stand-alone way.")

        self.set_done()

    #def eip_error_check(self):
        #"""
        #a version of the main app error checker,
        #but integrated within the connecting page of the wizard.
        #consumes the conductor error queue.
        #pops errors, and add those to the wizard page
        #"""
        # TODO handle errors.
        # We should redirect them to the log viewer
        # with a brief message.
        # XXX move to LAST PAGE instead.
        #logger.debug('eip error check from connecting page')
        #errq = self.conductor.error_queue

    #def _do_validation(self):
        #"""
        #called after _do_checks has finished
        #(connected to checker thread finished signal)
        #"""
        #from_login = self.wizard().from_login
        #prevpage = "login" if from_login else "signup"

        #wizard = self.wizard()
        #if self.errors:
            #logger.debug('going back with errors')
            #logger.error(self.errors)
            #name, first_error = self.pop_first_error()
            #wizard.set_validation_error(
                #prevpage,
                #first_error)
            #self.go_back()

    def nextId(self):
        wizard = self.wizard()
        return wizard.get_page_index('lastpage')

    def initializePage(self):
        super(ConnectionPage, self).initializePage()
        self.set_undone()
        cancelbutton = self.wizard().button(QtGui.QWizard.CancelButton)
        cancelbutton.hide()
        self.completeChanged.emit()

        wizard = self.wizard()
        eip_statuschange_signal = wizard.eip_statuschange_signal
        if eip_statuschange_signal:
            eip_statuschange_signal.connect(
                lambda status: self.send_status(
                    status))

    def send_status(self, status):
        wizard = self.wizard()
        wizard.openvpn_status.append(status)
