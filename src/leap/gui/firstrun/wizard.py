#!/usr/bin/env python
import logging

import sip
try:
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
except ValueError:
    pass

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.base import checks as basechecks
from leap.crypto import leapkeyring
from leap.eip import checks as eipchecks

from leap.gui import firstrun

from leap.gui import mainwindow_rc

try:
    from collections import OrderedDict
except ImportError:
    # We must be in 2.6
    from leap.util.dicts import OrderedDict

logger = logging.getLogger(__name__)

"""
~~~~~~~~~~~~~~~~~~~~~~~~~~
Work in progress!
~~~~~~~~~~~~~~~~~~~~~~~~~~
This wizard still needs to be refactored out.

TODO-ish:

[X] Break file in wizard / pages files (and its own folder).
[ ] Separate presentation from logic.
[ ] Have a "manager" class for connections, that can be
    dep-injected for testing.
[ ] Document signals used / expected.
[ ] Separate style from widgets.
[ ] Fix TOFU Widget for provider cert.
[X] Refactor widgets out.
[ ] Follow more MVC style.
[ ] Maybe separate "first run wizard" into different wizards
    that share some of the pages?
"""


def get_pages_dict():
    return OrderedDict((
        ('intro', firstrun.intro.IntroPage),
        ('providerselection',
            firstrun.providerselect.SelectProviderPage),
        ('login', firstrun.login.LogInPage),
        ('providerinfo', firstrun.providerinfo.ProviderInfoPage),
        ('providersetupvalidation',
            firstrun.providersetup.ProviderSetupValidationPage),
        ('signup', firstrun.register.RegisterUserPage),
        ('connect',
            firstrun.connect.ConnectionPage),
        ('lastpage', firstrun.last.LastPage)
    ))


