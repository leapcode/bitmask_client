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
from leap.gui.constants import APP_LOGO, pause_for_user

logger = logging.getLogger(__name__)


class RegisterUserValidationPage(ValidationPage):

    def __init__(self, parent=None):
        # XXX TODO:
        # We should check if we come from signup
        # or login, and change title / first step
        # accordingly.

        super(RegisterUserValidationPage, self).__init__(parent)
        self.setTitle("User Creation")
        self.setSubTitle(
            "Registering account with provider.")

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

        # FIXME #BUG 638 FIXME FIXME FIXME
        verify = False  # !!!!!!!!!!!!!!!!
        # FIXME #BUG 638 FIXME FIXME FIXME

        ###########################################
        # Set Credentials.
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

        eipconfigchecker = wizard.eipconfigchecker()
        pCertChecker = wizard.providercertchecker(
            domain=full_domain)

        ###########################################
        # XXX this only should be setup
        # if not from_login.

        signup = auth.LeapSRPRegister(
            schema="https",
            provider=full_domain,
            verify=verify)

        update_signal.emit("head_sentinel", 0)

        ##################################################
        # 1) register user
        ##################################################
        # XXX this only should be DONE
        # if NOT from_login.

        step = "register"
        update_signal.emit("checking availability", 20)
        update_signal.emit("registering with provider", 40)
        logger.debug('registering user')

        try:
            ok, req = signup.register_user(
                username, password)

        except socket.timeout:
            self.set_error(
                step,
                "Error connecting to provider (timeout)")
            pause_for_user()
            return False

        except requests.exceptions.ConnectionError as exc:
            logger.error(exc.message)
            self.set_error(
                step,
                "Error connecting to provider "
                "(connection error)")
            # XXX we should signal a BAD step
            pause_for_user()
            update_signal.emit("connection error!", 50)
            pause_for_user()
            return False

        # XXX check for != OK instead???

        if req.status_code in (404, 500):
            self.set_error(
                step,
                "Error during registration (%s)" % req.status_code)
            pause_for_user()
            return False

        validation_msgs = json.loads(req.content)
        errors = validation_msgs.get('errors', None)
        logger.debug('validation errors: %s' % validation_msgs)

        if errors and errors.get('login', None):
            # XXX this sometimes catch the blank username
            # but we're not allowing that (soon)
            self.set_error(
                step,
                'Username not available.')
            pause_for_user()
            return False

        pause_for_user()

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
            pause_for_user()
            return False
        pause_for_user()

        ##################################################
        # 3) getting client certificate
        ##################################################

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

        pause_for_user()

        ################
        # end !
        ################

        update_signal.emit("end_sentinel", 100)
        pause_for_user()

        # here we go! :)
        self.run_eip_checks_for_provider_and_connect(domain)

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
            logger.debug('going next')
            # check if this "next" interferes
            # with the eip signal.
            self.go_next()

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('lastpage')
