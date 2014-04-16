# -*- coding: utf-8 -*-
# eip_preferenceswindow.py
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
EIP Preferences window
"""
import logging

from functools import partial
from PySide import QtCore, QtGui

from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.gui.ui_eippreferences import Ui_EIPPreferences

logger = logging.getLogger(__name__)


class EIPPreferencesWindow(QtGui.QDialog):
    """
    Window that displays the EIP preferences.
    """
    def __init__(self, parent, domain, backend):
        """
        :param parent: parent object of the EIPPreferencesWindow.
        :type parent: QWidget
        :param domain: the selected by default domain.
        :type domain: unicode
        :param backend: Backend being used
        :type backend: Backend
        """
        QtGui.QDialog.__init__(self, parent)
        self.AUTOMATIC_GATEWAY_LABEL = self.tr("Automatic")

        self._settings = LeapSettings()
        self._backend = backend

        # Load UI
        self.ui = Ui_EIPPreferences()
        self.ui.setupUi(self)
        self.ui.lblProvidersGatewayStatus.setVisible(False)

        # Connections
        self.ui.cbProvidersGateway.currentIndexChanged[int].connect(
            self._populate_gateways)

        self.ui.cbGateways.currentIndexChanged[unicode].connect(
            lambda x: self.ui.lblProvidersGatewayStatus.setVisible(False))

        self._selected_domain = domain
        self._configured_providers = []

        self._backend_connect()
        self._add_configured_providers()

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
        providers = self._settings.get_configured_providers()
        if not providers:
            return

        self._backend.eip_get_initialized_providers(providers)

    def _load_providers_in_combo(self, providers):
        """
        SLOT
        TRIGGERS:
            Signaler.eip_get_initialized_providers

        Add the client's configured providers to the providers combo boxes.

        :param providers: the list of providers to add and whether each one is
                          initialized or not.
        :type providers: list of tuples (str, bool)
        """
        self.ui.cbProvidersGateway.clear()
        if not providers:
            self.ui.gbGatewaySelector.setEnabled(False)
            return

        for provider, is_initialized in providers:
            label = provider
            if not is_initialized:
                label += self.tr(" (uninitialized)")
            self.ui.cbProvidersGateway.addItem(label, userData=provider)

        # Select provider by name
        domain = self._selected_domain
        if domain is not None:
            provider_index = self.ui.cbProvidersGateway.findText(
                domain, QtCore.Qt.MatchStartsWith)
            self.ui.cbProvidersGateway.setCurrentIndex(provider_index)

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
            "Gateway settings for provider '{0}' saved.").format(provider)
        self._set_providers_gateway_status(msg, success=True)

    def _populate_gateways(self, domain_idx):
        """
        SLOT
        TRIGGERS:
            self.ui.cbProvidersGateway.currentIndexChanged[unicode]

        Loads the gateways that the provider provides into the UI for
        the user to select.

        :param domain: the domain index of the provider to load gateways from.
        :type domain: int
        """
        # We hide the maybe-visible status label after a change
        self.ui.lblProvidersGatewayStatus.setVisible(False)

        if domain_idx == -1:
            return

        domain = self.ui.cbProvidersGateway.itemData(domain_idx)
        self._selected_domain = domain

        self._backend.eip_get_gateways_list(domain)

    def _update_gateways_list(self, gateways):
        """
        SLOT
        TRIGGERS:
            Signaler.eip_get_gateways_list

        Add the available gateways and select the one stored in configuration
        file.
        """
        self.ui.pbSaveGateway.setEnabled(True)
        self.ui.cbGateways.setEnabled(True)

        self.ui.cbGateways.clear()
        self.ui.cbGateways.addItem(self.AUTOMATIC_GATEWAY_LABEL)

        try:
            # disconnect previously connected save method
            self.ui.pbSaveGateway.clicked.disconnect()
        except RuntimeError:
            pass  # Signal was not connected

        # set the proper connection for the 'save' button
        domain = self._selected_domain
        save_gateway = partial(self._save_selected_gateway, domain)
        self.ui.pbSaveGateway.clicked.connect(save_gateway)

        selected_gateway = self._settings.get_selected_gateway(
            self._selected_domain)

        index = 0
        for idx, (gw_name, gw_ip) in enumerate(gateways):
            gateway = "{0} ({1})".format(gw_name, gw_ip)
            self.ui.cbGateways.addItem(gateway, gw_ip)
            if gw_ip == selected_gateway:
                index = idx + 1

        self.ui.cbGateways.setCurrentIndex(index)

    def _gateways_list_error(self):
        """
        SLOT
        TRIGGERS:
            Signaler.eip_get_gateways_list_error

        An error has occurred retrieving the gateway list so we inform the
        user.
        """
        self._set_providers_gateway_status(
            self.tr("There was a problem with configuration files."),
            error=True)
        self.ui.pbSaveGateway.setEnabled(False)
        self.ui.cbGateways.setEnabled(False)

    def _gateways_list_uninitialized(self):
        """
        SLOT
        TRIGGERS:
            Signaler.eip_uninitialized_provider

        The requested provider in not initialized yet, so we give the user an
        error msg.
        """
        self._set_providers_gateway_status(
            self.tr("This is an uninitialized provider, please log in first."),
            error=True)
        self.ui.pbSaveGateway.setEnabled(False)
        self.ui.cbGateways.setEnabled(False)

    def _backend_connect(self):
        sig = self._backend.signaler
        sig.eip_get_gateways_list.connect(self._update_gateways_list)
        sig.eip_get_gateways_list_error.connect(self._gateways_list_error)
        sig.eip_uninitialized_provider.connect(
            self._gateways_list_uninitialized)
        sig.eip_get_initialized_providers.connect(
            self._load_providers_in_combo)
