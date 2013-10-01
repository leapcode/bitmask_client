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
import os
import logging

from functools import partial
from PySide import QtGui

from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.gui.ui_eippreferences import Ui_EIPPreferences
from leap.bitmask.services.eip.eipconfig import EIPConfig, VPNGatewaySelector

logger = logging.getLogger(__name__)


class EIPPreferencesWindow(QtGui.QDialog):
    """
    Window that displays the EIP preferences.
    """
    def __init__(self, parent):
        """
        :param parent: parent object of the EIPPreferencesWindow.
        :parent type: QWidget
        """
        QtGui.QDialog.__init__(self, parent)
        self.AUTOMATIC_GATEWAY_LABEL = self.tr("Automatic")

        self._settings = LeapSettings()

        # Load UI
        self.ui = Ui_EIPPreferences()
        self.ui.setupUi(self)
        self.ui.lblProvidersGatewayStatus.setVisible(False)

        # Connections
        self.ui.cbProvidersGateway.currentIndexChanged[unicode].connect(
            self._populate_gateways)

        self.ui.cbGateways.currentIndexChanged[unicode].connect(
            lambda x: self.ui.lblProvidersGatewayStatus.setVisible(False))

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
        self.ui.cbProvidersGateway.clear()
        for provider in self._settings.get_configured_providers():
            self.ui.cbProvidersGateway.addItem(provider)

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
            # disconnect previously connected save method
            self.ui.pbSaveGateway.clicked.disconnect()
        except RuntimeError:
            pass  # Signal was not connected

        # set the proper connection for the 'save' button
        save_gateway = partial(self._save_selected_gateway, domain)
        self.ui.pbSaveGateway.clicked.connect(save_gateway)

        eip_config = EIPConfig()
        provider_config = ProviderConfig.get_provider_config(domain)

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
