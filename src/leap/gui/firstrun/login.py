"""
LogIn Page, used inf First Run Wizard
"""
from PyQt4 import QtCore
from PyQt4 import QtGui

import requests

from leap.gui.firstrun.mixins import UserFormMixIn

from leap.gui.constants import APP_LOGO, FULL_USERNAME_REGEX
from leap.gui.styles import ErrorLabelStyleSheet


class LogInPage(QtGui.QWizardPage, UserFormMixIn):
    def __init__(self, parent=None):
        super(LogInPage, self).__init__(parent)

        self.setTitle("Log In")
        self.setSubTitle("Log in with your credentials.")

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        userNameLabel = QtGui.QLabel("User &name:")
        userNameLineEdit = QtGui.QLineEdit()
        userNameLineEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        userNameLabel.setBuddy(userNameLineEdit)

        # let's add regex validator
        usernameRe = QtCore.QRegExp(FULL_USERNAME_REGEX)
        userNameLineEdit.setValidator(
            QtGui.QRegExpValidator(usernameRe, self))
        self.userNameLineEdit = userNameLineEdit

        userPasswordLabel = QtGui.QLabel("&Password:")
        self.userPasswordLineEdit = QtGui.QLineEdit()
        self.userPasswordLineEdit.setEchoMode(
            QtGui.QLineEdit.Password)
        userPasswordLabel.setBuddy(self.userPasswordLineEdit)

        self.registerField('login_userName*', self.userNameLineEdit)
        self.registerField('login_userPassword*', self.userPasswordLineEdit)

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

        #self.registerField('is_login_wizard')

    def onUserNameEdit(self, *args):
        if self.initial_username_sample:
            self.userNameLineEdit.setText('')
            self.initial_username_sample = None

    # pagewizard methods

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        if wizard.is_provider_setup is True:
            next_ = 'connecting'
        if wizard.is_provider_setup is False:
            next_ = 'providersetup'
        return wizard.get_page_index(next_)

    def initializePage(self):
        self.userNameLineEdit.setText('username@provider.example.org')
        self.userNameLineEdit.cursorPositionChanged.connect(
            self.onUserNameEdit)
        self.initial_username_sample = True

    def validatePage(self):
        wizard = self.wizard()
        eipconfigchecker = wizard.eipconfigchecker()

        full_username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()
        if full_username.count('@') != 1:
            self.set_validation_status(
                "Username must be in the username@provider form.")
            return False

        username, domain = full_username.split('@')
        self.setField('provider_domain', domain)
        self.setField('login_userName', username)
        self.setField('login_userPassword', password)

        # Able to contact domain?
        # can get definition?
        # two-by-one
        try:
            eipconfigchecker.fetch_definition(domain=domain)

        # we're using requests here for all
        # the possible error cases that it catches.
        except requests.exceptions.ConnectionError as exc:
            self.set_validation_status(exc.message[1])
            return False
        except requests.exceptions.HTTPError as exc:
            self.set_validation_status(exc.message)
            return False
        wizard.set_providerconfig(
            eipconfigchecker.defaultprovider.config)

        # XXX validate user? or we leave that for later?
        # I think the best thing to do for that is
        # continue to provider setup page, and if
        # we catch authentication error there, redirect
        # again to this page (by clicking "next" to
        # come here).
        # Rationale is that we need to verify server certs
        # and so on.

        # mark that we came from login page.
        self.wizard().from_login = True

        return True
