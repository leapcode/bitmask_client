"""
Provider Setup Validation Page,
used in First Run Wizard
"""
# XXX This page is called regvalidation
# but it's implementing functionality in the former
# connect page.
# We should remame it to connect again, when we integrate
# the login branch of the wizard.

import logging
import json
import socket

from PyQt4 import QtGui

import requests

from leap.gui.progress import ValidationPage
from leap.util.web import get_https_domain_and_port

from leap.base import auth
from leap.gui.constants import APP_LOGO

logger = logging.getLogger(__name__)


class RegisterUserValidationPage(ValidationPage):

    def __init__(self, parent=None):
        super(RegisterUserValidationPage, self).__init__(parent)

        title = "Connecting..."
        # XXX uh... really?
        subtitle = "Checking connection with provider."

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

        # FIXME #BUG 638 FIXME FIXME FIXME
        verify = False  # !!!!!!!!!!!!!!!!
        # FIXME #BUG 638 FIXME FIXME FIXME

        ###########################################
        # Set Credentials.
        # username and password are in different fields
        # if they were stored in log_in or sign_up pages.
        is_signup = self.field("is_signup")

        unamek_base = 'userName'
        passwk_base = 'userPassword'
        unamek = 'login_%s' % unamek_base if not is_signup else unamek_base
        passwk = 'login_%s' % passwk_base if not is_signup else passwk_base

        username = self.field(unamek)
        password = self.field(passwk)
        credentials = username, password

        eipconfigchecker = wizard.eipconfigchecker(domain=_domain)
        #XXX change for _domain (sanitized)
        pCertChecker = wizard.providercertchecker(
            domain=full_domain)

        update_signal.emit("head_sentinel", 0)

        ##################################################
        # 2) fetching eip service config
        ##################################################

        step = "fetch_eipconf"
        fetching_eipconf_msg = "Fetching eip service configuration"
        update_signal.emit(fetching_eipconf_msg, 60)
        try:
            eipconfigchecker.fetch_eip_service_config(
                domain=full_domain)

        # XXX get specific exception
        except:
            self.set_error(
                step,
                'Could not download eip config.')
            #pause_for_user()
            return False
        #pause_for_user()

        ##################################################
        # 3) getting client certificate
        ##################################################
        # XXX maybe only do this if we come from signup

        step = "fetch_eipcert"
        fetching_clientcert_msg = "Fetching eip certificate"
        update_signal.emit(fetching_clientcert_msg, 80)

        try:
            pCertChecker.download_new_client_cert(
                credentials=credentials,
                verify=verify)

        except auth.SRPAuthenticationError as exc:
            self.set_error(
                step,
                "Authentication error: %s" % exc.message)
            return False

        #pause_for_user()

        ################
        # end !
        ################

        update_signal.emit("end_sentinel", 100)
        #pause_for_user()

        # here we go! :)
        # this should be called CONNECT PAGE AGAIN.
        self.run_eip_checks_for_provider_and_connect(_domain)

    def on_checks_validation_ready(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        pass

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
        is_signup = self.field("is_signup")
        prevpage = "signup" if is_signup else "login"

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
        if not wizard:
            return
        return wizard.get_page_index('lastpage')

    def initializePage(self):
        super(RegisterUserValidationPage, self).initializePage()
        self.set_undone()
        self.completeChanged.emit()
