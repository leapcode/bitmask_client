# -*- coding: utf-8 -*-
# wizard.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
First run wizard
"""
import os
import logging

from PySide import QtCore, QtGui
from functools import partial

from ui_wizard import Ui_Wizard
from leap.config.providerconfig import ProviderConfig
from leap.crypto.srpregister import SRPRegister
from leap.services.eip.providerbootstrapper import ProviderBootstrapper

logger = logging.getLogger(__name__)


class Wizard(QtGui.QWizard):
    """
    First run wizard to register a user and setup a provider
    """

    INTRO_PAGE = 0
    SELECT_PROVIDER_PAGE = 1
    PRESENT_PROVIDER_PAGE = 2
    SETUP_PROVIDER_PAGE = 3
    REGISTER_USER_PAGE = 4
    SERVICES_PAGE = 5
    FINISH_PAGE = 6

    WEAK_PASSWORDS = ("123456", "qweasd", "qwerty",
                      "password")

    BARE_USERNAME_REGEX = r"^[A-Za-z\d_]+$"

    def __init__(self, checker):
        QtGui.QWizard.__init__(self)

        self.ui = Ui_Wizard()
        self.ui.setupUi(self)

        self.setPixmap(QtGui.QWizard.LogoPixmap,
                       QtGui.QPixmap(":/images/leap-color-small.png"))

        self.QUESTION_ICON = QtGui.QPixmap(":/images/Emblem-question.png")
        self.ERROR_ICON = QtGui.QPixmap(":/images/Dialog-error.png")
        self.OK_ICON = QtGui.QPixmap(":/images/Dialog-accept.png")

        # Correspondence for services and their name to display
        self.SERVICE_DISPLAY = [
            self.tr("Encrypted Internet")
        ]
        self.SERVICE_CONFIG = [
            "openvpn"
        ]

        self._selected_services = set()

        self._show_register = False

        self.ui.grpCheckProvider.setVisible(False)
        self.ui.btnCheck.clicked.connect(self._check_provider)
        self.ui.lnProvider.returnPressed.connect(self._check_provider)

        self._provider_bootstrapper = ProviderBootstrapper()
        self._provider_bootstrapper.name_resolution.connect(
            self._name_resolution)
        self._provider_bootstrapper.https_connection.connect(
            self._https_connection)
        self._provider_bootstrapper.download_provider_info.connect(
            self._download_provider_info)

        self._provider_bootstrapper.download_ca_cert.connect(
            self._download_ca_cert)
        self._provider_bootstrapper.check_ca_fingerprint.connect(
            self._check_ca_fingerprint)
        self._provider_bootstrapper.check_api_certificate.connect(
            self._check_api_certificate)

        self._domain = None
        self._provider_config = ProviderConfig()

        self.currentIdChanged.connect(self._current_id_changed)

        self.ui.lblPassword.setEchoMode(QtGui.QLineEdit.Password)
        self.ui.lblPassword2.setEchoMode(QtGui.QLineEdit.Password)

        self.ui.lnProvider.textChanged.connect(
            self._enable_check)

        self.ui.lblUser.returnPressed.connect(
            self._focus_password)
        self.ui.lblPassword.returnPressed.connect(
            self._focus_second_password)
        self.ui.lblPassword2.returnPressed.connect(
            self._register)
        self.ui.btnRegister.clicked.connect(
            self._register)

        usernameRe = QtCore.QRegExp(self.BARE_USERNAME_REGEX)
        self.ui.lblUser.setValidator(
            QtGui.QRegExpValidator(usernameRe, self))

        self.page(self.REGISTER_USER_PAGE).setCommitPage(True)

        self._username = None
        self._password = None

        self._checker_thread = checker

        self.page(self.REGISTER_USER_PAGE).setButtonText(
            QtGui.QWizard.CommitButton, self.tr("&Next >"))
        self.page(self.FINISH_PAGE).setButtonText(
            QtGui.QWizard.FinishButton, self.tr("Connect"))

    def get_username(self):
        return self._username

    def get_password(self):
        return self._password

    def get_remember(self):
        return self.ui.chkRemember.isChecked()

    def get_services(self):
        return self._selected_services

    def _enable_check(self, text):
        self.ui.btnCheck.setEnabled(len(self.ui.lnProvider.text()) != 0)
        self._reset_provider_check()

    def _focus_password(self):
        """
        Focuses at the password lineedit for the registration page
        """
        self.ui.lblPassword.setFocus()

    def _focus_second_password(self):
        """
        Focuses at the second password lineedit for the registration page
        """
        self.ui.lblPassword2.setFocus()

    def _basic_password_checks(self, username, password, password2):
        """
        Performs basic password checks to avoid really easy passwords.

        @param username: username provided at the registrarion form
        @type username: str
        @param password: password from the registration form
        @type password: str
        @param password2: second password from the registration form
        @type password: str

        @return: returns True if all the checks pass, False otherwise
        @rtype: bool
        """
        message = None

        if message is None and password != password2:
            message = self.tr("Passwords don't match")

        if message is None and len(password) < 6:
            message = self.tr("Password too short")

        if message is None and password in self.WEAK_PASSWORDS:
            message = self.tr("Password too easy")

        if message is None and username == password:
            message = self.tr("Password equal to username")

        if message is not None:
            self._set_register_status(message, error=True)
            self._focus_password()
            return False

        return True

    def _register(self):
        """
        Performs the registration based on the values provided in the form
        """
        self.ui.btnRegister.setEnabled(False)

        username = self.ui.lblUser.text()
        password = self.ui.lblPassword.text()
        password2 = self.ui.lblPassword2.text()

        if self._basic_password_checks(username, password, password2):
            register = SRPRegister(provider_config=self._provider_config)
            register.registration_finished.connect(
                self._registration_finished)
            self._checker_thread.add_checks(
                [partial(register.register_user,
                         username.encode("utf8"),
                         password.encode("utf8"))])
            self._username = username
            self._password = password
            self._set_register_status(self.tr("Starting registration..."))
        else:
            self.ui.btnRegister.setEnabled(True)

    def _registration_finished(self, ok, req):
        if ok:
            self._set_register_status(self.tr("<font color='green'>"
                                              "<b>User registration OK. "
                                              "</b></font>"))
            self.ui.lblPassword2.clearFocus()
            self.ui.chkRemember.setEnabled(True)

            self.page(self.REGISTER_USER_PAGE).set_completed()
        else:
            old_username = self._username
            self._username = None
            self._password = None
            error_msg = self.tr("Unknown error")
            try:
                error_msg = req.json().get("errors").get("login")[0]
                if not error_msg.istitle():
                    error_msg = "%s %s" % (old_username, error_msg)
                self._set_register_status(error_msg)
            except:
                logger.error("Unknown error: %r" % (req.content,))
            self.ui.btnRegister.setEnabled(True)

    def _set_register_status(self, status, error=False):
        """
        Sets the status label in the registration page to status

        @param status: status message to display, can be HTML
        @type status: str
        """
        if error:
            status = "<font color='red'><b>%s</b></font>" % (status,)
        self.ui.lblRegisterStatus.setText(status)

    def _reset_provider_check(self):
        """
        Resets the UI for checking a provider. Also resets the domain
        in this object.
        """
        self.ui.lblNameResolution.setPixmap(None)
        self.ui.lblHTTPS.setPixmap(None)
        self.ui.lblProviderInfo.setPixmap(None)
        self.ui.lblProviderSelectStatus.setText("")
        self._domain = None
        self.button(QtGui.QWizard.NextButton).setEnabled(False)
        self.page(self.SELECT_PROVIDER_PAGE).set_completed(False)

    def _reset_provider_setup(self):
        """
        Resets the UI for setting up a provider.
        """
        self.ui.lblDownloadCaCert.setPixmap(None)
        self.ui.lblCheckCaFpr.setPixmap(None)
        self.ui.lblCheckApiCert.setPixmap(None)

    def _check_provider(self):
        """
        SLOT
        TRIGGERS:
          self.ui.btnCheck.clicked
          self.ui.lnProvider.returnPressed

        Starts the checks for a given provider
        """
        if len(self.ui.lnProvider.text()) == 0:
            return

        self.ui.grpCheckProvider.setVisible(True)
        self.ui.btnCheck.setEnabled(False)
        self.ui.lnProvider.setEnabled(False)
        self.button(QtGui.QWizard.BackButton).clearFocus()
        self._domain = self.ui.lnProvider.text()

        self.ui.lblNameResolution.setPixmap(self.QUESTION_ICON)
        self._provider_bootstrapper.run_provider_select_checks(
            self._checker_thread,
            self._domain)

    def _complete_task(self, data, label, complete=False, complete_page=-1):
        """
        Checks a task and completes a page if specified

        @param data: data as it comes from the bootstrapper thread for
        a specific check
        @type data: dict
        @param label: label that displays the status icon for a
        specific check that corresponds to the data
        @type label: QtGui.QLabel
        @param complete: if True, it completes the page specified,
        which must be of type WizardPage
        @type complete: bool
        @param complete_page: page id to complete
        @type complete_page: int
        """
        passed = data[self._provider_bootstrapper.PASSED_KEY]
        error = data[self._provider_bootstrapper.ERROR_KEY]
        if passed:
            label.setPixmap(self.OK_ICON)
            if complete:
                self.page(complete_page).set_completed()
                self.button(QtGui.QWizard.NextButton).setFocus()
        else:
            label.setPixmap(self.ERROR_ICON)
            logger.error(error)

    def _name_resolution(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.name_resolution

        Sets the status for the name resolution check
        """
        self._complete_task(data, self.ui.lblNameResolution)
        status = ""
        passed = data[self._provider_bootstrapper.PASSED_KEY]
        if not passed:
            status = self.tr("<font color='red'><b>Non-existent "
                             "provider</b></font>")
        self.ui.lblProviderSelectStatus.setText(status)
        self.ui.btnCheck.setEnabled(not passed)
        self.ui.lnProvider.setEnabled(not passed)
        self.ui.lblHTTPS.setPixmap(self.QUESTION_ICON)

    def _https_connection(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.https_connection

        Sets the status for the https connection check
        """
        self._complete_task(data, self.ui.lblHTTPS)
        status = ""
        passed = data[self._provider_bootstrapper.PASSED_KEY]
        if not passed:
            status = self.tr("<font color='red'><b>%s</b></font>") \
                % (data[self._provider_bootstrapper.ERROR_KEY])
            self.ui.lblProviderSelectStatus.setText(status)
        self.ui.btnCheck.setEnabled(not passed)
        self.ui.lnProvider.setEnabled(not passed)
        self.ui.lblProviderInfo.setPixmap(self.QUESTION_ICON)

    def _download_provider_info(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.download_provider_info

        Sets the status for the provider information download
        check. Since this check is the last of this set, it also
        completes the page if passed
        """
        if self._provider_config.load(os.path.join("leap",
                                                   "providers",
                                                   self._domain,
                                                   "provider.json")):
            self._complete_task(data, self.ui.lblProviderInfo,
                                True, self.SELECT_PROVIDER_PAGE)
        else:
            new_data = {
                self._provider_bootstrapper.PASSED_KEY: False,
                self._provider_bootstrapper.ERROR_KEY:
                self.tr("Unable to load provider configuration")
            }
            self._complete_task(new_data, self.ui.lblProviderInfo)

        status = ""
        if not data[self._provider_bootstrapper.PASSED_KEY]:
            status = self.tr("<font color='red'><b>Not a valid provider"
                             "</b></font>")
            self.ui.lblProviderSelectStatus.setText(status)
        self.ui.btnCheck.setEnabled(True)
        self.ui.lnProvider.setEnabled(True)

    def _download_ca_cert(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.download_ca_cert

        Sets the status for the download of the CA certificate check
        """
        self._complete_task(data, self.ui.lblDownloadCaCert)
        self.ui.lblCheckCaFpr.setPixmap(self.QUESTION_ICON)

    def _check_ca_fingerprint(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.check_ca_fingerprint

        Sets the status for the CA fingerprint check
        """
        self._complete_task(data, self.ui.lblCheckCaFpr)
        self.ui.lblCheckApiCert.setPixmap(self.QUESTION_ICON)

    def _check_api_certificate(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.check_api_certificate

        Sets the status for the API certificate check. Also finishes
        the provider bootstrapper thread since it's not needed anymore
        from this point on, unless the whole check chain is restarted
        """
        self._complete_task(data, self.ui.lblCheckApiCert,
                            True, self.SETUP_PROVIDER_PAGE)

    def _service_selection_changed(self, service, state):
        """
        SLOT
        TRIGGER: service_checkbox.stateChanged
        Adds the service to the state if the state is checked, removes
        it otherwise

        @param service: service to handle
        @type service: str
        @param state: state of the checkbox
        @type state: int
        """
        if state == QtCore.Qt.Checked:
            self._selected_services = \
                self._selected_services.union({service})
        else:
            self._selected_services = \
                self._selected_services.difference({service})

    def _populate_services(self):
        """
        Loads the services that the provider provides into the UI for
        the user to enable or disable
        """
        self.ui.grpServices.setTitle(
            self.tr("Services by %s") %
            (self._provider_config.get_name(),))

        for service in self._provider_config.get_services():
            try:
                checkbox = QtGui.QCheckBox(self)
                service_index = self.SERVICE_CONFIG.index(service)
                checkbox.setText(self.SERVICE_DISPLAY[service_index])
                self.ui.serviceListLayout.addWidget(checkbox)
                checkbox.stateChanged.connect(
                    partial(self._service_selection_changed, service))
                checkbox.setChecked(True)
            except ValueError:
                logger.error(
                    self.tr("Something went wrong while trying to "
                            "load service %s" % (service,)))

    def _current_id_changed(self, pageId):
        """
        SLOT
        TRIGGER: self.currentIdChanged

        Prepares the pages when they appear
        """
        if pageId == self.SELECT_PROVIDER_PAGE:
            self._reset_provider_check()
            self._enable_check("")

        if pageId == self.SETUP_PROVIDER_PAGE:
            self._reset_provider_setup()
            self.page(pageId).setSubTitle(self.tr("Gathering configuration "
                                                  "options for %s") %
                                          (self._provider_config
                                           .get_name(),))
            self.ui.lblDownloadCaCert.setPixmap(self.QUESTION_ICON)
            self._provider_bootstrapper.\
                run_provider_setup_checks(self._checker_thread,
                                          self._provider_config)

        if pageId == self.PRESENT_PROVIDER_PAGE:
            self.page(pageId).setSubTitle(self.tr("Services offered by %s") %
                                          (self._provider_config
                                           .get_name(),))

            lang = QtCore.QLocale.system().name()
            self.ui.lblProviderName.setText(
                "<b>%s</b>" %
                (self._provider_config.get_name(lang=lang),))
            self.ui.lblProviderURL.setText(
                "https://%s" % (self._provider_config.get_domain(),))
            self.ui.lblProviderDesc.setText(
                "<i>%s</i>" %
                (self._provider_config.get_description(lang=lang),))
            self.ui.lblProviderPolicy.setText(self._provider_config
                                              .get_enrollment_policy())

        if pageId == self.REGISTER_USER_PAGE:
            self.page(pageId).setSubTitle(self.tr("Register a new user with "
                                                  "%s") %
                                          (self._provider_config
                                           .get_name(),))

        if pageId == self.SERVICES_PAGE:
            self._populate_services()

    def nextId(self):
        """
        Sets the next page id for the wizard based on wether the user
        wants to register a new identity or uses an existing one
        """
        if self.currentPage() == self.page(self.INTRO_PAGE):
            self._show_register = self.ui.rdoRegister.isChecked()

        if self.currentPage() == self.page(self.SETUP_PROVIDER_PAGE):
            if self._show_register:
                return self.REGISTER_USER_PAGE
            else:
                return self.SERVICES_PAGE

        return QtGui.QWizard.nextId(self)
