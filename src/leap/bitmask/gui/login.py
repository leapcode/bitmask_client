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

from leap.bitmask.config import flags
from leap.bitmask.util import make_address
from leap.bitmask.util.keyring_helpers import has_keyring
from leap.bitmask.util.keyring_helpers import get_keyring
from leap.common.check import leap_assert_type

logger = logging.getLogger(__name__)


class LoginWidget(QtGui.QWidget):
    """
    Login widget that emits signals to display the wizard or to
    perform login.
    """
    # Emitted when the login button is clicked
    login = QtCore.Signal()
    logged_in_signal = QtCore.Signal()
    cancel_login = QtCore.Signal()
    logout = QtCore.Signal()

    # Emitted when the user selects "Other..." in the provider
    # combobox or click "Create Account"
    show_wizard = QtCore.Signal()

    MAX_STATUS_WIDTH = 40

    BARE_USERNAME_REGEX = r"^[A-Za-z\d_]+$"

    # Keyring
    KEYRING_KEY = "bitmask"

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

        self.ui.btnLogout.clicked.connect(
            self.logout)

        username_re = QtCore.QRegExp(self.BARE_USERNAME_REGEX)
        self.ui.lnUser.setValidator(
            QtGui.QRegExpValidator(username_re, self))

        self.logged_out()

        self.ui.btnLogout.clicked.connect(self.start_logout)

        self.ui.clblErrorMsg.hide()
        self.ui.clblErrorMsg.clicked.connect(self.ui.clblErrorMsg.hide)

        self.ui.lnUser.textEdited.connect(self.ui.clblErrorMsg.hide)
        self.ui.lnPassword.textEdited.connect(self.ui.clblErrorMsg.hide)

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
        Returns the user that appears in the widget.

        :rtype: unicode
        """
        return self.ui.lnUser.text()

    def set_password(self, password):
        """
        Sets the password for the widget

        :param password: password to set
        :type password: unicode
        """
        self.ui.lnPassword.setText(password)

    def get_password(self):
        """
        Returns the password that appears in the widget

        :rtype: unicode
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
            self.ui.clblErrorMsg.show()
            self.ui.clblErrorMsg.setText(status)
        else:
            self.ui.lblStatus.setText(status)

    def set_enabled(self, enabled=False):
        """
        Enables or disables all the login widgets

        :param enabled: wether they should be enabled or not
        :type enabled: bool
        """
        self.ui.lnUser.setEnabled(enabled)
        self.ui.lnPassword.setEnabled(enabled)
        self.ui.chkRemember.setEnabled(enabled)
        self.ui.cmbProviders.setEnabled(enabled)

        self._set_cancel(not enabled)

    def set_logout_btn_enabled(self, enabled):
        """
        Enables or disables the logout button.

        :param enabled: wether they should be enabled or not
        :type enabled: bool
        """
        self.ui.btnLogout.setEnabled(enabled)

    def _set_cancel(self, enabled=False):
        """
        Enables or disables the cancel action in the "log in" process.

        :param enabled: wether it should be enabled or not
        :type enabled: bool
        """
        text = self.tr("Cancel")
        login_or_cancel = self.cancel_login
        hide_remember = enabled

        if not enabled:
            text = self.tr("Log In")
            login_or_cancel = self.login

        self.ui.btnLogin.setText(text)

        self.ui.btnLogin.clicked.disconnect()
        self.ui.btnLogin.clicked.connect(login_or_cancel)
        self.ui.chkRemember.setVisible(not hide_remember)
        self.ui.lblStatus.setVisible(hide_remember)

    def _focus_password(self):
        """
        Focuses in the password lineedit
        """
        self.ui.lnPassword.setFocus()

    def _current_provider_changed(self, param):
    @QtCore.Slot(int)
        """
        TRIGGERS:
            self.ui.cmbProviders.currentIndexChanged
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

    def start_login(self):
        """
        Setups the login widgets for actually performing the login and
        performs some basic checks.

        :returns: True if everything's good to go, False otherwise
        :rtype: bool
        """
        username = self.get_user()
        password = self.get_password()
        provider = self.get_selected_provider()

        self._enabled_services = self._settings.get_enabled_services(
            self.get_selected_provider())

        if len(provider) == 0:
            self.set_status(
                self.tr("Please select a valid provider"))
            return False

        if len(username) == 0:
            self.set_status(
                self.tr("Please provide a valid username"))
            return False

        if len(password) == 0:
            self.set_status(
                self.tr("Please provide a valid password"))
            return False

        self.set_status(self.tr("Logging in..."), error=False)
        self.set_enabled(False)
        self.ui.clblErrorMsg.hide()

        self._settings.set_provider(provider)
        if self.get_remember() and has_keyring():
            # in the keyring and in the settings
            # we store the value 'usename@provider'
            full_user_id = make_address(username, provider).encode("utf8")
            try:
                keyring = get_keyring()
                keyring.set_password(self.KEYRING_KEY,
                                     full_user_id,
                                     password.encode("utf8"))
                # Only save the username if it was saved correctly in
                # the keyring
                self._settings.set_user(full_user_id)
            except Exception as e:
                logger.exception("Problem saving data to keyring. %r"
                                 % (e,))
        return True

    def logged_in(self):
        """
        Sets the widgets to the logged in state
        """
        self.ui.login_widget.hide()
        self.ui.logged_widget.show()
        self.ui.lblUser.setText(make_address(
            self.get_user(), self.get_selected_provider()))

        if flags.OFFLINE is False:
            self.logged_in_signal.emit()

    def logged_out(self):
        """
        Sets the widgets to the logged out state
        """
        # TODO consider "logging out offline" too...
        # how that would be ???

        self.ui.login_widget.show()
        self.ui.logged_widget.hide()

        self.set_password("")
        self.set_enabled(True)
        self.set_status("", error=False)

    def start_logout(self):
        """
        Sets the widgets to the logging out state
        """
        self.ui.btnLogout.setText(self.tr("Logging out..."))
        self.ui.btnLogout.setEnabled(False)

    def done_logout(self):
        """
        Sets the widgets to the logged out state
        """
        self.ui.btnLogout.setText(self.tr("Logout"))
        self.ui.btnLogout.setEnabled(True)
        self.ui.clblErrorMsg.hide()

    def load_user_from_keyring(self, saved_user):
        """
        Tries to load a user from the keyring, returns True if it was
        loaded successfully, False otherwise.

        :param saved_user: String containing the saved username as
                           user@domain
        :type saved_user: unicode

        :rtype: bool
        """
        leap_assert_type(saved_user, unicode)

        try:
            username, domain = saved_user.split('@')
        except ValueError as e:
            # if the saved_user does not contain an '@'
            logger.error('Username@provider malformed. %r' % (e, ))
            return False

        self.set_user(username)

        self.set_remember(True)

        saved_password = None
        try:
            keyring = get_keyring()
            saved_password = keyring.get_password(self.KEYRING_KEY,
                                                  saved_user
                                                  .encode("utf8"))
        except ValueError as e:
            logger.debug("Incorrect Password. %r." % (e,))

        if saved_password is not None:
            self.set_password(saved_password)
            return True

        return False
