"""
Register User Page, used in First Run Wizard
"""
import json
import logging
import socket

import requests

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.base import auth
from leap.gui.firstrun.mixins import UserFormMixIn

logger = logging.getLogger(__name__)

from leap.gui.constants import APP_LOGO, BARE_USERNAME_REGEX
from leap.gui.styles import ErrorLabelStyleSheet


class RegisterUserPage(QtGui.QWizardPage, UserFormMixIn):
    setSigningUpStatus = QtCore.pyqtSignal([])

    def __init__(self, parent=None):
        super(RegisterUserPage, self).__init__(parent)

        # bind wizard page signals
        self.setSigningUpStatus.connect(
            lambda: self.set_validation_status(
                'validating'))

        self.setTitle("Sign Up")

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        userNameLabel = QtGui.QLabel("User &name:")
        userNameLineEdit = QtGui.QLineEdit()
        userNameLineEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        userNameLabel.setBuddy(userNameLineEdit)

        # let's add regex validator
        usernameRe = QtCore.QRegExp(BARE_USERNAME_REGEX)
        userNameLineEdit.setValidator(
            QtGui.QRegExpValidator(usernameRe, self))
        self.userNameLineEdit = userNameLineEdit

        userPasswordLabel = QtGui.QLabel("&Password:")
        self.userPasswordLineEdit = QtGui.QLineEdit()
        self.userPasswordLineEdit.setEchoMode(
            QtGui.QLineEdit.Password)
        userPasswordLabel.setBuddy(self.userPasswordLineEdit)

        userPassword2Label = QtGui.QLabel("Password (again):")
        self.userPassword2LineEdit = QtGui.QLineEdit()
        self.userPassword2LineEdit.setEchoMode(
            QtGui.QLineEdit.Password)
        userPassword2Label.setBuddy(self.userPassword2LineEdit)

        rememberPasswordCheckBox = QtGui.QCheckBox(
            "&Remember username and password.")
        rememberPasswordCheckBox.setChecked(True)

        self.registerField('userName*', self.userNameLineEdit)
        self.registerField('userPassword*', self.userPasswordLineEdit)

        # XXX missing password confirmation
        # XXX validator!

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
        layout.addWidget(userPassword2Label, 3, 0)
        layout.addWidget(self.userPasswordLineEdit, 2, 3)
        layout.addWidget(self.userPassword2LineEdit, 3, 3)
        layout.addWidget(rememberPasswordCheckBox, 4, 3, 4, 4)
        self.setLayout(layout)

    # overwritten methods

    def initializePage(self):
        """
        inits wizard page
        """
        provider = self.field('provider_domain')
        self.setSubTitle(
            "Register a new user with provider %s." %
            provider)
        self.validationMsg.setText('')
        self.userPassword2LineEdit.setText('')

    def validatePage(self):
        """
        validation
        we initialize the srp protocol register
        and try to register user. if error
        returned we write validation error msg
        above the form.
        """
        wizard = self.wizard()

        self.setSigningUpStatus.emit()

        username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()
        password2 = self.userPassword2LineEdit.text()

        # we better have here
        # some call to a password checker...
        # to assess strenght and avoid silly stuff.

        if password != password2:
            self.set_validation_status('Password does not match.')
            return False

        if len(password) < 6:
            self.set_validation_status('Password too short.')
            return False

        if password == "123456":
            # joking
            self.set_validation_status('Password too obvious.')
            return False

        domain = self.field('provider_domain')

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

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('connecting')
