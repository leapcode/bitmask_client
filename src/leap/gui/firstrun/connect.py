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
        # XXX uh... really?
        subtitle = self.tr("Checking connection with provider.")

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
        _domain = u"%s:%s" % (domain, port) if port != 443 else unicode(domain)

        verify = True

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

        eipconfigchecker = wizard.eipconfigchecker(domain=_domain)
        #XXX change for _domain (sanitized)
        pCertChecker = wizard.providercertchecker(
            domain=full_domain)

        yield(("head_sentinel", 0), lambda: None)

        ##################################################
        # 1) fetching eip service config
        ##################################################
        def fetcheipconf():
            try:
                eipconfigchecker.fetch_eip_service_config(
                    domain=full_domain)

            # XXX get specific exception
            except Exception as exc:
                return self.fail(exc.message)

        yield((self.tr("Fetching provider config..."), 40),
              fetcheipconf)

        ##################################################
        # 2) getting client certificate
        ##################################################

        def fetcheipcert():
            try:
                downloaded = pCertChecker.download_new_client_cert(
                    credentials=credentials,
                    verify=verify)
                if not downloaded:
                    logger.error('Could not download client cert.')
                    return False

            except auth.SRPAuthenticationError as exc:
                return self.fail(self.tr(
                    "Authentication error: %s" % exc.message))
            else:
                return True

        yield((self.tr("Fetching eip certificate"), 80),
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
        # this should be called CONNECT PAGE AGAIN.
        # here we go! :)
        if self.is_done():
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
            conductor.run_checks()
            self.conductor = conductor
            errors = self.eip_error_check()
            if not errors and start_eip_signal:
                start_eip_signal.emit()

        else:
            logger.warning(
                "No conductor found. This means that "
                "probably the wizard has been launched "
                "in an stand-alone way.")

        # XXX look for a better place to signal
        # we are done.
        # We could probably have a fake validatePage
        # that checks if the domain transfer has been
        # done to conductor object, triggers the start_signal
        # and does the go_next()
        self.set_done()

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

    def _do_validation(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        from_login = self.wizard().from_login
        prevpage = "login" if from_login else "signup"

        wizard = self.wizard()
        if self.errors:
            logger.debug('going back with errors')
            logger.error(self.errors)
            name, first_error = self.pop_first_error()
            wizard.set_validation_error(
                prevpage,
                first_error)
            self.go_back()
        else:
            logger.debug('should go next, wait for user to click next')
            #self.go_next()

    def nextId(self):
        wizard = self.wizard()
        #if not wizard:
            #return
        return wizard.get_page_index('lastpage')

    def initializePage(self):
        super(ConnectionPage, self).initializePage()
        self.set_undone()
        self.completeChanged.emit()
