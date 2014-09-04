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

# TODO: we should use a more granular signaling instead of passing error/ok as
# a result.
from leap.bitmask.backend.leapbackend import ERROR_KEY, PASSED_KEY

from leap.bitmask.config import flags
from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.services import get_service_display_name, get_supported
from leap.bitmask.util.credentials import password_checks, username_checks
from leap.bitmask.util.credentials import USERNAME_REGEX
from leap.bitmask.util.keyring_helpers import has_keyring

from ui_wizard import Ui_Wizard

QtDelayedCall = QtCore.QTimer.singleShot
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

    def __init__(self, backend, leap_signaler):
        """
        Constructor for the main Wizard.

        :param backend: Backend being used
        :type backend: Backend
        """
        QtGui.QWizard.__init__(self)

        self.ui = Ui_Wizard()
        self.ui.setupUi(self)

        self._connected_signals = []

        self.setPixmap(QtGui.QWizard.LogoPixmap,
                       QtGui.QPixmap(":/images/mask-icon.png"))

        self.QUESTION_ICON = QtGui.QPixmap(":/images/black/22/question.png")
        self.ERROR_ICON = QtGui.QPixmap(":/images/black/22/off.png")
        self.OK_ICON = QtGui.QPixmap(":/images/black/22/on.png")

        self._selected_services = set()
        self._shown_services = set()

        self._show_register = False

        self._use_existing_provider = False

        self.ui.grpCheckProvider.setVisible(False)
        self._connect_and_track(self.ui.btnCheck.clicked, self._check_provider)
        self._connect_and_track(self.ui.lnProvider.returnPressed,
                                self._check_provider)

        self._leap_signaler = leap_signaler

        self._backend = backend
        self._backend_connect()

        self._domain = None

        # this details are set when the provider download is complete.
        self._provider_details = None

        self._connect_and_track(self.currentIdChanged,
                                self._current_id_changed)

        self._connect_and_track(self.ui.lnProvider.textChanged,
                                self._enable_check)
        self._connect_and_track(self.ui.rbNewProvider.toggled,
                                lambda x: self._enable_check())
        self._connect_and_track(self.ui.cbProviders.currentIndexChanged[int],
                                self._reset_provider_check)

        self._connect_and_track(self.ui.lblUser.returnPressed,
                                self._focus_password)
        self._connect_and_track(self.ui.lblPassword.returnPressed,
                                self._focus_second_password)
        self._connect_and_track(self.ui.lblPassword2.returnPressed,
                                self._register)
        self._connect_and_track(self.ui.btnRegister.clicked,
                                self._register)

        self._connect_and_track(self.ui.rbExistingProvider.toggled,
                                self._skip_provider_checks)

        usernameRe = QtCore.QRegExp(USERNAME_REGEX)
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
        self._connect_and_track(self.finished, self._wizard_finished)

    def _connect_and_track(self, signal, method):
        """
        Helper to connect signals and keep track of them.

        :param signal: the signal to connect to.
        :type signal: QtCore.Signal
        :param method: the method to call when the signal is triggered.
        :type method: callable, Slot or Signal
        """
        self._connected_signals.append((signal, method))
        signal.connect(method)

    @QtCore.Slot()
    def _wizard_finished(self):
        """
        TRIGGERS:
            self.finished

        This method is called when the wizard is accepted or rejected.
        Here we do the cleanup needed to use the wizard again reusing the
        instance.
        """
        self._provider_checks_ok = False
        self._provider_setup_ok = False
        self.ui.lnProvider.setText('')
        self.ui.grpCheckProvider.setVisible(False)
        self._disconnect_tracked()

    def _load_configured_providers(self):
        """
        Loads the configured providers into the wizard providers combo box.
        """
        self._backend.provider_get_pinned_providers()

    def _load_configured_providers_with_pinned(self, pinned):
        """
        Once we have the pinned providers from the backend, we
        continue setting everything up

        :param pinned: list of pinned providers
        :type pinned: list of str


        How the combobox items are arranged:
        -----------------------------------

        First run:

            demo.bitmask.net
            --
            pinned2.org
            pinned1.org
            pinned3.org

        After some usage:

            added-by-user.org
            pinned-but-then-used.org
            ---
            demo.bitmask.net
            pinned1.org
            pinned3.org
            pinned2.org

        In other words:
            * There are two sections.
            * Section one consists of all the providers that the user has used.
              If this is empty, than use demo.bitmask.net for this section.
              This list is sorted alphabetically.
            * Section two consists of all the pinned or 'pre seeded' providers,
              minus any providers that are now in section one. This last list
              is in random order.
        """
        ls = LeapSettings()
        user_added = ls.get_configured_providers()
        if not user_added and not pinned:
            self.ui.rbExistingProvider.setEnabled(False)
            self.ui.label_8.setEnabled(False)  # 'https://' label
            self.ui.cbProviders.setEnabled(False)
            return

        user_added.sort()

        if not user_added:
            user_added = [pinned.pop(0)]

        # separate unused pinned providers from user added ones
        for p in user_added:
            if p in pinned:
                pinned.remove(p)

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

        # We need to set it as complete explicitly
        self.page(self.INTRO_PAGE).set_completed()

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

    @QtCore.Slot(unicode)
    def _enable_check(self, reset=True):
        """
        TRIGGERS:
            self.ui.lnProvider.textChanged

        Enables/disables the 'check' button in the SELECT_PROVIDER_PAGE
        depending on the lnProvider content.

        :param reset: this contains the text of the line edit, and when is
                      called directly defines whether we want to reset the
                      checks.
        :type reset: unicode or bool
        """
        enabled = len(self.ui.lnProvider.text()) != 0
        enabled = enabled or self.ui.rbExistingProvider.isChecked()
        self.ui.btnCheck.setEnabled(enabled)

        if reset:
            self._reset_provider_check()

    def _focus_username(self):
        """
        Focus at the username lineedit for the registration page
        """
        self.ui.lblUser.setFocus()

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

        user_ok, msg = username_checks(username)
        if user_ok:
            pass_ok, msg = password_checks(username, password, password2)

        if user_ok and pass_ok:
            self._set_register_status(self.tr("Starting registration..."))

            self._backend.user_register(provider=self._domain,
                                        username=username, password=password)
            self._username = username
            self._password = password
        else:
            if user_ok:
                self._focus_password()
            else:
                self._focus_username()
            self._set_register_status(msg, error=True)
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

    @QtCore.Slot()
    def _registration_finished(self):
        """
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

    @QtCore.Slot()
    def _registration_failed(self):
        """
        TRIGGERS:
            self._backend.signaler.srp_registration_failed

        The registration has failed, so we report the problem.
        """
        self._username = self._password = None

        error_msg = self.tr("Something has gone wrong. Please try again.")
        self._set_register_status(error_msg, error=True)
        self.ui.btnRegister.setEnabled(True)

    @QtCore.Slot()
    def _registration_taken(self):
        """
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
        self.page(self.SELECT_PROVIDER_PAGE).set_completed(
            flags.SKIP_WIZARD_CHECKS)

    def _reset_provider_setup(self):
        """
        Resets the UI for setting up a provider.
        """
        self.ui.lblDownloadCaCert.setPixmap(None)
        self.ui.lblCheckCaFpr.setPixmap(None)
        self.ui.lblCheckApiCert.setPixmap(None)

    @QtCore.Slot()
    def _check_provider(self):
        """
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
        self._backend.provider_setup(provider=self._domain)

    @QtCore.Slot(bool)
    def _skip_provider_checks(self, skip):
        """
        TRIGGERS:
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
        passed = data[PASSED_KEY]
        error = data[ERROR_KEY]
        if passed:
            label.setPixmap(self.OK_ICON)
            if complete:
                self.page(complete_page).set_completed()
                self.button(QtGui.QWizard.NextButton).setFocus()
        else:
            label.setPixmap(self.ERROR_ICON)
            logger.error(error)

    @QtCore.Slot(dict)
    def _name_resolution(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_name_resolution

        Sets the status for the name resolution check
        """
        self._complete_task(data, self.ui.lblNameResolution)
        status = ""
        passed = data[PASSED_KEY]
        if not passed:
            status = self.tr("<font color='red'><b>Non-existent "
                             "provider</b></font>")
        else:
            self.ui.lblHTTPS.setPixmap(self.QUESTION_ICON)
        self.ui.lblProviderSelectStatus.setText(status)
        self.ui.btnCheck.setEnabled(not passed)
        self.ui.lnProvider.setEnabled(not passed)

    @QtCore.Slot(dict)
    def _https_connection(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_https_connection

        Sets the status for the https connection check
        """
        self._complete_task(data, self.ui.lblHTTPS)
        status = ""
        passed = data[PASSED_KEY]
        if not passed:
            status = self.tr("<font color='red'><b>%s</b></font>") \
                % (data[ERROR_KEY])
            self.ui.lblProviderSelectStatus.setText(status)
        else:
            self.ui.lblProviderInfo.setPixmap(self.QUESTION_ICON)
        self.ui.btnCheck.setEnabled(not passed)
        self.ui.lnProvider.setEnabled(not passed)

    @QtCore.Slot(dict)
    def _download_provider_info(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_download_provider_info

        Sets the status for the provider information download
        check. Since this check is the last of this set, it also
        completes the page if passed
        """
        if data[PASSED_KEY]:
            self._complete_task(data, self.ui.lblProviderInfo,
                                True, self.SELECT_PROVIDER_PAGE)
            self._provider_checks_ok = True
            lang = QtCore.QLocale.system().name()
            self._backend.provider_get_details(domain=self._domain, lang=lang)
        else:
            new_data = {
                PASSED_KEY: False,
                ERROR_KEY: self.tr("Unable to load provider configuration")
            }
            self._complete_task(new_data, self.ui.lblProviderInfo)

        status = ""
        if not data[PASSED_KEY]:
            status = self.tr("<font color='red'><b>Not a valid provider"
                             "</b></font>")
            self.ui.lblProviderSelectStatus.setText(status)
        self.ui.btnCheck.setEnabled(True)

        # Enable provider widget
        if self.ui.rbNewProvider.isChecked():
            self.ui.lnProvider.setEnabled(True)
        else:
            self.ui.cbProviders.setEnabled(True)

    @QtCore.Slot()
    def _provider_get_details(self, details):
        """
        Set the details for the just downloaded provider.

        :param details: the details of the provider.
        :type details: dict
        """
        self._provider_details = details

    @QtCore.Slot(dict)
    def _download_ca_cert(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_download_ca_cert

        Sets the status for the download of the CA certificate check
        """
        self._complete_task(data, self.ui.lblDownloadCaCert)
        passed = data[PASSED_KEY]
        if passed:
            self.ui.lblCheckCaFpr.setPixmap(self.QUESTION_ICON)

    @QtCore.Slot(dict)
    def _check_ca_fingerprint(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_check_ca_fingerprint

        Sets the status for the CA fingerprint check
        """
        self._complete_task(data, self.ui.lblCheckCaFpr)
        passed = data[PASSED_KEY]
        if passed:
            self.ui.lblCheckApiCert.setPixmap(self.QUESTION_ICON)

    @QtCore.Slot(dict)
    def _check_api_certificate(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_check_api_certificate

        Sets the status for the API certificate check. Also finishes
        the provider bootstrapper thread since it's not needed anymore
        from this point on, unless the whole check chain is restarted
        """
        self._complete_task(data, self.ui.lblCheckApiCert,
                            True, self.SETUP_PROVIDER_PAGE)
        self._provider_setup_ok = True

    @QtCore.Slot(str, int)
    def _service_selection_changed(self, service, state):
        """
        TRIGGERS:
            service_checkbox.stateChanged

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
        title = self.tr("Services by {0}").format(
            self._provider_details['domain'])
        self.ui.grpServices.setTitle(title)

        services = get_supported(self._provider_details['services'])

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

    @QtCore.Slot(int)
    def _current_id_changed(self, pageId):
        """
        TRIGGERS:
            self.currentIdChanged

        Prepares the pages when they appear

        :param pageId: the new current page id.
        :type pageId: int
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
                self.ui.lblDownloadCaCert.setPixmap(self.QUESTION_ICON)
                self._backend.provider_bootstrap(provider=self._domain)

        if pageId == self.PRESENT_PROVIDER_PAGE:
            details = self._provider_details
            name = "<b>{0}</b>".format(details['name'])
            domain = "https://{0}".format(details['domain'])
            description = "<i>{0}</i>".format(details['description'])
            self.ui.lblProviderName.setText(name)
            self.ui.lblProviderURL.setText(domain)
            self.ui.lblProviderDesc.setText(description)
            self.ui.lblServicesOffered.setText(details['services_string'])
            self.ui.lblProviderPolicy.setText(details['enrollment_policy'])

        if pageId == self.REGISTER_USER_PAGE:
            title = self.tr("Register a new user with {0}")
            title = title.format(self._provider_details['domain'])
            self.page(pageId).setTitle(title)
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
        sig = self._leap_signaler
        conntrack = self._connect_and_track
        conntrack(sig.prov_name_resolution, self._name_resolution)
        conntrack(sig.prov_https_connection, self._https_connection)
        conntrack(sig.prov_download_provider_info,
                  self._download_provider_info)
        conntrack(sig.prov_get_details, self._provider_get_details)
        conntrack(sig.prov_get_pinned_providers,
                  self._load_configured_providers_with_pinned)

        conntrack(sig.prov_download_ca_cert, self._download_ca_cert)
        conntrack(sig.prov_check_ca_fingerprint, self._check_ca_fingerprint)
        conntrack(sig.prov_check_api_certificate, self._check_api_certificate)

        conntrack(sig.srp_registration_finished, self._registration_finished)
        conntrack(sig.srp_registration_failed, self._registration_failed)
        conntrack(sig.srp_registration_taken, self._registration_taken)

    def _disconnect_tracked(self):
        """
        This method is called when the wizard dialog is closed.
        We disconnect all the signals in here.
        """
        for signal, method in self._connected_signals:
            try:
                signal.disconnect(method)
            except RuntimeError:
                pass  # Signal was not connected
