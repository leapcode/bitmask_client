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

from ui_wizard import Ui_Wizard
from leap.config.providerconfig import ProviderConfig
from leap.crypto.srpregister import SRPRegister
from leap.services.eip.providerbootstrapper import ProviderBootstrapper
from leap.services.eip.eipbootstrapper import EIPBootstrapper

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
    SETUP_EIP_PAGE = 5
    FINISH_PATH = 6

    WEAK_PASSWORDS = ("1234", "12345", "123456",
                      "password")

    def __init__(self):
        QtGui.QWizard.__init__(self)

        self.ui = Ui_Wizard()
        self.ui.setupUi(self)

        self.QUESTION_ICON = QtGui.QPixmap(":/images/Emblem-question.png")
        self.ERROR_ICON = QtGui.QPixmap(":/images/Dialog-error.png")
        self.OK_ICON = QtGui.QPixmap(":/images/Dialog-accept.png")

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

        self._eip_bootstrapper = EIPBootstrapper()

        self._eip_bootstrapper.download_config.connect(
            self._download_eip_config)
        self._eip_bootstrapper.download_client_certificate.connect(
            self._download_client_certificate)

        self._domain = None
        self._provider_config = ProviderConfig()

        self.currentIdChanged.connect(self._current_id_changed)

        self.ui.lblPassword.setEchoMode(QtGui.QLineEdit.Password)
        self.ui.lblPassword2.setEchoMode(QtGui.QLineEdit.Password)

        self.ui.lblUser.returnPressed.connect(
            self._focus_password)
        self.ui.lblPassword.returnPressed.connect(
            self._focus_second_password)
        self.ui.lblPassword2.returnPressed.connect(
            self._register)
        self.ui.btnRegister.clicked.connect(
            self._register)

        self._username = None

    def __del__(self):
        self._provider_bootstrapper.set_should_quit()
        self._eip_bootstrapper.set_should_quit()
        self._provider_bootstrapper.wait()
        self._eip_bootstrapper.wait()

    def get_username(self):
        return self._username

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

        try:
            username.encode("ascii")
            password.encode("ascii")
        except:
            message = u"Refrain from using non ASCII áñ characters"

        if message is not None and password != password2:
            message = "Passwords don't match"

        if message is not None and len(password) < 4:
            message = "Password too short"

        if message is not None and password in self.WEAK_PASSWORDS:
            message = "Password too easy"

        if message is not None and username == password:
            message = "Password equal to username"

        if message is not None:
            self._set_register_status(message)
            self._focus_password()
            return False

        return True

    def _register(self):
        """
        Performs the registration based on the values provided in the form
        """
        self.ui.btnRegister.setEnabled(False)
        # See the disabled button
        while QtGui.QApplication.instance().hasPendingEvents():
            QtGui.QApplication.instance().processEvents()
        self.button(QtGui.QWizard.NextButton).setFocus()

        username = self.ui.lblUser.text()
        password = self.ui.lblPassword.text()
        password2 = self.ui.lblPassword2.text()

        if self._basic_password_checks(username, password, password2):
            register = SRPRegister(provider_config=self._provider_config)
            ok, req = register.register_user(username, password)
            if ok:
                self._set_register_status("<b>User registration OK</b>")
                self._username = username
                self.ui.lblPassword2.clearFocus()
                # Detach this call to allow UI updates briefly
                QtCore.QTimer.singleShot(1,
                                         self.page(self.REGISTER_USER_PAGE)
                                         .set_completed)
            else:
                print req.content
                error_msg = "Unknown error"
                try:
                    error_msg = req.json().get("errors").get("login")[0]
                except:
                    logger.error("Unknown error: %r" % (req.content,))
                self._set_register_status(error_msg)
                self.ui.btnRegister.setEnabled(True)
        else:
            self.ui.btnRegister.setEnabled(True)

    def _set_register_status(self, status):
        """
        Sets the status label in the registration page to status

        @param status: status message to display, can be HTML
        @type status: str
        """
        self.ui.lblRegisterStatus.setText(status)

    def _check_provider(self):
        """
        SLOT
        TRIGGERS:
          self.ui.btnCheck.clicked
          self.ui.lnProvider.returnPressed

        Starts the checks for a given provider
        """
        self.ui.grpCheckProvider.setVisible(True)
        self.ui.btnCheck.setEnabled(False)
        self._domain = self.ui.lnProvider.text()

        self._provider_bootstrapper.start()
        self._provider_bootstrapper.run_provider_select_checks(self._domain)

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

    def _https_connection(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.https_connection

        Sets the status for the https connection check
        """
        self._complete_task(data, self.ui.lblHTTPS)

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
                "Unable to load provider configuration"
            }
            self._complete_task(new_data, self.ui.lblProviderInfo)

        self.ui.btnCheck.setEnabled(True)

    def _download_ca_cert(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.download_ca_cert

        Sets the status for the download of the CA certificate check
        """
        self._complete_task(data, self.ui.lblDownloadCaCert)

    def _check_ca_fingerprint(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.check_ca_fingerprint

        Sets the status for the CA fingerprint check
        """
        self._complete_task(data, self.ui.lblCheckCaFpr)

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
        self._provider_bootstrapper.set_should_quit()

    def _download_eip_config(self, data):
        """
        SLOT
        TRIGGER: self._eip_bootstrapper.download_config

        Sets the status for the EIP config downloading check
        """
        self._complete_task(data, self.ui.lblDownloadEIPConfig)

    def _download_client_certificate(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.download_client_certificate

        Sets the status for the download client certificate check and
        completes the page if passed. Also stops the eip bootstrapper
        thread since it's not needed from this point on unless the
        check chain is restarted
        """
        self._complete_task(data, self.ui.lblDownloadClientCert,
                            True, self.SETUP_EIP_PAGE)
        self._eip_bootstrapper.set_should_quit()

    def _current_id_changed(self, pageId):
        """
        SLOT
        TRIGGER: self.currentIdChanged

        Prepares the pages when they appear
        """
        if pageId == self.SELECT_PROVIDER_PAGE:
            self.ui.grpCheckProvider.setVisible(False)
            self.ui.lblNameResolution.setPixmap(self.QUESTION_ICON)
            self.ui.lblHTTPS.setPixmap(self.QUESTION_ICON)
            self.ui.lblProviderInfo.setPixmap(self.QUESTION_ICON)

        if pageId == self.SETUP_PROVIDER_PAGE:
            self._provider_bootstrapper.\
                run_provider_setup_checks(self._provider_config)

        if pageId == self.SETUP_EIP_PAGE:
            self._eip_bootstrapper.start()
            self._eip_bootstrapper.run_eip_setup_checks(self._provider_config)

        if pageId == self.PRESENT_PROVIDER_PAGE:
            # TODO: get the right lang for these
            self.ui.lblProviderName.setText(
                "<b>%s</b>" %
                (self._provider_config.get_name(),))
            self.ui.lblProviderURL.setText(self._provider_config.get_domain())
            self.ui.lblProviderDesc.setText(
                "<i>%s</i>" %
                (self._provider_config.get_description(),))
            self.ui.lblProviderPolicy.setText(self._provider_config
                                              .get_enrollment_policy())

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
                return self.SETUP_EIP_PAGE

        return QtGui.QWizard.nextId(self)
