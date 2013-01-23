"""
Provider Setup Validation Page,
used if First Run Wizard
"""
import logging

import requests

from PyQt4 import QtGui

from leap.base import exceptions as baseexceptions
from leap.gui.progress import ValidationPage

from leap.gui.constants import APP_LOGO

logger = logging.getLogger(__name__)


class ProviderSetupValidationPage(ValidationPage):
    def __init__(self, parent=None):
        super(ProviderSetupValidationPage, self).__init__(parent)
        self.current_page = "providersetupvalidation"

        # XXX needed anymore?
        #is_signup = self.field("is_signup")
        #self.is_signup = is_signup

        self.setTitle(self.tr("Provider setup"))
        self.setSubTitle(
            self.tr("Doing autoconfig."))

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

    def _do_checks(self):
        """
        generator that yields actual checks
        that are executed in a separate thread
        """

        full_domain = self.field('provider_domain')
        wizard = self.wizard()
        pconfig = wizard.providerconfig

        #pCertChecker = wizard.providercertchecker
        #certchecker = pCertChecker(domain=full_domain)
        pCertChecker = wizard.providercertchecker(
            domain=full_domain)

        yield(("head_sentinel", 0), lambda: None)

        ########################
        # 1) fetch ca cert
        ########################

        def fetchcacert():
            if pconfig:
                ca_cert_uri = pconfig.get('ca_cert_uri').geturl()
            else:
                ca_cert_uri = None

            # XXX check scheme == "https"
            # XXX passing verify == False because
            # we have trusted right before.
            # We should check it's the same domain!!!
            # (Check with the trusted fingerprints dict
            # or something smart)
            try:
                pCertChecker.download_ca_cert(
                    uri=ca_cert_uri,
                    verify=False)

            except baseexceptions.LeapException as exc:
                logger.error(exc.message)
                # XXX this should be _ method
                return self.fail(self.tr(exc.usermessage))

            except Exception as exc:
                return self.fail(exc.message)

            else:
                return True

        yield((self.tr('Fetching CA certificate'), 30),
              fetchcacert)

        #########################
        # 2) check CA fingerprint
        #########################

        def checkcafingerprint():
            # XXX get the real thing!!!
            pass
        #ca_cert_fingerprint = pconfig.get('ca_cert_fingerprint', None)

        # XXX get fingerprint dict (types)
        #sha256_fpr = ca_cert_fingerprint.split('=')[1]

        #validate_fpr = pCertChecker.check_ca_cert_fingerprint(
            #fingerprint=sha256_fpr)
        #if not validate_fpr:
            # XXX update validationMsg
            # should catch exception
            #return False

        yield((self.tr("Checking CA fingerprint"), 60),
              checkcafingerprint)

        #########################
        # 2) check CA fingerprint
        #########################

        def validatecacert():
            api_uri = pconfig.get('api_uri', None)
            try:
                pCertChecker.verify_api_https(api_uri)
            except requests.exceptions.SSLError as exc:
                return self.fail("Validation Error")
            except Exception as exc:
                return self.fail(exc.msg)
            else:
                return True

        yield((self.tr('Validating api certificate'), 90), validatecacert)

        self.set_done()
        yield(('end_sentinel', 100), lambda: None)

    def on_checks_validation_ready(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        wizard = self.wizard()
        prevpage = "login" if wizard.from_login else "providerselection"

        if self.errors:
            logger.debug('going back with errors')
            name, first_error = self.pop_first_error()
            wizard.set_validation_error(
                prevpage,
                first_error)

    def nextId(self):
        wizard = self.wizard()
        from_login = wizard.from_login
        if from_login:
            next_ = 'connect'
        else:
            next_ = 'signup'
        return wizard.get_page_index(next_)

    def initializePage(self):
        super(ProviderSetupValidationPage, self).initializePage()
        self.set_undone()
        self.completeChanged.emit()
