"""
LogIn Page, used inf First Run Wizard
"""
from PyQt4 import QtCore
from PyQt4 import QtGui

import requests

from leap.base import auth
from leap.gui.firstrun.mixins import UserFormMixIn
from leap.gui.progress import InlineValidationPage
from leap.gui import styles

from leap.gui.constants import APP_LOGO, FULL_USERNAME_REGEX


class LogInPage(InlineValidationPage, UserFormMixIn):  # InlineValidationPage

    def __init__(self, parent=None):

        super(LogInPage, self).__init__(parent)
        self.current_page = "login"

        self.setTitle(self.tr("Log In"))
        self.setSubTitle(self.tr("Log in with your credentials"))
        self.current_page = "login"

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        self.setupSteps()
        self.setupUI()

        self.do_confirm_next = False

    def setupUI(self):
        userNameLabel = QtGui.QLabel(self.tr("User &name:"))
        userNameLineEdit = QtGui.QLineEdit()
        userNameLineEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        userNameLabel.setBuddy(userNameLineEdit)

        # let's add regex validator
        usernameRe = QtCore.QRegExp(FULL_USERNAME_REGEX)
        userNameLineEdit.setValidator(
            QtGui.QRegExpValidator(usernameRe, self))

        #userNameLineEdit.setPlaceholderText(
            #'username@provider.example.org')
        self.userNameLineEdit = userNameLineEdit

        userPasswordLabel = QtGui.QLabel(self.tr("&Password:"))
        self.userPasswordLineEdit = QtGui.QLineEdit()
        self.userPasswordLineEdit.setEchoMode(
            QtGui.QLineEdit.Password)
        userPasswordLabel.setBuddy(self.userPasswordLineEdit)

        self.registerField('login_userName*', self.userNameLineEdit)
        self.registerField('login_userPassword*', self.userPasswordLineEdit)

        layout = QtGui.QGridLayout()
        layout.setColumnMinimumWidth(0, 20)

        validationMsg = QtGui.QLabel("")
        validationMsg.setStyleSheet(styles.ErrorLabelStyleSheet)
        self.validationMsg = validationMsg

        layout.addWidget(validationMsg, 0, 3)
        layout.addWidget(userNameLabel, 1, 0)
        layout.addWidget(self.userNameLineEdit, 1, 3)
        layout.addWidget(userPasswordLabel, 2, 0)
        layout.addWidget(self.userPasswordLineEdit, 2, 3)

        # add validation frame
        self.setupValidationFrame()
        layout.addWidget(self.valFrame, 4, 2, 4, 2)
        self.valFrame.hide()

        self.nextText(self.tr("Log in"))
        self.setLayout(layout)

        #self.registerField('is_login_wizard')

    # actual checks

    def _do_checks(self):

        full_username = self.userNameLineEdit.text()
        ###########################
        # 0) check user@domain form
        ###########################

        def checkusername():
            if full_username.count('@') != 1:
                return self.fail(
                    self.tr(
                        "Username must be in the username@provider form."))
            else:
                return True

        yield(("head_sentinel", 0), checkusername)

        username, domain = full_username.split('@')
        password = self.userPasswordLineEdit.text()

        # We try a call to an authenticated
        # page here as a mean to catch
        # srp authentication errors while
        wizard = self.wizard()
        eipconfigchecker = wizard.eipconfigchecker(domain=domain)

        ########################
        # 1) try name resolution
        ########################
        # show the frame before going on...
        QtCore.QMetaObject.invokeMethod(
            self, "showStepsFrame")

        # Able to contact domain?
        # can get definition?
        # two-by-one
        def resolvedomain():
            try:
                eipconfigchecker.fetch_definition(domain=domain)

            # we're using requests here for all
            # the possible error cases that it catches.
            except requests.exceptions.ConnectionError as exc:
                return self.fail(exc.message[1])
            except requests.exceptions.HTTPError as exc:
                return self.fail(exc.message)
            except Exception as exc:
                # XXX get catchall error msg
                return self.fail(
                    exc.message)
            else:
                return True

        yield((self.tr("Resolving domain name"), 20), resolvedomain)

        wizard.set_providerconfig(
            eipconfigchecker.defaultprovider.config)

        ########################
        # 2) do authentication
        ########################
        credentials = username, password
        pCertChecker = wizard.providercertchecker(
            domain=domain)

        def validate_credentials():
            #################
            # FIXME #BUG #638
            verify = False

            try:
                pCertChecker.download_new_client_cert(
                    credentials=credentials,
                    verify=verify)

            except auth.SRPAuthenticationError as exc:
                return self.fail(
                    self.tr("Authentication error: %s" % exc.message))

            except Exception as exc:
                return self.fail(exc.message)

            else:
                return True

        yield(('Validating credentials', 60), validate_credentials)

        self.set_done()
        yield(("end_sentinel", 100), lambda: None)

    def green_validation_status(self):
        val = self.validationMsg
        val.setText(self.tr('Credentials validated.'))
        val.setStyleSheet(styles.GreenLineEdit)

    def on_checks_validation_ready(self):
        """
        after checks
        """
        if self.is_done():
            self.disableFields()
            self.cleanup_errormsg()
            self.clean_wizard_errors(self.current_page)
            # make the user confirm the transition
            # to next page.
            self.nextText('&Next')
            self.nextFocus()
            self.green_validation_status()
            self.do_confirm_next = True

    # ui update

    def nextText(self, text):
        self.setButtonText(
            QtGui.QWizard.NextButton, text)

    def nextFocus(self):
        self.wizard().button(
            QtGui.QWizard.NextButton).setFocus()

    def disableNextButton(self):
        self.wizard().button(
            QtGui.QWizard.NextButton).setDisabled(True)

    def onUserNamePositionChanged(self, *args):
        if self.initial_username_sample:
            self.userNameLineEdit.setText('')
            # XXX set regular color
            self.initial_username_sample = None

    def onUserNameTextChanged(self, *args):
        if self.initial_username_sample:
            k = args[0][-1]
            self.initial_username_sample = None
            self.userNameLineEdit.setText(k)

    def disableFields(self):
        for field in (self.userNameLineEdit,
                      self.userPasswordLineEdit):
            field.setDisabled(True)

    def populateErrors(self):
        # XXX could move this to ValidationMixin
        # used in providerselect and register too

        errors = self.wizard().get_validation_error(
            self.current_page)
        showerr = self.validationMsg.setText

        if errors:
            bad_str = getattr(self, 'bad_string', None)
            cur_str = self.userNameLineEdit.text()

            if bad_str is None:
                # first time we fall here.
                # save the current bad_string value
                self.bad_string = cur_str
                showerr(errors)
            else:
                # not the first time
                if cur_str == bad_str:
                    showerr(errors)
                else:
                    self.focused_field = False
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

    # pagewizard methods

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
        username = self.userNameLineEdit
        username.setText('username@provider.example.org')
        username.cursorPositionChanged.connect(
            self.onUserNamePositionChanged)
        username.textChanged.connect(
            self.onUserNameTextChanged)
        self.initial_username_sample = True
        self.validationMsg.setText('')
        self.valFrame.hide()

    def reset_validation_status(self):
        """
        empty the validation msg
        and clean the inline validation widget.
        """
        self.validationMsg.setText('')
        self.steps.removeAllSteps()
        self.clearTable()

    def validatePage(self):
        """
        if not register done, do checks.
        if done, wait for click.
        """
        self.disableNextButton()
        self.cleanup_errormsg()
        self.clean_wizard_errors(self.current_page)

        if self.do_confirm_next:
            full_username = self.userNameLineEdit.text()
            password = self.userPasswordLineEdit.text()
            username, domain = full_username.split('@')
            self.setField('provider_domain', domain)
            self.setField('login_userName', username)
            self.setField('login_userPassword', password)
            self.wizard().from_login = True

            return True

        if not self.is_done():
            self.reset_validation_status()
            self.do_checks()

        return self.is_done()
