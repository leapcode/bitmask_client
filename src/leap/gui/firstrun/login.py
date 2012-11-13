"""
LogIn Page, used inf First Run Wizard
"""
from PyQt4 import QtCore
from PyQt4 import QtGui

#import requests

from leap.gui.firstrun.mixins import UserFormMixIn

from leap.gui.constants import APP_LOGO, FULL_USERNAME_REGEX
from leap.gui.styles import ErrorLabelStyleSheet


class LogInPage(QtGui.QWizardPage, UserFormMixIn):
    def __init__(self, parent=None):
        super(LogInPage, self).__init__(parent)

        self.setTitle("Log In")
        self.setSubTitle("Log in with your credentials.")
        self.current_page = "login"

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

    #### begin possible refactor

    def populateErrors(self):
        # XXX could move this to ValidationMixin
        # used in providerselect and register too

        errors = self.wizard().get_validation_error(
            self.current_page)
        prev_er = getattr(self, 'prevalidation_error', None)
        showerr = self.validationMsg.setText

        if not errors and prev_er:
            showerr(prev_er)
            return

        if errors:
            bad_str = getattr(self, 'bad_string', None)
            cur_str = self.userNameLineEdit.text()

            if bad_str is None:
                # first time we fall here.
                # save the current bad_string value
                self.bad_string = cur_str
                showerr(errors)
            else:
                if prev_er:
                    showerr(prev_er)
                    return
                # not the first time
                if cur_str == bad_str:
                    showerr(errors)
                else:
                    showerr('')

    def cleanup_errormsg(self):
        """
        we reset bad_string to None
        should be called before leaving the page
        """
        self.bad_string = None

    def paintEvent(self, event):
        """
        we hook our populate errors
        on paintEvent because we need it to catch
        when user enters the page coming from next,
        and initializePage does not cover that case.
        Maybe there's a better event to hook upon.
        """
        super(LogInPage, self).paintEvent(event)
        self.populateErrors()

    def set_prevalidation_error(self, error):
        self.prevalidation_error = error

    #### end possible refactor

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        if wizard.is_provider_setup is False:
            next_ = 'providersetupvalidation'
        if wizard.is_provider_setup is True:
            # XXX bad name, ok, gonna change that
            next_ = 'signupvalidation'
        return wizard.get_page_index(next_)

    def initializePage(self):
        super(LogInPage, self).initializePage()
        self.userNameLineEdit.setText('username@provider.example.org')
        self.userNameLineEdit.cursorPositionChanged.connect(
            self.onUserNameEdit)
        self.initial_username_sample = True

    def validatePage(self):
        #wizard = self.wizard()
        #eipconfigchecker = wizard.eipconfigchecker()

        full_username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()
        if full_username.count('@') != 1:
            self.set_prevalidation_error(
                "Username must be in the username@provider form.")
            return False

        username, domain = full_username.split('@')
        self.setField('provider_domain', domain)
        self.setField('login_userName', username)
        self.setField('login_userPassword', password)

        ####################################################
        # Validation logic:
        # move to provider setup page
        ####################################################
        # Able to contact domain?
        # can get definition?
        # two-by-one
        #try:
            #eipconfigchecker.fetch_definition(domain=domain)
#
        # we're using requests here for all
        # the possible error cases that it catches.
        #except requests.exceptions.ConnectionError as exc:
            #self.set_validation_status(exc.message[1])
            #return False
        #except requests.exceptions.HTTPError as exc:
            #self.set_validation_status(exc.message)
            #return False
        #wizard.set_providerconfig(
            #eipconfigchecker.defaultprovider.config)
        ####################################################

        # XXX I think this is not needed
        # since we're also checking for the is_signup field.
        self.wizard().from_login = True

        # some cleanup before we leave the page
        self.cleanup_errormsg()

        return True
