"""
Register User Page, used in First Run Wizard
"""
import json
import logging
import socket

import requests

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui.firstrun.mixins import UserFormMixIn

logger = logging.getLogger(__name__)

from leap.base import auth
from leap.gui import styles
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
        self.do_confirm_next = False
        self.focused_field = False

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
        self.commitText("Sign up!")

    # commit button

    def commitText(self, text):
        # change "commit" button text
        self.setButtonText(
            QtGui.QWizard.CommitButton, text)

    @property
    def commitButton(self):
        return self.wizard().button(QtGui.QWizard.CommitButton)

    def commitFocus(self):
        self.commitButton.setFocus()

    def disableCommitButton(self):
        self.commitButton.setDisabled(True)

    def disableFields(self):
        for field in (self.userNameLineEdit,
                      self.userPasswordLineEdit,
                      self.userPassword2LineEdit):
            field.setDisabled(True)

    # error painting

    def markRedAndGetFocus(self, field):
        field.setStyleSheet(styles.ErrorLineEdit)
        if not self.focused_field:
            self.focused_field = True
            field.setFocus(QtCore.Qt.OtherFocusReason)

    def markRegular(self, field):
        field.setStyleSheet(styles.RegularLineEdit)

    def populateErrors(self):
        def showerr(text):
            self.validationMsg.setText(text)
            err_lower = text.lower()
            if "username" in err_lower:
                self.markRedAndGetFocus(
                    self.userNameLineEdit)
            if "password" in err_lower:
                self.markRedAndGetFocus(
                    self.userPasswordLineEdit)

        def unmarkred():
            for field in (self.userNameLineEdit,
                          self.userPasswordLineEdit,
                          self.userPassword2LineEdit):
                self.markRegular(field)

        errors = self.wizard().get_validation_error(
            self.current_page)
        if errors:
            bad_str = getattr(self, 'bad_string', None)
            cur_str = self.userNameLineEdit.text()
            #prev_er = getattr(self, 'prevalidation_error', None)

            if bad_str is None:
                # first time we fall here.
                # save the current bad_string value
                self.bad_string = cur_str
                showerr(errors)
            else:
                #if prev_er:
                    #showerr(prev_er)
                    #return
                # not the first time
                if cur_str == bad_str:
                    showerr(errors)
                else:
                    self.focused_field = False
                    showerr('')
                    unmarkred()
        else:
            # no errors
            self.focused_field = False
            unmarkred()

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

    def _do_checks(self):
        """
        generator that yields actual checks
        that are executed in a separate thread
        """
        provider = self.field('provider_domain')
        username = self.userNameLineEdit.text()
        password = self.userPasswordLineEdit.text()
        password2 = self.userPassword2LineEdit.text()

        def checkpass():
            # we better have here
            # some call to a password checker...
            # to assess strenght and avoid silly stuff.

            if password != password2:
                return self.fail(self.tr('Password does not match..'))

            if len(password) < 6:
                #self.set_prevalidation_error('Password too short.')
                return self.fail(self.tr('Password too short.'))

            if password == "123456":
                # joking, but not too much.
                #self.set_prevalidation_error('Password too obvious.')
                return self.fail(self.tr('Password too obvious.'))

            # go
            return True

        yield(("head_sentinel", 0), checkpass)

        # XXX should emit signal for .show the frame!
        # XXX HERE!

        ##################################################
        # 1) register user
        ##################################################

        # show the frame before going on...
        QtCore.QMetaObject.invokeMethod(
            self, "showStepsFrame")

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
                return self.fail(
                    self.tr("Error connecting to provider (timeout)"))

            except requests.exceptions.ConnectionError as exc:
                logger.error(exc.message)
                return self.fail(
                    self.tr('Error Connecting to provider (connerr).'))
            except Exception as exc:
                return self.fail(exc.message)

            # XXX check for != OK instead???

            if req.status_code in (404, 500):
                return self.fail(
                    self.tr(
                        "Error during registration (%s)") % req.status_code)

            validation_msgs = json.loads(req.content)
            errors = validation_msgs.get('errors', None)
            logger.debug('validation errors: %s' % validation_msgs)

            if errors and errors.get('login', None):
                # XXX this sometimes catch the blank username
                # but we're not allowing that (soon)
                return self.fail(
                    self.tr('Username not available.'))

        logger.debug('registering user')
        yield(("registering with provider", 40), register)

        self.set_done()
        yield(("end_sentinel", 0), lambda: None)

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
            self.commitText('Connect!')
            self.commitFocus()
            self.green_validation_status()
            self.do_confirm_next = True

    def green_validation_status(self):
        val = self.validationMsg
        val.setText(self.tr('Registration succeeded!'))
        val.setStyleSheet(styles.GreenLineEdit)

    def reset_validation_status(self):
        """
        empty the validation msg
        and clean the inline validation widget.
        """
        self.validationMsg.setText('')
        self.steps.removeAllSteps()
        self.clearTable()

    # pagewizard methods

    def validatePage(self):
        """
        if not register done, do checks.
        if done, wait for click.
        """
        self.disableCommitButton()
        self.cleanup_errormsg()
        self.clean_wizard_errors(self.current_page)

        # After a successful validation
        # (ie, success register with server)
        # we change the commit button text
        # and set this flag to True.
        if self.do_confirm_next:
            return True

        if not self.is_done():
            # calls checks, which after successful
            # execution will call on_checks_validation_ready
            self.reset_validation_status()
            self.do_checks()

        return self.is_done()

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
        self.valFrame.hide()

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        # XXX this should be called connect
        return wizard.get_page_index('signupvalidation')
