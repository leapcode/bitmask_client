#!/usr/bin/env python
import logging

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.crypto import leapkeyring
from leap.gui import mainwindow_rc

logger = logging.getLogger(__name__)

APP_LOGO = ':/images/leap-color-small.png'

# registration ######################
# move to base/
import binascii

import requests
import srp


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
        req = self.session.post(uri, data=user_data)
        logger.debug(req)
        logger.debug('user_data: %s', user_data)
        #logger.debug('response: %s', req.text)
        # we catch it in the form
        req.raise_for_status()
        return True

######################################

ErrorLabelStyleSheet = """
QLabel { color: red;
         font-weight: bold}
"""


class FirstRunWizard(QtGui.QWizard):
    def __init__(
            self, parent=None, providers=None,
            success_cb=None):
        super(FirstRunWizard, self).__init__(
            parent,
            QtCore.Qt.WindowStaysOnTopHint)

        # XXX hardcoded for tests
        if not providers:
            providers = ('springbok',)
        self.providers = providers

        # success callback
        self.success_cb = success_cb

        self.addPage(IntroPage())
        self.addPage(SelectProviderPage(providers=providers))

        self.addPage(RegisterUserPage(wizard=self))
        #self.addPage(GlobalEIPSettings())
        self.addPage(LastPage())

        self.setPixmap(
            QtGui.QWizard.BannerPixmap,
            QtGui.QPixmap(':/images/banner.png'))
        self.setPixmap(
            QtGui.QWizard.BackgroundPixmap,
            QtGui.QPixmap(':/images/background.png'))

        self.setWindowTitle("First Run Wizard")

        # TODO: set style for MAC / windows ...
        #self.setWizardStyle()

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
        password = self.field('userPassword')
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

        leapkeyring.leap_set_password(username, password, seed=seed)

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
            "main window of the Leap App.")

        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


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


class RegisterUserPage(QtGui.QWizardPage):
    def __init__(self, parent=None, wizard=None):
        super(RegisterUserPage, self).__init__(parent)

        # XXX check for no wizard pased
        # getting provider from previous step
        provider = wizard.get_provider()

        self.setTitle("User registration")
        self.setSubTitle(
            "Register a new user with provider %s." %
            provider)
        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        rememberPasswordCheckBox = QtGui.QCheckBox(
            "&Remember password.")
        rememberPasswordCheckBox.setChecked(True)

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

        self.registerField('userName', self.userNameLineEdit)
        self.registerField('userPassword', self.userPasswordLineEdit)
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

    def reset_validation_status(self):
        """
        empty the validation msg
        """
        self.validationMsg.setText('')

    def set_status_validating(self):
        """
        set validation msg to 'registering...'
        """
        # XXX  this is not shown,
        # I guess it is because there is no delay...
        self.validationMsg.setText('registering...')

    def set_status_invalid_username(self):
        """
        set validation msg to
        not available user
        """
        self.validationMsg.setText('Username not available.')

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
        self.set_status_validating()
        # could move to status box maybe...

        username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()

        # XXX TODO -- remove debug info
        # XXX get from provider info
        # XXX enforce https
        # and pass a verify value

        signup = LeapSRPRegister(
            schema="http",
            #provider="localhost",
            provider="springbok",
            #port=8000
        )
        try:
            valid = signup.register_user(username, password)
        except requests.exceptions.HTTPError:
            valid = False
            # TODO catch 404, or other errors...
            self.set_status_invalid_username()

        return True if valid is True else False


class GlobalEIPSettings(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(GlobalEIPSettings, self).__init__(parent)


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
