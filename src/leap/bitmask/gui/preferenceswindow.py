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
import os
import logging

from functools import partial
from PySide import QtCore, QtGui

from leap.bitmask.gui.ui_preferences import Ui_Preferences
from leap.soledad.client import NoStorageSecret
from leap.bitmask.crypto.srpauth import SRPAuthBadPassword
from leap.bitmask.util.password import basic_password_checks
from leap.bitmask.services import get_supported
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.services.eip.eipconfig import EIPConfig, VPNGatewaySelector
from leap.bitmask.services import get_service_display_name

logger = logging.getLogger(__name__)


class PreferencesWindow(QtGui.QDialog):
    """
    Window that displays the preferences.
    """

    WEAK_PASSWORDS = ("123456", "qweasd", "qwerty", "password")

    def __init__(self, parent, srp_auth, leap_settings, standalone):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget
        :param srp_auth: SRPAuth object configured in the main app.
        :type srp_auth: SRPAuth
        :param standalone: If True, the application is running as standalone
                           and the preferences dialog should display some
                           messages according to this.
        :type standalone: bool
        """
        QtGui.QDialog.__init__(self, parent)
        self.AUTOMATIC_GATEWAY_LABEL = self.tr("Automatic")

        self._srp_auth = srp_auth
        self._settings = leap_settings
        self._standalone = standalone
        self._soledad = None

        # Load UI
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.ui.lblPasswordChangeStatus.setVisible(False)
        self.ui.lblProvidersServicesStatus.setVisible(False)
        self.ui.lblProvidersGatewayStatus.setVisible(False)

        self._selected_services = set()

        # Connections
        self.ui.pbChangePassword.clicked.connect(self._change_password)
        self.ui.cbProvidersServices.currentIndexChanged[unicode].connect(
            self._populate_services)
        self.ui.cbProvidersGateway.currentIndexChanged[unicode].connect(
            self._populate_gateways)

        self.ui.cbGateways.currentIndexChanged[unicode].connect(
            lambda x: self.ui.lblProvidersGatewayStatus.setVisible(False))

        if not self._settings.get_configured_providers():
            self.ui.gbEnabledServices.setEnabled(False)
        else:
            self._add_configured_providers()

    def set_soledad_ready(self, soledad):
        """
        SLOT
        TRIGGERS:
            parent.soledad_ready

        It sets the soledad object as ready to use.

        :param soledad: Soledad object configured in the main app.
        :type soledad: Soledad
        """
        self._soledad = soledad
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

    def _change_password(self):
        """
        SLOT
        TRIGGERS:
            self.ui.pbChangePassword.clicked

        Changes the user's password if the inputboxes are correctly filled.
        """
        username = self._srp_auth.get_username()
        current_password = self.ui.leCurrentPassword.text()
        new_password = self.ui.leNewPassword.text()
        new_password2 = self.ui.leNewPassword2.text()

        ok, msg = basic_password_checks(username, new_password, new_password2)

        if not ok:
            self._set_changing_password(False)
            self._set_password_change_status(msg, error=True)
            self.ui.leNewPassword.setFocus()
            return

        self._set_changing_password(True)
        d = self._srp_auth.change_password(current_password, new_password)
        d.addCallback(partial(self._change_password_success, new_password))
        d.addErrback(self._change_password_problem)

    def _change_password_success(self, new_password, _):
        """
        Callback used to display a successfully performed action.

        :param new_password: the new password for the user.
        :type new_password: str.
        :param _: the returned data from self._srp_auth.change_password
                  Ignored
        """
        logger.debug("SRP password changed successfully.")
        try:
            self._soledad.change_passphrase(str(new_password))
            logger.debug("Soledad password changed successfully.")
        except NoStorageSecret:
            logger.debug(
                "No storage secret for password change in Soledad.")

        self._set_password_change_status(
            self.tr("Password changed successfully."), success=True)
        self._clear_password_inputs()
        self._set_changing_password(False)

    def _change_password_problem(self, failure):
        """
        Errback called if there was a problem with the deferred.
        Also is used to display an error message.

        :param failure: the cause of the method failed.
        :type failure: twisted.python.Failure
        """
        logger.error("Error changing password: %s", (failure, ))
        problem = self.tr("There was a problem changing the password.")

        if failure.check(SRPAuthBadPassword):
            problem = self.tr("You did not enter a correct current password.")

        self._set_password_change_status(problem, error=True)

        self._set_changing_password(False)
        failure.trap(Exception)

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

    def _set_providers_gateway_status(self, status, success=False,
                                      error=False):
        """
        Sets the status label for the gateway change.

        :param status: status message to display, can be HTML
        :type status: str
        :param success: is set to True if we should display the
                        message as green
        :type success: bool
        :param error: is set to True if we should display the
                        message as red
        :type error: bool
        """
        if success:
            status = "<font color='green'><b>%s</b></font>" % (status,)
        elif error:
            status = "<font color='red'><b>%s</b></font>" % (status,)

        self.ui.lblProvidersGatewayStatus.setVisible(True)
        self.ui.lblProvidersGatewayStatus.setText(status)

    def _add_configured_providers(self):
        """
        Add the client's configured providers to the providers combo boxes.
        """
        self.ui.cbProvidersServices.clear()
        self.ui.cbProvidersGateway.clear()
        for provider in self._settings.get_configured_providers():
            self.ui.cbProvidersServices.addItem(provider)
            self.ui.cbProvidersGateway.addItem(provider)

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

        # We hide the maybe-visible status label after a change
        self.ui.lblProvidersServicesStatus.setVisible(False)

    def _populate_services(self, domain):
        """
        SLOT
        TRIGGERS:
            self.ui.cbProvidersServices.currentIndexChanged[unicode]

        Loads the services that the provider provides into the UI for
        the user to enable or disable.

        :param domain: the domain of the provider to load services from.
        :type domain: str
        """
        # We hide the maybe-visible status label after a change
        self.ui.lblProvidersServicesStatus.setVisible(False)

        if not domain:
            return

        provider_config = self._get_provider_config(domain)
        if provider_config is None:
            return

        # set the proper connection for the 'save' button
        try:
            self.ui.pbSaveServices.clicked.disconnect()
        except RuntimeError:
            pass  # Signal was not connected

        save_services = partial(self._save_enabled_services, domain)
        self.ui.pbSaveServices.clicked.connect(save_services)

        services = get_supported(provider_config.get_services())
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
                service_label = get_service_display_name(
                    service, self._standalone)
                checkbox.setText(service_label)

                self.ui.vlServices.addWidget(checkbox)
                checkbox.stateChanged.connect(
                    partial(self._service_selection_changed, service))

                checkbox.setChecked(service in services_conf)
            except ValueError:
                logger.error("Something went wrong while trying to "
                             "load service %s" % (service,))

    def _save_enabled_services(self, provider):
        """
        SLOT
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

    def _get_provider_config(self, domain):
        """
        Helper to return a valid Provider Config from the domain name.

        :param domain: the domain name of the provider.
        :type domain: str

        :rtype: ProviderConfig or None if there is a problem loading the config
        """
        provider_config = ProviderConfig()
        provider_config_path = os.path.join(
            "leap", "providers", domain, "provider.json")

        if not provider_config.load(provider_config_path):
            provider_config = None

        return provider_config

    def _save_selected_gateway(self, provider):
        """
        SLOT
        TRIGGERS:
            self.ui.pbSaveGateway.clicked

        Saves the new gateway setting to the configuration file.

        :param provider: the provider config that we need to save.
        :type provider: str
        """
        gateway = self.ui.cbGateways.currentText()

        if gateway == self.AUTOMATIC_GATEWAY_LABEL:
            gateway = self._settings.GATEWAY_AUTOMATIC
        else:
            idx = self.ui.cbGateways.currentIndex()
            gateway = self.ui.cbGateways.itemData(idx)

        self._settings.set_selected_gateway(provider, gateway)

        msg = self.tr(
            "Gateway settings for provider '{0}' saved.".format(provider))
        logger.debug(msg)
        self._set_providers_gateway_status(msg, success=True)

    def _populate_gateways(self, domain):
        """
        SLOT
        TRIGGERS:
            self.ui.cbProvidersGateway.currentIndexChanged[unicode]

        Loads the gateways that the provider provides into the UI for
        the user to select.

        :param domain: the domain of the provider to load gateways from.
        :type domain: str
        """
        # We hide the maybe-visible status label after a change
        self.ui.lblProvidersGatewayStatus.setVisible(False)

        if not domain:
            return

        try:
            # disconnect prevoiusly connected save method
            self.ui.pbSaveGateway.clicked.disconnect()
        except RuntimeError:
            pass  # Signal was not connected

        # set the proper connection for the 'save' button
        save_gateway = partial(self._save_selected_gateway, domain)
        self.ui.pbSaveGateway.clicked.connect(save_gateway)

        eip_config = EIPConfig()
        provider_config = self._get_provider_config(domain)

        eip_config_path = os.path.join("leap", "providers",
                                       domain, "eip-service.json")
        api_version = provider_config.get_api_version()
        eip_config.set_api_version(api_version)
        eip_loaded = eip_config.load(eip_config_path)

        if not eip_loaded or provider_config is None:
            self._set_providers_gateway_status(
                self.tr("There was a problem with configuration files."),
                error=True)
            return

        gateways = VPNGatewaySelector(eip_config).get_gateways_list()
        logger.debug(gateways)

        self.ui.cbGateways.clear()
        self.ui.cbGateways.addItem(self.AUTOMATIC_GATEWAY_LABEL)

        # Add the available gateways and
        # select the one stored in configuration file.
        selected_gateway = self._settings.get_selected_gateway(domain)
        index = 0
        for idx, (gw_name, gw_ip) in enumerate(gateways):
            gateway = "{0} ({1})".format(gw_name, gw_ip)
            self.ui.cbGateways.addItem(gateway, gw_ip)
            if gw_ip == selected_gateway:
                index = idx + 1

        self.ui.cbGateways.setCurrentIndex(index)
