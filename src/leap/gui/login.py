# -*- coding: utf-8 -*-
# login.py
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
Login widget implementation
"""
import logging

from PySide import QtCore, QtGui
from ui_login import Ui_LoginWidget

from leap.util.keyring_helpers import has_keyring

logger = logging.getLogger(__name__)


class LoginWidget(QtGui.QWidget):
    """
    Login widget that emits signals to display the wizard or to
    perform login.
    """

    # Emitted when the login button is clicked
    login = QtCore.Signal()
    # Emitted when the user selects "Other..." in the provider
    # combobox or click "Create Account"
    show_wizard = QtCore.Signal()

    MAX_STATUS_WIDTH = 40

    def __init__(self, settings, parent=None):
        """
        Constructs the LoginWidget.

        :param settings: client wide settings
        :type settings: LeapSettings
        :param parent: The parent widget for this widget
        :type parent: QWidget or None
        """
        QtGui.QWidget.__init__(self, parent)

        self._settings = settings
        self._selected_provider_index = -1

        self.ui = Ui_LoginWidget()
        self.ui.setupUi(self)

        self.ui.chkRemember.stateChanged.connect(
            self._remember_state_changed)
        self.ui.chkRemember.setEnabled(has_keyring())

        self.ui.lnPassword.setEchoMode(QtGui.QLineEdit.Password)

        self.ui.btnLogin.clicked.connect(self.login)
        self.ui.lnPassword.returnPressed.connect(self.login)

        self.ui.lnUser.returnPressed.connect(self._focus_password)

        self.ui.cmbProviders.currentIndexChanged.connect(
            self._current_provider_changed)
        self.ui.btnCreateAccount.clicked.connect(
            self.show_wizard)

    def _remember_state_changed(self, state):
        """
        Saves the remember state in the LeapSettings

        :param state: possible stats can be Checked, Unchecked and
        PartiallyChecked
        :type state: QtCore.Qt.CheckState
        """
        enable = True if state == QtCore.Qt.Checked else False
        self._settings.set_remember(enable)

    def set_providers(self, provider_list):
        """
        Set the provider list to provider_list plus an "Other..." item
        that triggers the wizard

        :param provider_list: list of providers
        :type provider_list: list of str
        """
        self.ui.cmbProviders.blockSignals(True)
        self.ui.cmbProviders.clear()
        self.ui.cmbProviders.addItems(provider_list + [self.tr("Other...")])
        self.ui.cmbProviders.blockSignals(False)

    def select_provider_by_name(self, name):
        """
        Given a provider name/domain, it selects it in the combobox

        :param name: name or domain for the provider
        :type name: str
        """
        provider_index = self.ui.cmbProviders.findText(name)
        self.ui.cmbProviders.setCurrentIndex(provider_index)

    def get_selected_provider(self):
        """
        Returns the selected provider in the combobox
        """
        return self.ui.cmbProviders.currentText()

    def set_remember(self, value):
        """
        Checks the remember user and password checkbox

        :param value: True to mark it checked, False otherwise
        :type value: bool
        """
        self.ui.chkRemember.setChecked(value)

    def get_remember(self):
        """
        Returns the remember checkbox state

        :rtype: bool
        """
        return self.ui.chkRemember.isChecked()

    def set_user(self, user):
        """
        Sets the user and focuses on the next field, password.

        :param user: user to set the field to
        :type user: str
        """
        self.ui.lnUser.setText(user)
        self._focus_password()

    def get_user(self):
        """
        Returns the user that appears in the widget

        :rtype: str
        """
        return self.ui.lnUser.text()

    def set_password(self, password):
        """
        Sets the password for the widget

        :param password: password to set
        :type password: str
        """
        self.ui.lnPassword.setText(password)

    def get_password(self):
        """
        Returns the password that appears in the widget

        :rtype: str
        """
        return self.ui.lnPassword.text()

    def set_status(self, status, error=True):
        """
        Sets the status label at the login stage to status

        :param status: status message
        :type status: str
        """
        if len(status) > self.MAX_STATUS_WIDTH:
            status = status[:self.MAX_STATUS_WIDTH] + "..."
        if error:
            status = "<font color='red'><b>%s</b></font>" % (status,)
        self.ui.lblStatus.setText(status)

    def set_enabled(self, enabled=False):
        """
        Enables or disables all the login widgets

        :param enabled: wether they should be enabled or not
        :type enabled: bool
        """
        self.ui.lnUser.setEnabled(enabled)
        self.ui.lnPassword.setEnabled(enabled)
        self.ui.btnLogin.setEnabled(enabled)
        self.ui.chkRemember.setEnabled(enabled)
        self.ui.cmbProviders.setEnabled(enabled)

    def _focus_password(self):
        """
        Focuses in the password lineedit
        """
        self.ui.lnPassword.setFocus()

    def _current_provider_changed(self, param):
        """
        SLOT
        TRIGGERS: self.ui.cmbProviders.currentIndexChanged
        """
        if param == (self.ui.cmbProviders.count() - 1):
            self.show_wizard.emit()
            # Leave the previously selected provider in the combobox
            prev_provider = 0
            if self._selected_provider_index != -1:
                prev_provider = self._selected_provider_index
            self.ui.cmbProviders.blockSignals(True)
            self.ui.cmbProviders.setCurrentIndex(prev_provider)
            self.ui.cmbProviders.blockSignals(False)
        else:
            self._selected_provider_index = param
