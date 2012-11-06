"""
Provider Setup Validation Page,
used if First Run Wizard
"""

from PyQt4 import QtGui

from leap.gui.progress import ValidationPage

from leap.gui.constants import APP_LOGO


class ProviderSetupValidationPage(ValidationPage):
    def __init__(self, parent=None):
        super(ProviderSetupValidationPage, self).__init__(parent)
        self.setTitle("Setting up provider")
        #self.setSubTitle(
            #"auto configuring provider...")

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

    def _do_checks(self, signal=None):
        """
        executes actual checks in a separate thread
        """
        import time
        domain = self.field('provider_domain')
        wizard = self.wizard()
        pconfig = wizard.providerconfig

        pCertChecker = wizard.providercertchecker
        certchecker = pCertChecker(domain=domain)

        signal.emit('Fetching CA certificate')
        self.progress.setValue(30)

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

        #certchecker.download_ca_cert(
            #uri=ca_cert_uri,
            #verify=False)

        time.sleep(2)

        signal.emit('Checking CA fingerprint')
        self.progress.setValue(66)
        #ca_cert_fingerprint = pconfig.get('ca_cert_fingerprint', None)

        # XXX get fingerprint dict (types)
        #sha256_fpr = ca_cert_fingerprint.split('=')[1]

        #validate_fpr = certchecker.check_ca_cert_fingerprint(
            #fingerprint=sha256_fpr)
        time.sleep(0.5)
        #if not validate_fpr:
            # XXX update validationMsg
            # should catch exception
            #return False

        signal.emit('Validating api certificate')
        self.progress.setValue(90)

        #api_uri = pconfig.get('api_uri', None)
        #try:
            #api_cert_verified = certchecker.verify_api_https(api_uri)
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
        time.sleep(0.5)
        #ca_cert_path = checker.ca_cert_path

        self.progress.setValue(100)
        signal.emit('end_sentinel')
        time.sleep(1)

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
        is_signup = self.field('is_signup')
        if is_signup is True:
            next_ = 'signup'
        if is_signup is False:
            next_ = 'connecting'
        return wizard.get_page_index(next_)
