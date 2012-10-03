#!/usr/bin/env python
# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4 import QtGui

# XXX change and use some other stuff.
import firstrunwizard_rc


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

    def accept(self):
        print 'chosen provider: ', self.get_provider()
        print 'username: ', self.field('userName')
        print 'password: ', self.field('userPassword')
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
        self.userNameLineEdit = QtGui.QLineEdit()
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

        layout.addWidget(userNameLabel, 0, 0)
        layout.addWidget(self.userNameLineEdit, 0, 3)

        layout.addWidget(userPasswordLabel, 1, 0)
        layout.addWidget(self.userPasswordLineEdit, 1, 3)

        layout.addWidget(rememberPasswordCheckBox, 2, 3, 2, 4)
        self.setLayout(layout)

        # XXX how to validatioN ----

    def initializePage(self):
        pass


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
