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
from passwordwindow import PasswordWindow
from leap.bitmask.services import get_service_display_name
from leap.bitmask.config.leapsettings import LeapSettings

logger = logging.getLogger(__name__)


class PreferencesAccountPage(QtGui.QWidget):

    def __init__(self, parent, account, app):
        """
        """
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_PreferencesAccountPage()
        self.ui.setupUi(self)

        self.account = account
        self.app = app

        self._selected_services = set()
        self.ui.change_password_label.setVisible(False)
        self.ui.provider_services_label.setVisible(False)

        self.ui.change_password_button.clicked.connect(
            self._show_change_password)
        app.signaler.prov_get_supported_services.connect(self._load_services)
        app.backend.provider_get_supported_services(domain=account.domain)

        if account.username is None:
            self.ui.change_password_label.setText(
                self.tr('You must be logged in to change your password.'))
            self.ui.change_password_label.setVisible(True)
            self.ui.change_password_button.setEnabled(False)

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
        services = list(self._selected_services)

        # We hide the maybe-visible status label after a change
        self.ui.provider_services_label.setVisible(False)

        # write to config
        self.app.settings.set_enabled_services(self.account.domain, services)

        # emit signal alerting change
        self.app.service_selection_changed.emit(self.account, services)

    @QtCore.Slot(str)
    def _load_services(self, services):
        """
        TRIGGERS:
            prov_get_supported_services

        Loads the services that the provider provides into the UI for
        the user to enable or disable.

        :param services: list of supported service names
        :type services: list of str
        """
        services_conf = self.account.services()

        self._selected_services = set()

        # remove existing checkboxes
        layout = self.ui.provider_services_layout
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        # add one checkbox per service and set the current value
        # from what is saved in settings.
        for service in services:
            try:
                checkbox = QtGui.QCheckBox(
                    get_service_display_name(service), self)
                self.ui.provider_services_layout.addWidget(checkbox)
                checkbox.stateChanged.connect(
                    partial(self._service_selection_changed, service))
                checkbox.setChecked(service in services_conf)
            except ValueError:
                logger.error("Something went wrong while trying to "
                             "load service %s" % (service,))

    @QtCore.Slot()
    def _show_change_password(self):
        change_password_window = PasswordWindow(self, self.account, self.app)
        change_password_window.show()
