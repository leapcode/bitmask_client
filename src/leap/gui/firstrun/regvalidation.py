"""
Provider Setup Validation Page,
used if First Run Wizard
"""
import logging
import json
import socket
import time

from PyQt4 import QtGui

import requests

from leap.gui.progress import ValidationPage

from leap.base import auth
from leap.gui.constants import APP_LOGO

logger = logging.getLogger(__name__)


class RegisterUserValidationPage(ValidationPage):

    def __init__(self, parent=None):

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
        domain = self.field('provider_domain')
        username = self.field('userName')
        password = self.field('userPassword')

        update_signal.emit("head_sentinel")
        update_signal.emit("registering with provider", 40)
        time.sleep(4)

        if wizard and wizard.debug_server:
            # We're debugging
            dbgsrv = wizard.debug_server
            schema = dbgsrv.scheme
            netloc = dbgsrv.netloc
            port = None
            netloc_split = netloc.split(':')
            if len(netloc_split) > 1:
                provider, port = netloc_split
            else:
                provider = netloc

            signup = auth.LeapSRPRegister(
                scheme=schema,
                provider=provider,
                port=port)

        else:
            # this is the real thing
            signup = auth.LeapSRPRegister(
                # XXX FIXME FIXME FIXME FIXME
                # XXX FIXME 0 Force HTTPS !!!
                # XXX FIXME FIXME FIXME FIXME
                #schema="https",
                schema="http",
                provider=domain)
        try:
            ok, req = signup.register_user(username, password)
        except socket.timeout:
            self.set_validation_status(
                "Error connecting to provider (timeout)")
            return False

        except requests.exceptions.ConnectionError as exc:
            logger.error(exc)
            self.set_validation_status(
                "Error connecting to provider "
                "(connection error)")
            return False

        if ok:
            return True

        # something went wrong.
        # not registered, let's catch what.
        # get timeout
        # ...
        if req.status_code == 500:
            self.set_validation_status(
                "Error during registration (500)")
            return False

        if req.status_code == 404:
            self.set_validation_status(
                "Error during registration (404)")
            return False

        validation_msgs = json.loads(req.content)
        logger.debug('validation errors: %s' % validation_msgs)
        errors = validation_msgs.get('errors', None)
        if errors and errors.get('login', None):
            # XXX this sometimes catch the blank username
            # but we're not allowing that (soon)
            self.set_validation_status(
                'Username not available.')
        else:
            self.set_validation_status(
                "Error during sign up")
        return False

    def _do_validation(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        wizard = self.wizard()
        if self.errors:
            print 'going back with errors'
            wizard.set_validation_error(
                'signup', 'that name is taken')
            self.go_back()
        else:
            print 'going next'
            self.go_next()

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('connecting')
