#!/usr/bin/env python
# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4 import QtGui

# XXX change and use some other stuff.
import firstrunwizard_rc

# registration ######################
# move to base/

import requests
import srp


class LeapSRPRegister(object):

    def __init__(self,
                 schema="https",
                 provider=None,
                 port=None,
                 register_path="users.json",
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
        uri = "%s://%s:%s/%s" % (
            self.schema,
            self.provider,
            self.port,
            self.register_path)
        return uri

    def register_user(self, username, password, keep=False):
        salt, vkey = self.srp.create_salted_verification_key(
            username,
            password,
            self.HASHFUN,
            self.NG)

        user_data = {
            'login': username,
            'password_verifier': vkey,
            'password_salt': salt}

        uri = self.get_registration_uri()
        print 'post to uri: %s' % uri
        # XXX get self.method
        req = self.session.post(uri, data=user_data)
        print req
        req.raise_for_status()
        return True

######################################

ErrorLabelStyleSheet = """
QLabel { color: red;
         font-weight: bold}
"""


class FirstRunWizard(QtGui.QWizard):
    def __init__(self, parent=None, providers=None):
        super(FirstRunWizard, self).__init__(parent)

        if not providers:
            providers = ('springbok',)
        self.providers = providers

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

    def accept(self):
        print 'chosen provider: ', self.get_provider()
        print 'username: ', self.field('userName')
        #print 'password: ', self.field('userPassword')
        print 'remember password: ', self.field('rememberPassword')
        super(FirstRunWizard, self).accept()
        # XXX we should emit a completed signal here...
        # and pass a dict with options
        # XXX unless one exists by default...

    def get_provider(self):
        provider = self.field('provider_index')
        return self.providers[provider]


class IntroPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)

        self.setTitle("First run wizard.")
        self.setPixmap(
            QtGui.QWizard.WatermarkPixmap,
            QtGui.QPixmap(':/images/watermark1.png'))

        label = QtGui.QLabel(
            "Now we will guide you through "
            "some configuration that is needed before you "
            "connect for the first time.<br><br>"
            "If you ever need to modify this options again, "
            "you can access from the '<i>Settings</i>' menu in the "
            "main window of the app.")
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
            QtGui.QPixmap(':/images/logo1.png'))

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
        # XXX save as self.provider,
        # we will need it for validating page
        provider = wizard.get_provider()

        self.setTitle("User registration")
        self.setSubTitle(
            "Register a new user with provider %s." %
            provider)
        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(':/images/logo2.png'))

        rememberPasswordCheckBox = QtGui.QCheckBox(
            "&Remember password.")
        rememberPasswordCheckBox.setChecked(True)

        userNameLabel = QtGui.QLabel("User &name:")
        userNameLineEdit = QtGui.QLineEdit()
        userNameLineEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        self.userNameLineEdit = userNameLineEdit
        userNameLabel.setBuddy(self.userNameLineEdit)

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
        print 'validating page...'
        self.set_status_validating()
        # could move to status box maybe...

        username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()

        # XXX TODO -- remove debug info
        # XXX get from provider info

        signup = LeapSRPRegister(
            schema="http",
            #provider="springbok"
            provider="localhost",
            port=8000
        )
        try:
            valid = signup.register_user(username, password)
        except requests.exceptions.HTTPError:
            valid = False
            # XXX use QString
            # XXX line wrap
            # XXX Raise Validation Labels...
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
        self.setPixmap(
            QtGui.QWizard.WatermarkPixmap,
            QtGui.QPixmap(':/images/watermark2.png'))

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

    import sys

    app = QtGui.QApplication(sys.argv)
    wizard = FirstRunWizard()
    wizard.show()
    sys.exit(app.exec_())
