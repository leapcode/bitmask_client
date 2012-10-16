#!/usr/bin/env python
import logging
import json
import socket

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.crypto import leapkeyring
from leap.gui import mainwindow_rc

try:
    from collections import OrderedDict
except ImportError:
    # We must be in 2.6
    from leap.util.dicts import OrderedDict

# XXX DEBUG
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

APP_LOGO = ':/images/leap-color-small.png'

# registration ######################
# move to base/
import binascii

import requests
import srp

from leap.base import constants as baseconstants

SIGNUP_TIMEOUT = getattr(baseconstants, 'SIGNUP_TIMEOUT', 5)


class LeapSRPRegister(object):

    def __init__(self,
                 schema="https",
                 provider=None,
                 port=None,
                 register_path="1/users.json",
                 method="POST",
                 fetcher=requests,
                 srp=srp,
                 hashfun=srp.SHA256,
                 ng_constant=srp.NG_1024):

        self.schema = schema
        self.provider = provider
        self.port = port
        self.register_path = register_path
        self.method = method
        self.fetcher = fetcher
        self.srp = srp
        self.HASHFUN = hashfun
        self.NG = ng_constant

        self.init_session()

    def init_session(self):
        self.session = self.fetcher.session()

    def get_registration_uri(self):
        # XXX assert is https!
        # use urlparse
        if self.port:
            uri = "%s://%s:%s/%s" % (
                self.schema,
                self.provider,
                self.port,
                self.register_path)
        else:
            uri = "%s://%s/%s" % (
                self.schema,
                self.provider,
                self.register_path)

        return uri

    def register_user(self, username, password, keep=False):
        """
        @rtype: tuple
        @rparam: (ok, request)
        """
        salt, vkey = self.srp.create_salted_verification_key(
            username,
            password,
            self.HASHFUN,
            self.NG)

        user_data = {
            'user[login]': username,
            'user[password_verifier]': binascii.hexlify(vkey),
            'user[password_salt]': binascii.hexlify(salt)}

        uri = self.get_registration_uri()
        logger.debug('post to uri: %s' % uri)

        # XXX get self.method
        req = self.session.post(
            uri, data=user_data,
            timeout=SIGNUP_TIMEOUT)
        logger.debug(req)
        logger.debug('user_data: %s', user_data)
        #logger.debug('response: %s', req.text)
        # we catch it in the form
        #req.raise_for_status()
        return (req.ok, req)

######################################

ErrorLabelStyleSheet = """
QLabel { color: red;
         font-weight: bold}
"""


