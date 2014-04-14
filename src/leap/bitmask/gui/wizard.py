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
import logging
import random

from functools import partial

from PySide import QtCore, QtGui

from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.provider import get_provider_path
from leap.bitmask.services import get_service_display_name, get_supported
from leap.bitmask.util.keyring_helpers import has_keyring
from leap.bitmask.util.password import basic_password_checks

from ui_wizard import Ui_Wizard

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

    BARE_USERNAME_REGEX = r"^[A-Za-z\d_]+$"

    def __init__(self, backend, bypass_checks=False):
        """
        Constructor for the main Wizard.

        :param backend: Backend being used
        :type backend: Backend
        :param bypass_checks: Set to true if the app should bypass
                              first round of checks for CA
                              certificates at bootstrap
        :type bypass_checks: bool
        """
        QtGui.QWizard.__init__(self)

        self.ui = Ui_Wizard()
        self.ui.setupUi(self)

        self.setPixmap(QtGui.QWizard.LogoPixmap,
                       QtGui.QPixmap(":/images/mask-icon.png"))

        self.QUESTION_ICON = QtGui.QPixmap(":/images/Emblem-question.png")
        self.ERROR_ICON = QtGui.QPixmap(":/images/Dialog-error.png")
        self.OK_ICON = QtGui.QPixmap(":/images/Dialog-accept.png")

        self._selected_services = set()
        self._shown_services = set()

        self._show_register = False

        self._use_existing_provider = False

        self.ui.grpCheckProvider.setVisible(False)
        self.ui.btnCheck.clicked.connect(self._check_provider)
        self.ui.lnProvider.returnPressed.connect(self._check_provider)

        self._backend = backend
        self._backend_connect()

        self._domain = None
        # HACK!! We need provider_config for the time being, it'll be
        # removed
        self._provider_config = (
            self._backend._components["provider"]._provider_config)

        # We will store a reference to the defers for eventual use
        # (eg, to cancel them) but not doing anything with them right now.
        self._provider_select_defer = None
        self._provider_setup_defer = None

        self.currentIdChanged.connect(self._current_id_changed)

        self.ui.lnProvider.textChanged.connect(self._enable_check)
        self.ui.rbNewProvider.toggled.connect(
            lambda x: self._enable_check())
        self.ui.cbProviders.currentIndexChanged[int].connect(
            self._reset_provider_check)

        self.ui.lblUser.returnPressed.connect(
            self._focus_password)
        self.ui.lblPassword.returnPressed.connect(
            self._focus_second_password)
        self.ui.lblPassword2.returnPressed.connect(
            self._register)
        self.ui.btnRegister.clicked.connect(
            self._register)

        self.ui.rbExistingProvider.toggled.connect(self._skip_provider_checks)

        usernameRe = QtCore.QRegExp(self.BARE_USERNAME_REGEX)
        self.ui.lblUser.setValidator(
            QtGui.QRegExpValidator(usernameRe, self))

        self.page(self.REGISTER_USER_PAGE).setCommitPage(True)

        self._username = None
        self._password = None

        self.page(self.REGISTER_USER_PAGE).setButtonText(
            QtGui.QWizard.CommitButton, self.tr("&Next >"))
        self.page(self.SERVICES_PAGE).setButtonText(
            QtGui.QWizard.FinishButton, self.tr("Connect"))

        # XXX: Temporary removal for enrollment policy
        # https://leap.se/code/issues/2922
        self.ui.label_12.setVisible(False)
        self.ui.lblProviderPolicy.setVisible(False)

        self._load_configured_providers()

        self._provider_checks_ok = False
        self._provider_setup_ok = False
        self.finished.connect(self._wizard_finished)

    @QtCore.Slot()
    def _wizard_finished(self):
        """
        SLOT
        TRIGGER:
            self.finished

        This method is called when the wizard is accepted or rejected.
        Here we do the cleanup needed to use the wizard again reusing the
        instance.
        """
        self._provider_checks_ok = False
        self._provider_setup_ok = False
        self.ui.lnProvider.setText('')
        self.ui.grpCheckProvider.setVisible(False)
        self._backend_disconnect()

    def _load_configured_providers(self):
        """
        Loads the configured providers into the wizard providers combo box.
        """
        ls = LeapSettings()
        providers = ls.get_configured_providers()
        if not providers:
            self.ui.rbExistingProvider.setEnabled(False)
            self.ui.label_8.setEnabled(False)  # 'https://' label
            self.ui.cbProviders.setEnabled(False)
            return

        pinned = []
        user_added = []

        # separate pinned providers from user added ones
        for p in providers:
            if ls.is_pinned_provider(p):
                pinned.append(p)
            else:
                user_added.append(p)

        if user_added:
            self.ui.cbProviders.addItems(user_added)

        if user_added and pinned:
            self.ui.cbProviders.addItem('---')

        if pinned:
            random.shuffle(pinned)  # don't prioritize alphabetically
            self.ui.cbProviders.addItems(pinned)

        # We have configured providers, so by default we select the
        # 'Use existing provider' option.
        self.ui.rbExistingProvider.setChecked(True)

    def get_domain(self):
        return self._domain

    def get_username(self):
        return self._username

    def get_password(self):
        return self._password

    def get_remember(self):
        return has_keyring() and self.ui.chkRemember.isChecked()

    def get_services(self):
        return self._selected_services

    @QtCore.Slot()
    def _enable_check(self, reset=True):
        """
        SLOT
        TRIGGER:
            self.ui.lnProvider.textChanged

        Enables/disables the 'check' button in the SELECT_PROVIDER_PAGE
        depending on the lnProvider content.
        """
        enabled = len(self.ui.lnProvider.text()) != 0
        enabled = enabled or self.ui.rbExistingProvider.isChecked()
        self.ui.btnCheck.setEnabled(enabled)

        if reset:
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

    def _register(self):
        """
        Performs the registration based on the values provided in the form
        """
        self.ui.btnRegister.setEnabled(False)

        username = self.ui.lblUser.text()
        password = self.ui.lblPassword.text()
        password2 = self.ui.lblPassword2.text()

        ok, msg = basic_password_checks(username, password, password2)
        if ok:
            self._set_register_status(self.tr("Starting registration..."))

            self._backend.register_user(self._domain, username, password)
            self._username = username
            self._password = password
        else:
            self._set_register_status(msg, error=True)
            self._focus_password()
            self.ui.btnRegister.setEnabled(True)

    def _set_registration_fields_visibility(self, visible):
        """
        This method hides the username and password labels and inputboxes.

        :param visible: sets the visibility of the widgets
            True: widgets are visible or False: are not
        :type visible: bool
        """
        # username and password inputs
        self.ui.lblUser.setVisible(visible)
        self.ui.lblPassword.setVisible(visible)
        self.ui.lblPassword2.setVisible(visible)

        # username and password labels
        self.ui.label_15.setVisible(visible)
        self.ui.label_16.setVisible(visible)
        self.ui.label_17.setVisible(visible)

        # register button
        self.ui.btnRegister.setVisible(visible)

    def _registration_finished(self):
        """
        SLOT
        TRIGGERS:
          self._backend.signaler.srp_registration_finished

        The registration has finished successfully, so we do some final steps.
        """
        user_domain = self._username + "@" + self._domain
        message = "<font color='green'><h3>"
        message += self.tr("User %s successfully registered.") % (
            user_domain, )
        message += "</h3></font>"
        self._set_register_status(message)

        self.ui.lblPassword2.clearFocus()
        self._set_registration_fields_visibility(False)

        # Allow the user to remember his password
        if has_keyring():
            self.ui.chkRemember.setVisible(True)
            self.ui.chkRemember.setEnabled(True)

        self.page(self.REGISTER_USER_PAGE).set_completed()
        self.button(QtGui.QWizard.BackButton).setEnabled(False)

    def _registration_failed(self):
        """
        SLOT
        TRIGGERS:
          self._backend.signaler.srp_registration_failed

        The registration has failed, so we report the problem.
        """
        self._username = self._password = None

        error_msg = self.tr("Something has gone wrong. Please try again.")
        self._set_register_status(error_msg, error=True)
        self.ui.btnRegister.setEnabled(True)

    def _registration_taken(self):
        """
        SLOT
        TRIGGERS:
          self._backend.signaler.srp_registration_taken

        The requested username is taken, warn the user about that.
        """
        self._username = self._password = None

        error_msg = self.tr("The requested username is taken, choose another.")
        self._set_register_status(error_msg, error=True)
        self.ui.btnRegister.setEnabled(True)

    def _set_register_status(self, status, error=False):
        """
        Sets the status label in the registration page to status

        :param status: status message to display, can be HTML
        :type status: str
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
        if self.ui.rbNewProvider.isChecked():
            self._domain = self.ui.lnProvider.text()
        else:
            self._domain = self.ui.cbProviders.currentText()

        self._provider_checks_ok = False

        # just in case that the user has already setup a provider and
        # go 'back' to check a provider
        self._provider_setup_ok = False

        self.ui.grpCheckProvider.setVisible(True)
        self.ui.btnCheck.setEnabled(False)

        # Disable provider widget
        if self.ui.rbNewProvider.isChecked():
            self.ui.lnProvider.setEnabled(False)
        else:
            self.ui.cbProviders.setEnabled(False)

        self.button(QtGui.QWizard.BackButton).clearFocus()

        self.ui.lblNameResolution.setPixmap(self.QUESTION_ICON)
        self._provider_select_defer = self._backend.\
            setup_provider(self._domain)

    def _skip_provider_checks(self, skip):
        """
        SLOT
        Triggered:
            self.ui.rbExistingProvider.toggled

        Allows the user to move to the next page without make any checks,
        used when we are selecting an already configured provider.

        :param skip: if we should skip checks or not
        :type skip: bool
        """
        if skip:
            self._reset_provider_check()

        self._use_existing_provider = skip

    def _complete_task(self, data, label, complete=False, complete_page=-1):
        """
        Checks a task and completes a page if specified

        :param data: data as it comes from the bootstrapper thread for
        a specific check
        :type data: dict
        :param label: label that displays the status icon for a
        specific check that corresponds to the data
        :type label: QtGui.QLabel
        :param complete: if True, it completes the page specified,
        which must be of type WizardPage
        :type complete: bool
        :param complete_page: page id to complete
        :type complete_page: int
        """
        passed = data[self._backend.PASSED_KEY]
        error = data[self._backend.ERROR_KEY]
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
        TRIGGER: self._backend.signaler.prov_name_resolution

        Sets the status for the name resolution check
        """
        self._complete_task(data, self.ui.lblNameResolution)
        status = ""
        passed = data[self._backend.PASSED_KEY]
        if not passed:
            status = self.tr("<font color='red'><b>Non-existent "
                             "provider</b></font>")
        else:
            self.ui.lblHTTPS.setPixmap(self.QUESTION_ICON)
        self.ui.lblProviderSelectStatus.setText(status)
        self.ui.btnCheck.setEnabled(not passed)
        self.ui.lnProvider.setEnabled(not passed)

    def _https_connection(self, data):
        """
        SLOT
        TRIGGER: self._backend.signaler.prov_https_connection

        Sets the status for the https connection check
        """
        self._complete_task(data, self.ui.lblHTTPS)
        status = ""
        passed = data[self._backend.PASSED_KEY]
        if not passed:
            status = self.tr("<font color='red'><b>%s</b></font>") \
                % (data[self._backend.ERROR_KEY])
            self.ui.lblProviderSelectStatus.setText(status)
        else:
            self.ui.lblProviderInfo.setPixmap(self.QUESTION_ICON)
        self.ui.btnCheck.setEnabled(not passed)
        self.ui.lnProvider.setEnabled(not passed)

    def _download_provider_info(self, data):
        """
        SLOT
        TRIGGER: self._backend.signaler.prov_download_provider_info

        Sets the status for the provider information download
        check. Since this check is the last of this set, it also
        completes the page if passed
        """
        if self._provider_config.load(get_provider_path(self._domain)):
            self._complete_task(data, self.ui.lblProviderInfo,
                                True, self.SELECT_PROVIDER_PAGE)
            self._provider_checks_ok = True
        else:
            new_data = {
                self._backend.PASSED_KEY: False,
                self._backend.ERROR_KEY:
                self.tr("Unable to load provider configuration")
            }
            self._complete_task(new_data, self.ui.lblProviderInfo)

        status = ""
        if not data[self._backend.PASSED_KEY]:
            status = self.tr("<font color='red'><b>Not a valid provider"
                             "</b></font>")
            self.ui.lblProviderSelectStatus.setText(status)
        self.ui.btnCheck.setEnabled(True)

        # Enable provider widget
        if self.ui.rbNewProvider.isChecked():
            self.ui.lnProvider.setEnabled(True)
        else:
            self.ui.cbProviders.setEnabled(True)

    def _download_ca_cert(self, data):
        """
        SLOT
        TRIGGER: self._backend.signaler.prov_download_ca_cert

        Sets the status for the download of the CA certificate check
        """
        self._complete_task(data, self.ui.lblDownloadCaCert)
        passed = data[self._backend.PASSED_KEY]
        if passed:
            self.ui.lblCheckCaFpr.setPixmap(self.QUESTION_ICON)

    def _check_ca_fingerprint(self, data):
        """
        SLOT
        TRIGGER: self._backend.signaler.prov_check_ca_fingerprint

        Sets the status for the CA fingerprint check
        """
        self._complete_task(data, self.ui.lblCheckCaFpr)
        passed = data[self._backend.PASSED_KEY]
        if passed:
            self.ui.lblCheckApiCert.setPixmap(self.QUESTION_ICON)

    def _check_api_certificate(self, data):
        """
        SLOT
        TRIGGER: self._backend.signaler.prov_check_api_certificate

        Sets the status for the API certificate check. Also finishes
        the provider bootstrapper thread since it's not needed anymore
        from this point on, unless the whole check chain is restarted
        """
        self._complete_task(data, self.ui.lblCheckApiCert,
                            True, self.SETUP_PROVIDER_PAGE)
        self._provider_setup_ok = True

    def _service_selection_changed(self, service, state):
        """
        SLOT
        TRIGGER: service_checkbox.stateChanged
        Adds the service to the state if the state is checked, removes
        it otherwise

        :param service: service to handle
        :type service: str
        :param state: state of the checkbox
        :type state: int
        """
        if state == QtCore.Qt.Checked:
            self._selected_services = \
                self._selected_services.union(set([service]))
        else:
            self._selected_services = \
                self._selected_services.difference(set([service]))

    def _populate_services(self):
        """
        Loads the services that the provider provides into the UI for
        the user to enable or disable.
        """
        self.ui.grpServices.setTitle(
            self.tr("Services by %s") %
            (self._provider_config.get_name(),))

        services = get_supported(
            self._provider_config.get_services())

        for service in services:
            try:
                if service not in self._shown_services:
                    checkbox = QtGui.QCheckBox(self)
                    service_label = get_service_display_name(service)
                    checkbox.setText(service_label)

                    self.ui.serviceListLayout.addWidget(checkbox)
                    checkbox.stateChanged.connect(
                        partial(self._service_selection_changed, service))
                    checkbox.setChecked(True)
                    self._shown_services.add(service)
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
            self._clear_register_widgets()
            skip = self.ui.rbExistingProvider.isChecked()
            if not self._provider_checks_ok:
                self._enable_check()
                self._skip_provider_checks(skip)
            else:
                self._enable_check(reset=False)

        if pageId == self.SETUP_PROVIDER_PAGE:
            if not self._provider_setup_ok:
                self._reset_provider_setup()
                sub_title = self.tr("Gathering configuration options for {0}")
                sub_title = sub_title.format(self._provider_config.get_name())
                self.page(pageId).setSubTitle(sub_title)
                self.ui.lblDownloadCaCert.setPixmap(self.QUESTION_ICON)
                self._provider_setup_defer = self._backend.\
                    provider_bootstrap(self._domain)

        if pageId == self.PRESENT_PROVIDER_PAGE:
            self.page(pageId).setSubTitle(self.tr("Description of services "
                                                  "offered by %s") %
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

            self.ui.lblServicesOffered.setText(self._provider_config
                                               .get_services_string())
            self.ui.lblProviderPolicy.setText(self._provider_config
                                              .get_enrollment_policy())

        if pageId == self.REGISTER_USER_PAGE:
            self.page(pageId).setSubTitle(self.tr("Register a new user with "
                                                  "%s") %
                                          (self._provider_config
                                           .get_name(),))
            self.ui.chkRemember.setVisible(False)

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

        if self.currentPage() == self.page(self.SELECT_PROVIDER_PAGE):
            if self._use_existing_provider:
                self._domain = self.ui.cbProviders.currentText()
                self._provider_config = ProviderConfig.get_provider_config(
                    self._domain)
                if self._show_register:
                    return self.REGISTER_USER_PAGE
                else:
                    return self.SERVICES_PAGE

        return QtGui.QWizard.nextId(self)

    def _clear_register_widgets(self):
        """
        Clears the widgets that my be filled and a possible error message.
        """
        self._set_register_status("")
        self.ui.lblUser.setText("")
        self.ui.lblPassword.setText("")
        self.ui.lblPassword2.setText("")

    def _backend_connect(self):
        """
        Connects all the backend signals with the wizard.
        """
        sig = self._backend.signaler
        sig.prov_name_resolution.connect(self._name_resolution)
        sig.prov_https_connection.connect(self._https_connection)
        sig.prov_download_provider_info.connect(self._download_provider_info)

        sig.prov_download_ca_cert.connect(self._download_ca_cert)
        sig.prov_check_ca_fingerprint.connect(self._check_ca_fingerprint)
        sig.prov_check_api_certificate.connect(self._check_api_certificate)

        sig.srp_registration_finished.connect(self._registration_finished)
        sig.srp_registration_failed.connect(self._registration_failed)
        sig.srp_registration_taken.connect(self._registration_taken)

    def _backend_disconnect(self):
        """
        This method is called when the wizard dialog is closed.
        We disconnect all the backend signals in here.
        """
        sig = self._backend.signaler
        try:
            # disconnect backend signals
            sig.prov_name_resolution.disconnect(self._name_resolution)
            sig.prov_https_connection.disconnect(self._https_connection)
            sig.prov_download_provider_info.disconnect(
                self._download_provider_info)

            sig.prov_download_ca_cert.disconnect(self._download_ca_cert)
            sig.prov_check_ca_fingerprint.disconnect(
                self._check_ca_fingerprint)
            sig.prov_check_api_certificate.disconnect(
                self._check_api_certificate)
        except RuntimeError:
            pass  # Signal was not connected
