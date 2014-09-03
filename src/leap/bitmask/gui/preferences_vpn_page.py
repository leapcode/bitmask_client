# -*- coding: utf-8 -*-
# Copyright (C) 2014 LEAP
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
Widget for "vpn" preferences
"""

from PySide import QtCore, QtGui
from ui_preferences_vpn_page import Ui_PreferencesVpnPage

from leap.bitmask.config.leapsettings import LeapSettings


class PreferencesVpnPage(QtGui.QWidget):
    """
    Page in the preferences window that shows VPN settings
    """

    def __init__(self, parent, domain, backend, leap_signaler):
        """
        :param parent: parent object of the EIPPreferencesWindow.
        :type parent: QWidget

        :param domain: the selected by default domain.
        :type domain: unicode

        :param backend: Backend being used
        :type backend: Backend
        """
        QtGui.QWidget.__init__(self, parent)
        self.AUTOMATIC_GATEWAY_LABEL = self.tr("Automatic")

        self._settings = LeapSettings()
        self._leap_signaler = leap_signaler
        self._backend = backend

        # Load UI
        self.ui = Ui_PreferencesVpnPage()
        self.ui.setupUi(self)
        self.ui.flash_label.setVisible(False)

        # Connections
        self.ui.gateways_list.clicked.connect(self._save_selected_gateway)

        self._domain = domain
        self._backend_connect()
        self._backend.eip_get_gateways_list(domain=domain)

    def _flash_error(self, message):
        """
        Sets string for the flash message.

        :param message: the text to be displayed
        :type message: str
        """
        message = "<font color='red'><b>%s</b></font>" % (message,)
        self.ui.flash_label.setVisible(True)
        self.ui.flash_label.setText(message)

    # def _flash_success(self, message):
    #     """
    #     Sets string for the flash message.
    #
    #     :param message: the text to be displayed
    #     :type message: str
    #     """
    #     message = "<font color='green'><b>%s</b></font>" % (message,)
    #     self.ui.flash_label.setVisible(True)
    #     self.ui.flash_label.setText(message)

    @QtCore.Slot(str)
    def _save_selected_gateway(self, index):
        """
        TRIGGERS:
            self.ui.gateways_list.clicked

        Saves the new gateway setting to the configuration file.

        :param index: the current index of the selection.
        :type current_item: QModelIndex
        """
        item = self.ui.gateways_list.currentItem()

        if item.text() == self.AUTOMATIC_GATEWAY_LABEL:
            gateway = self._settings.GATEWAY_AUTOMATIC
        else:
            gateway = item.data(QtCore.Qt.UserRole)
        self._settings.set_selected_gateway(self._domain, gateway)
        self._backend.settings_set_selected_gateway(provider=self._domain,
                                                    gateway=gateway)

    @QtCore.Slot(list)
    def _update_gateways_list(self, gateways):
        """
        TRIGGERS:
            Signaler.eip_get_gateways_list

        :param gateways: a list of gateways
        :type gateways: list of unicode

        Add the available gateways and select the one stored in
        configuration file.
        """
        self.ui.gateways_list.clear()
        self.ui.gateways_list.addItem(self.AUTOMATIC_GATEWAY_LABEL)

        selected_gateway = self._settings.get_selected_gateway(
            self._domain)

        index = 0
        for idx, (gw_name, gw_ip, gw_country) in enumerate(gateways):
            gateway_text = "{0} ({1})".format(gw_name, gw_ip)
            item = QtGui.QListWidgetItem(self.ui.gateways_list)
            item.setText(gateway_text)
            item.setIcon(QtGui.QIcon(
                ":/images/countries/%s.png" % (gw_country.lower(),)))
            item.setData(QtCore.Qt.UserRole, gw_ip)
            if gw_ip == selected_gateway:
                index = idx + 1
        self.ui.gateways_list.setCurrentRow(index)

    @QtCore.Slot()
    def _gateways_list_error(self):
        """
        TRIGGERS:
            Signaler.eip_get_gateways_list_error

        An error has occurred retrieving the gateway list
        so we inform the user.
        """
        self._flash_error(
            self.tr("Error loading configuration file."))
        self.ui.gateways_list.setEnabled(False)

    def _backend_connect(self):
        sig = self._leap_signaler
        sig.eip_get_gateways_list.connect(self._update_gateways_list)
        sig.eip_get_gateways_list_error.connect(self._gateways_list_error)
