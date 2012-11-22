"""
Provider Setup Validation Page,
used if First Run Wizard
"""
import logging

from PyQt4 import QtGui

from leap.base import exceptions as baseexceptions
from leap.gui.progress import ValidationPage

from leap.gui.constants import APP_LOGO

logger = logging.getLogger(__name__)


class ProviderSetupValidationPage(ValidationPage):
    def __init__(self, parent=None):
        super(ProviderSetupValidationPage, self).__init__(parent)
        is_signup = self.field("is_signup")
        self.is_signup = is_signup

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
        curpage = "providersetupvalidation"

        full_domain = self.field('provider_domain')
        wizard = self.wizard()
        pconfig = wizard.providerconfig

        #pCertChecker = wizard.providercertchecker
        #certchecker = pCertChecker(domain=full_domain)
        pCertChecker = wizard.providercertchecker(
            domain=full_domain)

        def fail():
            self.is_done = False
            return False

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
                wizard.set_validation_error(
                    curpage, exc.usermessage)
                return fail()

            except Exception as exc:
                wizard.set_validation_error(
                    curpage, exc.message)
                return fail()

            else:
                return True

        yield(('Fetching CA certificate', 30), fetchcacert)

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

        yield((self.tr("Checking CA fingerprint"), 60), checkcafingerprint)

        #########################
        # 2) check CA fingerprint
        #########################

        def validatecacert():
            pass
            #api_uri = pconfig.get('api_uri', None)
            #try:
                #api_cert_verified = pCertChecker.verify_api_https(api_uri)
            #except requests.exceptions.SSLError as exc:
                #logger.error('BUG #638. %s' % exc.message)
                # XXX RAISE! See #638
                # bypassing until the hostname is fixed.
                # We probably should raise yet-another-warning
                # here saying user that the hostname "XX.XX.XX.XX' does not
                # match 'foo.bar.baz'
                #api_cert_verified = True

            #if not api_cert_verified:
                # XXX update validationMsg
                # should catch exception
                #return False

            #???
            #ca_cert_path = checker.ca_cert_path

        yield((self.tr('Validating api certificate'), 90), validatecacert)

        self.set_done()
        yield(('end_sentinel', 100), lambda: None)

    def on_checks_validation_ready(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        prevpage = "providerselection" if self.is_signup else "login"
        wizard = self.wizard()

        if self.errors:
            logger.debug('going back with errors')
            name, first_error = self.pop_first_error()
            wizard.set_validation_error(
                prevpage,
                first_error)
            # XXX don't go back, signal error
            #self.go_back()
        else:
            logger.debug('should be going next, wait on user')
            #self.go_next()

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        is_signup = self.field('is_signup')
        if is_signup is True:
            next_ = 'signup'
        if is_signup is False:
            # XXX bad name. change to connect again.
            next_ = 'signupvalidation'
        return wizard.get_page_index(next_)

    def initializePage(self):
        super(ProviderSetupValidationPage, self).initializePage()
        self.set_undone()
        self.completeChanged.emit()
