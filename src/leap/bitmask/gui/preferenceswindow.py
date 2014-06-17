# -*- coding: utf-8 -*-
# preferenceswindow.py
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
Preferences window
"""
import logging

from functools import partial

from PySide import QtCore, QtGui

from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.gui.ui_preferences import Ui_Preferences
from leap.bitmask.util.credentials import password_checks
from leap.bitmask.services import get_service_display_name, MX_SERVICE

logger = logging.getLogger(__name__)


class PreferencesWindow(QtGui.QDialog):
    """
    Window that displays the preferences.
    """
    preferences_saved = QtCore.Signal()

    def __init__(self, parent, username, domain, backend, soledad_started, mx,
                 leap_signaler):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget
        :param username: the user set in the login widget
        :type username: unicode
        :param domain: the selected domain in the login widget
        :type domain: unicode
        :param backend: Backend being used
        :type backend: Backend
        :param soledad_started: whether soledad has started or not
        :type soledad_started: bool
        :param mx: whether the current provider provides mx or not.
        :type mx: bool
        """
        QtGui.QDialog.__init__(self, parent)
        self.AUTOMATIC_GATEWAY_LABEL = self.tr("Automatic")

        self._username = username
        self._domain = domain
        self._leap_signaler = leap_signaler
        self._backend = backend
        self._soledad_started = soledad_started
        self._mx_provided = mx

        self._settings = LeapSettings()
        self._backend_connect()

        # Load UI
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.ui.lblPasswordChangeStatus.setVisible(False)
        self.ui.lblProvidersServicesStatus.setVisible(False)

        self._selected_services = set()

        # Connections
        self.ui.pbChangePassword.clicked.connect(self._change_password)
        self.ui.cbProvidersServices.currentIndexChanged[unicode].connect(
            self._populate_services)

        if not self._settings.get_configured_providers():
            self.ui.gbEnabledServices.setEnabled(False)
        else:
            self._add_configured_providers()

        if self._username is None:
            self._not_logged_in()
        else:
            self.ui.gbPasswordChange.setEnabled(True)
            if self._mx_provided:
                self._provides_mx()

        self._select_provider_by_name(domain)

    def _not_logged_in(self):
        """
        Actions to perform if the user is not logged in.
        """
        msg = self.tr(
            "In order to change your password you need to be logged in.")
        self._set_password_change_status(msg)
        self.ui.gbPasswordChange.setEnabled(False)

    def _provides_mx(self):
        """
        Actions to perform if the provider provides MX.
        """
        pw_enabled = True
        enabled_services = self._settings.get_enabled_services(self._domain)
        mx_name = get_service_display_name(MX_SERVICE)

        if MX_SERVICE not in enabled_services:
            msg = self.tr("You need to enable {0} in order to change "
                          "the password.".format(mx_name))
            self._set_password_change_status(msg, error=True)
            pw_enabled = False
        else:
            # check if Soledad is bootstrapped
            if not self._soledad_started:
                msg = self.tr(
                    "You need to wait until {0} is ready in "
                    "order to change the password.".format(mx_name))
                self._set_password_change_status(msg)
                pw_enabled = False

        self.ui.gbPasswordChange.setEnabled(pw_enabled)

    @QtCore.Slot()
    def set_soledad_ready(self):
        """
        TRIGGERS:
            parent.soledad_ready

        It notifies when the soledad object as ready to use.
        """
        self.ui.lblPasswordChangeStatus.setVisible(False)
        self.ui.gbPasswordChange.setEnabled(True)

    def _set_password_change_status(self, status, error=False, success=False):
        """
        Sets the status label for the password change.

        :param status: status message to display, can be HTML
        :type status: str
        """
        if error:
            status = "<font color='red'><b>%s</b></font>" % (status,)
        elif success:
            status = "<font color='green'><b>%s</b></font>" % (status,)

        if not self.ui.gbPasswordChange.isEnabled():
            status = "<font color='black'>%s</font>" % (status,)

        self.ui.lblPasswordChangeStatus.setVisible(True)
        self.ui.lblPasswordChangeStatus.setText(status)

    def _set_changing_password(self, disable):
        """
        Enables or disables the widgets in the password change group box.

        :param disable: True if the widgets should be disabled and
                        it displays the status label that shows that is
                        changing the password.
                        False if they should be enabled.
        :type disable: bool
        """
        if disable:
            self._set_password_change_status(self.tr("Changing password..."))

        self.ui.leCurrentPassword.setEnabled(not disable)
        self.ui.leNewPassword.setEnabled(not disable)
        self.ui.leNewPassword2.setEnabled(not disable)
        self.ui.pbChangePassword.setEnabled(not disable)

    @QtCore.Slot()
    def _change_password(self):
        """
        TRIGGERS:
            self.ui.pbChangePassword.clicked

        Changes the user's password if the inputboxes are correctly filled.
        """
        username = self._username
        current_password = self.ui.leCurrentPassword.text()
        new_password = self.ui.leNewPassword.text()
        new_password2 = self.ui.leNewPassword2.text()

        ok, msg = password_checks(username, new_password, new_password2)

        if not ok:
            self._set_changing_password(False)
            self._set_password_change_status(msg, error=True)
            self.ui.leNewPassword.setFocus()
            return

        self._set_changing_password(True)
        self._backend.user_change_password(current_password=current_password,
                                           new_password=new_password)

    @QtCore.Slot()
    def _srp_change_password_ok(self):
        """
        TRIGGERS:
            self._backend.signaler.srp_password_change_ok

        Callback used to display a successfully changed password.
        """
        new_password = self.ui.leNewPassword.text()
        logger.debug("SRP password changed successfully.")

        if self._mx_provided:
            self._backend.soledad_change_password(new_password=new_password)
        else:
            self._change_password_success()

    @QtCore.Slot(unicode)
    def _srp_change_password_problem(self, msg):
        """
        TRIGGERS:
            self._backend.signaler.srp_password_change_error
            self._backend.signaler.srp_password_change_badpw

        Callback used to display an error on changing password.

        :param msg: the message to show to the user.
        :type msg: unicode
        """
        logger.error("Error changing password")
        self._set_password_change_status(msg, error=True)
        self._set_changing_password(False)

    @QtCore.Slot()
    def _soledad_change_password_ok(self):
        """
        TRIGGERS:
            Signaler.soledad_password_change_ok

        Soledad password change went OK.
        """
        logger.debug("Soledad password changed successfully.")
        self._change_password_success()

    def _change_password_success(self):
        """
        Callback used to display a successfully changed password.
        """
        logger.debug("Soledad password changed successfully.")

        self._set_password_change_status(
            self.tr("Password changed successfully."), success=True)
        self._clear_password_inputs()
        self._set_changing_password(False)

    @QtCore.Slot(unicode)
    def _soledad_change_password_problem(self, msg):
        """
        TRIGGERS:
            Signaler.soledad_password_change_error

        Callback used to display an error on changing password.

        :param msg: the message to show to the user.
        :type msg: unicode
        """
        logger.error("Error changing soledad password")
        self._set_password_change_status(msg, error=True)
        self._set_changing_password(False)

    def _clear_password_inputs(self):
        """
        Clear the contents of the inputs.
        """
        self.ui.leCurrentPassword.setText("")
        self.ui.leNewPassword.setText("")
        self.ui.leNewPassword2.setText("")

    def _set_providers_services_status(self, status, success=False):
        """
        Sets the status label for the password change.

        :param status: status message to display, can be HTML
        :type status: str
        :param success: is set to True if we should display the
                        message as green
        :type success: bool
        """
        if success:
            status = "<font color='green'><b>%s</b></font>" % (status,)

        self.ui.lblProvidersServicesStatus.setVisible(True)
        self.ui.lblProvidersServicesStatus.setText(status)

    def _add_configured_providers(self):
        """
        Add the client's configured providers to the providers combo boxes.
        """
        self.ui.cbProvidersServices.clear()
        for provider in self._settings.get_configured_providers():
            self.ui.cbProvidersServices.addItem(provider)

    def _select_provider_by_name(self, name):
        """
        Given a provider name/domain, selects it in the combobox.

        :param name: name or domain for the provider
        :type name: str
        """
        provider_index = self.ui.cbProvidersServices.findText(name)
        self.ui.cbProvidersServices.setCurrentIndex(provider_index)

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

        # We hide the maybe-visible status label after a change
        self.ui.lblProvidersServicesStatus.setVisible(False)

    @QtCore.Slot(str)
    def _populate_services(self, domain):
        """
        TRIGGERS:
            self.ui.cbProvidersServices.currentIndexChanged[unicode]

        Fill the services list with the selected provider's services.

        :param domain: the domain of the provider to load services from.
        :type domain: str
        """
        # We hide the maybe-visible status label after a change
        self.ui.lblProvidersServicesStatus.setVisible(False)

        if not domain:
            return

        # set the proper connection for the 'save' button
        try:
            self.ui.pbSaveServices.clicked.disconnect()
        except RuntimeError:
            pass  # Signal was not connected

        save_services = partial(self._save_enabled_services, domain)
        self.ui.pbSaveServices.clicked.connect(save_services)

        self._backend.provider_get_supported_services(domain=domain)

    @QtCore.Slot(str)
    def _load_services(self, services):
        """
        TRIGGERS:
            self.ui.cbProvidersServices.currentIndexChanged[unicode]

        Loads the services that the provider provides into the UI for
        the user to enable or disable.

        :param domain: the domain of the provider to load services from.
        :type domain: str
        """
        domain = self.ui.cbProvidersServices.currentText()
        services_conf = self._settings.get_enabled_services(domain)

        # discard changes if other provider is selected
        self._selected_services = set()

        # from: http://stackoverflow.com/a/13103617/687989
        # remove existing checkboxes
        layout = self.ui.vlServices
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        # add one checkbox per service and set the current configured value
        for service in services:
            try:
                checkbox = QtGui.QCheckBox(self)
                service_label = get_service_display_name(service)
                checkbox.setText(service_label)

                self.ui.vlServices.addWidget(checkbox)
                checkbox.stateChanged.connect(
                    partial(self._service_selection_changed, service))

                checkbox.setChecked(service in services_conf)
            except ValueError:
                logger.error("Something went wrong while trying to "
                             "load service %s" % (service,))

    @QtCore.Slot(str)
    def _save_enabled_services(self, provider):
        """
        TRIGGERS:
            self.ui.pbSaveServices.clicked

        Saves the new enabled services settings to the configuration file.

        :param provider: the provider config that we need to save.
        :type provider: str
        """
        services = list(self._selected_services)
        self._settings.set_enabled_services(provider, services)

        msg = self.tr(
            "Services settings for provider '{0}' saved.".format(provider))
        logger.debug(msg)
        self._set_providers_services_status(msg, success=True)
        self.preferences_saved.emit()

    def _backend_connect(self):
        """
        Helper to connect to backend signals
        """
        sig = self._leap_signaler

        sig.prov_get_supported_services.connect(self._load_services)

        sig.srp_password_change_ok.connect(self._srp_change_password_ok)

        pwd_change_error = lambda: self._srp_change_password_problem(
            self.tr("There was a problem changing the password."))
        sig.srp_password_change_error.connect(pwd_change_error)

        pwd_change_badpw = lambda: self._srp_change_password_problem(
            self.tr("You did not enter a correct current password."))
        sig.srp_password_change_badpw.connect(pwd_change_badpw)

        sig.soledad_password_change_ok.connect(
            self._soledad_change_password_ok)

        sig.soledad_password_change_error.connect(
            self._soledad_change_password_problem)