class FirstRunWizard(QtGui.QWizard):

    def __init__(
            self,
            conductor_instance,
            parent=None,
            pages_dict=None,
            username=None,
            providers=None,
            success_cb=None, is_provider_setup=False,
            trusted_certs=None,
            netchecker=basechecks.LeapNetworkChecker,
            providercertchecker=eipchecks.ProviderCertChecker,
            eipconfigchecker=eipchecks.EIPConfigChecker,
            start_eipconnection_signal=None,
            eip_statuschange_signal=None,
            debug_server=None,
            quitcallback=None):
        super(FirstRunWizard, self).__init__(
            parent,
            QtCore.Qt.WindowStaysOnTopHint)

        # we keep a reference to the conductor
        # to be able to launch eip checks and connection
        # in the connection page, before the wizard has ended.
        self.conductor = conductor_instance

        self.username = username
        self.providers = providers

        # success callback
        self.success_cb = success_cb

        # is provider setup?
        self.is_provider_setup = is_provider_setup

        # a dict with trusted fingerprints
        # in the form {'nospacesfingerprint': ['host1', 'host2']}
        self.trusted_certs = trusted_certs

        # Checkers
        self.netchecker = netchecker
        self.providercertchecker = providercertchecker
        self.eipconfigchecker = eipconfigchecker

        # debug server
        self.debug_server = debug_server

        # Signals
        # will be emitted in connecting page
        self.start_eipconnection_signal = start_eipconnection_signal
        self.eip_statuschange_signal = eip_statuschange_signal

        if quitcallback is not None:
            self.button(
                QtGui.QWizard.CancelButton).clicked.connect(
                    quitcallback)

        self.providerconfig = None
        # previously registered
        # if True, jumps to LogIn page.
        # by setting 1st page??
        #self.is_previously_registered = is_previously_registered
        # XXX ??? ^v
        self.is_previously_registered = bool(self.username)
        self.from_login = False

        pages_dict = pages_dict or get_pages_dict()
        self.add_pages_from_dict(pages_dict)

        self.validation_errors = {}
        self.openvpn_status = []

        self.setPixmap(
            QtGui.QWizard.BannerPixmap,
            QtGui.QPixmap(':/images/banner.png'))
        self.setPixmap(
            QtGui.QWizard.BackgroundPixmap,
            QtGui.QPixmap(':/images/background.png'))

        # set options
        self.setOption(QtGui.QWizard.IndependentPages, on=False)
        self.setOption(QtGui.QWizard.NoBackButtonOnStartPage, on=True)

        self.setWindowTitle("First Run Wizard")

        # TODO: set style for MAC / windows ...
        #self.setWizardStyle()

    #
    # setup pages in wizard
    #

    def add_pages_from_dict(self, pages_dict):
        """
        @param pages_dict: the dictionary with pages, where
            values are a tuple of InstanceofWizardPage, kwargs.
        @type pages_dict: dict
        """
        for name, page in pages_dict.items():
            # XXX check for is_previously registered
            # and skip adding the signup branch if so
            self.addPage(page())
        self.pages_dict = pages_dict

    def get_page_index(self, page_name):
        """
        returns the index of the given page
        @param page_name: the name of the desired page
        @type page_name: str
        @rparam: index of page in wizard
        @rtype: int
        """
        return self.pages_dict.keys().index(page_name)

    #
    # validation errors
    #

    def set_validation_error(self, pagename, error):
        self.validation_errors[pagename] = error

    def clean_validation_error(self, pagename):
        vald = self.validation_errors
        if pagename in vald:
            del vald[pagename]

    def get_validation_error(self, pagename):
        return self.validation_errors.get(pagename, None)

    def accept(self):
        """
        final step in the wizard.
        gather the info, update settings
        and call the success callback if any has been passed.
        """
        super(FirstRunWizard, self).accept()

        # username and password are in different fields
        # if they were stored in log_in or sign_up pages.
        from_login = self.from_login
        unamek_base = 'userName'
        passwk_base = 'userPassword'
        unamek = 'login_%s' % unamek_base if from_login else unamek_base
        passwk = 'login_%s' % passwk_base if from_login else passwk_base

        username = self.field(unamek)
        password = self.field(passwk)
        provider = self.field('provider_domain')
        remember_pass = self.field('rememberPassword')

        logger.debug('chosen provider: %s', provider)
        logger.debug('username: %s', username)
        logger.debug('remember password: %s', remember_pass)

        # we are assuming here that we only remember one username
        # in the form username@provider.domain
        # We probably could extend this to support some form of
        # profiles.

        settings = QtCore.QSettings()

        settings.setValue("FirstRunWizardDone", True)
        settings.setValue("provider_domain", provider)
        full_username = "%s@%s" % (username, provider)

        settings.setValue("remember_user_and_pass", remember_pass)

        if remember_pass:
            settings.setValue("username", full_username)
            seed = self.get_random_str(10)
            settings.setValue("%s_seed" % provider, seed)

            # XXX #744: comment out for 0.2.0 release
            # if we need to have a version of python-keyring < 0.9
            leapkeyring.leap_set_password(
                full_username, password, seed=seed)

        logger.debug('First Run Wizard Done.')
        cb = self.success_cb
        if cb and callable(cb):
            self.success_cb()

    # misc helpers

    def get_random_str(self, n):
        """
        returns a random string
        :param n: the length of the desired string
        :rvalue: str
        """
        from string import (ascii_uppercase, ascii_lowercase, digits)
        from random import choice
        return ''.join(choice(
            ascii_uppercase +
            ascii_lowercase +
            digits) for x in range(n))

    def set_providerconfig(self, providerconfig):
        """
        sets a providerconfig attribute
        used when we fetch and parse a json configuration
        """
        self.providerconfig = providerconfig

    def get_provider_by_index(self):  # pragma: no cover
        """
        returns the value of a provider given its index.
        this was used in the select provider page,
        in the case where we were preseeding providers in a combobox
        """
        # Leaving it here for the moment when we go back at the
        # option of preseeding with known provider values.
        provider = self.field('provider_index')
        return self.providers[provider]


if __name__ == '__main__':
    # standalone test
    # it can be (somehow) run against
    # gui/tests/integration/fake_user_signup.py

    import sys
    import logging
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    app = QtGui.QApplication(sys.argv)
    server = sys.argv[1] if len(sys.argv) > 1 else None

    trusted_certs = {
        "3DF83F316BFA0186"
        "0A11A5C9C7FC24B9"
        "18C62B941192CC1A"
        "49AE62218B2A4B7C": ['springbok']}

    wizard = FirstRunWizard(
        None, trusted_certs=trusted_certs,
        debug_server=server)
    wizard.show()
    sys.exit(app.exec_())
