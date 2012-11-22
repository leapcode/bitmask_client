"""
Register User Page, used in First Run Wizard
"""
import logging
import socket

import requests

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui.firstrun.mixins import UserFormMixIn

logger = logging.getLogger(__name__)

from leap.base import auth
from leap.gui.constants import APP_LOGO, BARE_USERNAME_REGEX
from leap.gui.progress import InlineValidationPage
from leap.gui.styles import ErrorLabelStyleSheet


class RegisterUserPage(InlineValidationPage, UserFormMixIn):

    def __init__(self, parent=None):

        super(RegisterUserPage, self).__init__(parent)
        self.current_page = "signup"

        self.setTitle(self.tr("Sign Up"))
        # subtitle is set in the initializePage

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        # commit page means there's no way back after this...
        # XXX should change the text on the "commit" button...
        self.setCommitPage(True)

        self.setupSteps()
        self.setupUI()

    def setupUI(self):
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
        self.registerField('userPassword2*', self.userPassword2LineEdit)

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

        # add validation frame
        self.setupValidationFrame()
        layout.addWidget(self.valFrame, 5, 2, 5, 2)
        self.valFrame.hide()

        self.setLayout(layout)

        # change "commit" button text
        self.setButtonText(
            QtGui.QWizard.CommitButton, "Sign up!")

    # pagewizard methods

    def populateErrors(self):
        # XXX could move this to ValidationMixin
        # used in providerselect too

        errors = self.wizard().get_validation_error(
            self.current_page)
        if errors:
            bad_str = getattr(self, 'bad_string', None)
            cur_str = self.userNameLineEdit.text()
            showerr = self.validationMsg.setText
            prev_er = getattr(self, 'prevalidation_error', None)

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
        super(RegisterUserPage, self).paintEvent(event)
        self.populateErrors()

    def validatePage(self):
        """
        we only pre-validate here password weakness
        stuff, or any other client side validation
        that we think of.
        real server validation is made on next page,
        and if any errors are thrown there we come back
        and re-display the validation label.
        """
        # calls checks, which after successful
        # execution will call on_checks_validation_ready
        self.do_checks()
        return self.is_done()

    def _do_checks(self):
        """
        generator that yields actual checks
        that are executed in a separate thread
        """
        wizard = self.wizard()
        curpage = self.current_page
        senderr = lambda err: wizard.set_validation_error(curpage, err)

        provider = self.field('provider_domain')
        username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()
        password2 = self.userPassword2LineEdit.text()

        def fail():
            self.set_undone()
            return False

        def checkpass():
            # we better have here
            # some call to a password checker...
            # to assess strenght and avoid silly stuff.

            if password != password2:
                msg = self.tr('Password does not match..')
                senderr(msg)
                return fail()

            if len(password) < 6:
                #self.set_prevalidation_error('Password too short.')
                msg = self.tr('Password too short.')
                senderr(msg)
                return fail()

            if password == "123456":
                # joking, but not too much.
                #self.set_prevalidation_error('Password too obvious.')
                msg = self.tr('Password too obvious.')
                senderr(msg)
                return fail()

            # go
            return True

        yield(("head_sentinel", 0), checkpass)

        # XXX should emit signal for .show the frame!
        # XXX HERE!

        ##################################################
        # 1) register user
        ##################################################

        def register():
            # XXX FIXME!
            verify = False

            signup = auth.LeapSRPRegister(
                schema="https",
                provider=provider,
                verify=verify)
            try:
                ok, req = signup.register_user(
                    username, password)

            except socket.timeout:
                msg = self.tr("Error connecting to provider (timeout)")
                senderr(msg)
                return fail()

            except requests.exceptions.ConnectionError as exc:
                logger.error(exc.message)
                msg = self.tr('Error Connecting to provider (connerr).')
                senderr(msg)
                return fail()

            # XXX check for != OK instead???

            if req.status_code in (404, 500):
                msg = self.tr(
                    "Error during registration (%s)") % req.status_code
                return fail()

            validation_msgs = json.loads(req.content)
            errors = validation_msgs.get('errors', None)
            logger.debug('validation errors: %s' % validation_msgs)

            if errors and errors.get('login', None):
                # XXX this sometimes catch the blank username
                # but we're not allowing that (soon)
                msg = self.tr('Username not available.')
                senderr(msg)
                return fail()

        logger.debug('registering user')
        yield(("registering with provider", 40), register)

        # set_done??
        self.set_done()
        yield(("end_sentinel", 0), lambda: None)

    def on_checks_validation_ready(self):

        if self.is_done():
            self.cleanup_errormsg()
            self.go_next()

    def initializePage(self):
        """
        inits wizard page
        """
        provider = self.field('provider_domain')
        self.setSubTitle(
            self.tr("Register a new user with provider %s.") %
            provider)
        self.validationMsg.setText('')
        self.userPassword2LineEdit.setText('')

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('signupvalidation')