class FirstRunWizard(QtGui.QWizard):

    def __init__(
            self, parent=None, providers=None,
            success_cb=None, is_provider_setup=False):
        super(FirstRunWizard, self).__init__(
            parent,
            QtCore.Qt.WindowStaysOnTopHint)

        # XXX hardcoded for tests
        if not providers:
            providers = ('springbok',)
        self.providers = providers

        # success callback
        self.success_cb = success_cb

        # is provider setup?
        self.is_provider_setup = is_provider_setup

        # FIXME remove kwargs, we can access
        # wizard as self.wizard()

        # FIXME add param for previously_registered
        # should start at login page.

        pages_dict = OrderedDict((
            # (name, (WizardPage, **kwargs))
            ('intro', (IntroPage, {})),
            ('providerselection', (
                SelectProviderPage,
                {'providers': providers})),
            ('login', (LogInPage, {})),
            ('providerinfo', (ProviderInfoPage, {})),
            ('providersetup', (ProviderSetupPage, {})),
            ('signup', (
                RegisterUserPage, {})),
            ('connecting', (ConnectingPage, {})),
            ('lastpage', (LastPage, {}))
        ))
        self.add_pages_from_dict(pages_dict)

        self.setPixmap(
            QtGui.QWizard.BannerPixmap,
            QtGui.QPixmap(':/images/banner.png'))
        self.setPixmap(
            QtGui.QWizard.BackgroundPixmap,
            QtGui.QPixmap(':/images/background.png'))

        self.setWindowTitle("First Run Wizard")

        # TODO: set style for MAC / windows ...
        #self.setWizardStyle()

    def add_pages_from_dict(self, pages_dict):
        """
        @param pages_dict: the dictionary with pages, where
            values are a tuple of InstanceofWizardPage, kwargs.
        @type pages_dict: dict
        """
        for name, (page, page_args) in pages_dict.items():
            self.addPage(page(**page_args))
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

    #def get_page(self, page_name):
        #"""
        #returns a wizard page doing a lookup for
        #the page_name in the pages dictionary
        #@param page_name: the page name to lookup
        #@type page_name: str
        #"""
        #logger.debug('getting page %s' % page_name)
        #page_tuple = self.pages_dict.get(page_name, None)
        #if not page_tuple:
            #return None
        #wizard_page, args = page_tuple
        #logger.debug('wizard page %s', wizard_page)
        #return wizard_page

    def setWindowFlags(self, flags):
        logger.debug('setting window flags')
        QtGui.QWizard.setWindowFlags(self, flags)

    def focusOutEvent(self, event):
        # needed ?
        self.setFocus(True)
        self.activateWindow()
        self.raise_()
        self.show()

    def accept(self):
        """
        final step in the wizard.
        gather the info, update settings
        and call the success callback.
        """
        provider = self.get_provider()
        username = self.field('userName')
        #password = self.field('userPassword')
        remember_pass = self.field('rememberPassword')

        logger.debug('chosen provider: %s', provider)
        logger.debug('username: %s', username)
        logger.debug('remember password: %s', remember_pass)
        super(FirstRunWizard, self).accept()

        settings = QtCore.QSettings()
        settings.setValue("FirstRunWizardDone", True)
        settings.setValue(
            "eip_%s_username" % provider,
            username)
        settings.setValue("%s_remember_pass" % provider, remember_pass)

        seed = self.get_random_str(10)
        settings.setValue("%s_seed" % provider, seed)

        # Commenting out for 0.2.0 release
        # since we did not fix #744 on time.

        #leapkeyring.leap_set_password(username, password, seed=seed)

        logger.debug('First Run Wizard Done.')
        cb = self.success_cb
        if cb and callable(cb):
            self.success_cb()

    def get_provider(self):
        provider = self.field('provider_index')
        return self.providers[provider]

    def get_random_str(self, n):
        from string import (ascii_uppercase, ascii_lowercase, digits)
        from random import choice
        return ''.join(choice(
            ascii_uppercase +
            ascii_lowercase +
            digits) for x in range(n))


class IntroPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)

        self.setTitle("First run wizard.")

        #self.setPixmap(
            #QtGui.QWizard.WatermarkPixmap,
            #QtGui.QPixmap(':/images/watermark1.png'))

        label = QtGui.QLabel(
            "Now we will guide you through "
            "some configuration that is needed before you "
            "can connect for the first time.<br><br>"
            "If you ever need to modify these options again, "
            "you can find the wizard in the '<i>Settings</i>' menu from the "
            "main window.<br><br>"
            "Do you want to <b>sign up</b> for a new account, or <b>log "
            "in</b> with an already existing username?<br>")
        label.setWordWrap(True)

        self.sign_up = QtGui.QRadioButton(
            "Sign up for a new account.")
        self.sign_up.setChecked(True)
        self.log_in = QtGui.QRadioButton(
            "Log In with my credentials.")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.sign_up)
        layout.addWidget(self.log_in)
        self.setLayout(layout)

        self.registerField('is_signup', self.sign_up)

    def validatePage(self):
        return True

    def nextId(self):
        """
        returns next id
        in a non-linear wizard
        """
        if self.sign_up.isChecked():
            next_ = 'providerselection'
        if self.log_in.isChecked():
            next_ = 'login'
        wizard = self.wizard()
        return wizard.get_page_index(next_)


class SelectProviderPage(QtGui.QWizardPage):
    def __init__(self, parent=None, providers=None):
        super(SelectProviderPage, self).__init__(parent)

        self.setTitle("Select Provider")
        self.setSubTitle(
            "Please select which provider do you want "
            "to use for your connection."
        )
        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        providerNameLabel = QtGui.QLabel("&Provider:")

        providercombo = QtGui.QComboBox()
        if providers:
            for provider in providers:
                providercombo.addItem(provider)
        providerNameSelect = providercombo

        providerNameLabel.setBuddy(providerNameSelect)

        self.registerField('provider_index', providerNameSelect)

        layout = QtGui.QGridLayout()
        layout.addWidget(providerNameLabel, 0, 0)
        layout.addWidget(providerNameSelect, 0, 1)
        self.setLayout(layout)

    def validatePage(self):
        # XXX just DEBUGGING ..>!
        wizard = self.wizard()
        if bool(wizard):
            logger.debug('current: %s', wizard.currentPage())
        return True

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('providerinfo')


class ProviderInfoPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(ProviderInfoPage, self).__init__(parent)

        self.setTitle("Provider Info")
        self.setSubTitle("Available information about chosen provider.")

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('providersetup')


class ProviderSetupPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(ProviderSetupPage, self).__init__(parent)

        self.setTitle("Provider Setup")
        self.setSubTitle("Setting up provider.")

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


class UserFormMixIn(object):

    def reset_validation_status(self):
        """
        empty the validation msg
        """
        self.validationMsg.setText('')

    def set_status_validating(self):
        """
        set validation msg to 'registering...'
        """
        # XXX  this is NOT WORKING.
        # My guess is that, even if we are using
        # signals to trigger this, it does
        # not show until the validate function
        # returns.
        # I guess it is because there is no delay...
        logger.debug('registering........')
        self.validationMsg.setText('registering...')
        # need to call update somehow???

    # XXX refactor set_status_foo

    def set_status_invalid_username(self):
        """
        set validation msg to
        not available user
        """
        self.validationMsg.setText('Username not available.')

    def set_status_server_500(self):
        """
        set validation msg to
        internal server error
        """
        self.validationMsg.setText("Error during registration (500)")

    def set_status_timeout(self):
        """
        set validation msg to
        timeout
        """
        self.validationMsg.setText("Error connecting to provider (timeout)")

    def set_status_connerror(self):
        """
        set validation msg to
        connection refused
        """
        self.validationMsg.setText(
            "Error connecting to provider "
            "(connection error)")

    def set_status_unknown_error(self):
        """
        set validation msg to
        unknown error
        """
        self.validationMsg.setText("Error during signup")


class LogInPage(QtGui.QWizardPage, UserFormMixIn):
    def __init__(self, parent=None):
        super(LogInPage, self).__init__(parent)

        self.setTitle("Log In")
        self.setSubTitle("Log in with your credentials.")

        userNameLabel = QtGui.QLabel("User &name:")
        userNameLineEdit = QtGui.QLineEdit()
        userNameLineEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        userNameLabel.setBuddy(userNameLineEdit)

        # add regex validator
        usernameRe = QtCore.QRegExp(r"^[A-Za-z\d_]+$")
        userNameLineEdit.setValidator(
            QtGui.QRegExpValidator(usernameRe, self))
        self.userNameLineEdit = userNameLineEdit

        userPasswordLabel = QtGui.QLabel("&Password:")
        self.userPasswordLineEdit = QtGui.QLineEdit()
        self.userPasswordLineEdit.setEchoMode(
            QtGui.QLineEdit.Password)
        userPasswordLabel.setBuddy(self.userPasswordLineEdit)

        self.registerField('log_in_userName*', self.userNameLineEdit)
        self.registerField('log_in_userPassword*', self.userPasswordLineEdit)

        layout = QtGui.QGridLayout()
        layout.setColumnMinimumWidth(0, 20)

        validationMsg = QtGui.QLabel("")
        validationMsg.setStyleSheet(ErrorLabelStyleSheet)

        self.validationMsg = validationMsg

        layout.addWidget(validationMsg, 0, 3)

        layout.addWidget(userNameLabel, 1, 0)
        layout.addWidget(self.userNameLineEdit, 1, 3)

        layout.addWidget(userPasswordLabel, 2, 0)
        layout.addWidget(self.userPasswordLineEdit, 2, 3)

        self.setLayout(layout)

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        if wizard.is_provider_setup is True:
            next_ = 'connecting'
        if wizard.is_provider_setup is False:
            next_ = 'providersetup'
        return wizard.get_page_index(next_)


