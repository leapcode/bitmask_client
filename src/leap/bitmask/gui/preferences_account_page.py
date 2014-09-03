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
Widget for "account" preferences
"""
import logging

from functools import partial

from PySide import QtCore, QtGui
from ui_preferences_account_page import Ui_PreferencesAccountPage

logger = logging.getLogger(__name__)

class PreferencesAccountPage(QtGui.QWidget):
    """

    """

    def __init__(self, parent):
        """
        """
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_PreferencesAccountPage()
        self.ui.setupUi(self)
        self.show()

        self._selected_services = set()
        #self._leap_signaler.prov_get_supported_services.connect(self._load_services)

    @QtCore.Slot()
    def set_soledad_ready(self):
        """
        TRIGGERS:
            parent.soledad_ready

        It notifies when the soledad object as ready to use.
        """
        #self.ui.lblPasswordChangeStatus.setVisible(False)
        #self.ui.gbPasswordChange.setEnabled(True)

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