class RegisterUserPage(QtGui.QWizardPage, UserFormMixIn):
    setSigningUpStatus = QtCore.pyqtSignal([])

    def __init__(self, parent=None):
        super(RegisterUserPage, self).__init__(parent)

        # bind wizard page signals
        self.setSigningUpStatus.connect(
            self.set_status_validating)

        wizard = self.wizard()
        provider = wizard.get_provider() if wizard else None

        self.setTitle("User registration")
        self.setSubTitle(
            "Register a new user with provider %s." %
            provider)
        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        userNameLabel = QtGui.QLabel("User &name:")
        userNameLineEdit = QtGui.QLineEdit()
        userNameLineEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        userNameLabel.setBuddy(userNameLineEdit)

        # add regex validator
        usernameRe = QtCore.QRegExp(r"^[A-Za-z\d_]+$")
        userNameLineEdit.setValidator(
            QtGui.QRegExpValidator(usernameRe, self))
        self.userNameLineEdit = userNameLineEdit

        userPasswordLabel = QtGui.QLabel("&Password:")
        self.userPasswordLineEdit = QtGui.QLineEdit()
        self.userPasswordLineEdit.setEchoMode(
            QtGui.QLineEdit.Password)
        userPasswordLabel.setBuddy(self.userPasswordLineEdit)

        rememberPasswordCheckBox = QtGui.QCheckBox(
            "&Remember username and password.")
        rememberPasswordCheckBox.setChecked(True)

        self.registerField('userName*', self.userNameLineEdit)
        self.registerField('userPassword*', self.userPasswordLineEdit)
        self.registerField('rememberPassword', rememberPasswordCheckBox)

        layout = QtGui.QGridLayout()
        layout.setColumnMinimumWidth(0, 20)

        validationMsg = QtGui.QLabel("")
        validationMsg.setStyleSheet(ErrorLabelStyleSheet)

        self.validationMsg = validationMsg

        layout.addWidget(validationMsg, 0, 3)

        layout.addWidget(userNameLabel, 1, 0)
        layout.addWidget(self.userNameLineEdit, 1, 3)

        layout.addWidget(userPasswordLabel, 2, 0)
        layout.addWidget(self.userPasswordLineEdit, 2, 3)

        layout.addWidget(rememberPasswordCheckBox, 3, 3, 3, 4)
        self.setLayout(layout)

    # overwritten methods

    def initializePage(self):
        """
        inits wizard page
        """
        self.validationMsg.setText('')

    def validatePage(self):
        """
        validation
        we initialize the srp protocol register
        and try to register user. if error
        returned we write validation error msg
        above the form.
        """
        # the slot for this signal is not doing
        # what's expected. Investigate why,
        # right now we're not giving any feedback
        # to the user re. what's going on. The only
        # thing I can see as a workaround is setting
        # a low timeout.
        self.setSigningUpStatus.emit()

        username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()

        # XXX TODO -- remove debug info
        # XXX get from provider info
        # XXX enforce https
        # and pass a verify value

        signup = LeapSRPRegister(
            schema="http",
            provider="springbok",

            # debug -----
            #provider="localhost",
            #register_path="timeout",
            #port=8000
        )
        try:
            ok, req = signup.register_user(username, password)
        except socket.timeout:
            self.set_status_timeout()
            return False

        except requests.exceptions.ConnectionError as exc:
            logger.error(exc)
            self.set_status_connerror()
            return False

        if ok:
            return True

        # something went wrong.
        # not registered, let's catch what.
        # get timeout
        # ...
        if req.status_code == 500:
            self.set_status_server_500()
            return False

        validation_msgs = json.loads(req.content)
        logger.debug('validation errors: %s' % validation_msgs)
        errors = validation_msgs.get('errors', None)
        if errors and errors.get('login', None):
            # XXX this sometimes catch the blank username
            # but we're not allowing that (soon)
            self.set_status_invalid_username()
        else:
            self.set_status_unknown_error()
        return False

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('connecting')


class GlobalEIPSettings(QtGui.QWizardPage):
    """
    not in use right now
    """
    def __init__(self, parent=None):
        super(GlobalEIPSettings, self).__init__(parent)


class ConnectingPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(ConnectingPage, self).__init__(parent)

        self.setTitle("Connecting")
        self.setSubTitle('Connecting to provider.')


class LastPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(LastPage, self).__init__(parent)

        self.setTitle("Ready to go!")

        #self.setPixmap(
            #QtGui.QWizard.WatermarkPixmap,
            #QtGui.QPixmap(':/images/watermark2.png'))

        self.label = QtGui.QLabel()
        self.label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def initializePage(self):
        finishText = self.wizard().buttonText(
            QtGui.QWizard.FinishButton)
        finishText = finishText.replace('&', '')
        self.label.setText(
            "Click '<i>%s</i>' to end the wizard and start "
            "encrypting your connection." % finishText)


if __name__ == '__main__':
    # standalone test
    import sys
    import logging
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    app = QtGui.QApplication(sys.argv)
    wizard = FirstRunWizard()
    wizard.show()
    sys.exit(app.exec_())
