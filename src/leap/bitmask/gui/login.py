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

The login sequence is the following:
    - _do_login
    - backend.provider_setup (check_name_resolution, check_https, download_provider_info)
        - on error:   _provider_setup_intermediate
        - on success: _load_provider_config
    - backend.provider_bootstrap (download_ca_cert, check_ca_fingerprint, check_api_certificate)
        - on error:   _provider_setup_intermediate
        - on success: _provider_config_loaded
    - backend.user_login
        - on error:   _authentication_error
        - on success: _authentication_finished

"""
import logging

from PySide import QtCore, QtGui
from ui_login import Ui_LoginWidget

# TODO: we should use a more granular signaling instead of passing error/ok as
# a result.
from leap.bitmask.backend.leapbackend import ERROR_KEY, PASSED_KEY
from leap.bitmask.config import flags
from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.gui.signaltracker import SignalTracker
from leap.bitmask.util import make_address
from leap.bitmask.util.credentials import USERNAME_REGEX
from leap.bitmask.util.keyring_helpers import has_keyring
from leap.bitmask.util.keyring_helpers import get_keyring
from leap.common.check import leap_assert_type

logger = logging.getLogger(__name__)


class LoginState(object):
    """
    This class holds the states related to the login sequence.
    """

    def __init__(self):
        # `wait_to_login` defines whether we should wait to start the login
        # sequence or we should start right away.
        # This is used, for instance, to hold on until EIP is started since the
        # firewall could block the login attempt.
        self.wait_to_login = False

        # This state indicates that the login sequence was required to start
        # but it was set on hold since we `wait_to_login` was True
        self.login_waiting = False

        # Full username of the logged user, with the format: 'user@provider'
        self.full_logged_username = None


class LoginWidget(QtGui.QWidget, SignalTracker):
    """
    Login widget that emits signals to display the wizard or to
    perform login.
    """
    login_start = QtCore.Signal()
    login_finished = QtCore.Signal()
    login_offline_finished = QtCore.Signal()
    login_failed = QtCore.Signal()
    logged_out = QtCore.Signal()

    MAX_STATUS_WIDTH = 40

    # Keyring
    KEYRING_KEY = "bitmask"

    def __init__(self, backend, signaler, parent=None):
        """
        Constructs the LoginWidget.

        :param backend: Backend being used
        :type backend: Backend
        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        :param parent: The parent widget for this widget
        :type parent: QWidget or None
        """
        QtGui.QWidget.__init__(self, parent)
        SignalTracker.__init__(self)

        self.ui = Ui_LoginWidget()
        self.ui.setupUi(self)

        self.ui.chkRemember.stateChanged.connect(self._remember_state_changed)
        self.ui.chkRemember.setEnabled(has_keyring())

        self.ui.lnUser.textChanged.connect(self._credentials_changed)
        self.ui.lnPassword.textChanged.connect(self._credentials_changed)

        self.ui.btnLogin.clicked.connect(self._do_login)
        self.ui.btnLogout.clicked.connect(self.do_logout)

        self.ui.lnUser.setValidator(
            QtGui.QRegExpValidator(QtCore.QRegExp(USERNAME_REGEX), self))

        self.ui.clblErrorMsg.hide()
        self.ui.clblErrorMsg.clicked.connect(self.ui.clblErrorMsg.hide)

        self.ui.lnUser.textEdited.connect(self.ui.clblErrorMsg.hide)
        self.ui.lnPassword.textEdited.connect(self.ui.clblErrorMsg.hide)

        self._settings = LeapSettings()
        self._backend = backend
        self._leap_signaler = signaler

        # the selected provider that we'll use to login
        self._provider = None

        self._state = LoginState()

        self._set_logged_out()

    @QtCore.Slot(int)
    def _remember_state_changed(self, state):
        """
        Save the remember state in the LeapSettings.

        :param state: the current state of the check box.
        :type state: int
        """
        # The possible state values of the checkbox (from QtCore.Qt.CheckState)
        # are: Checked, Unchecked and PartiallyChecked
        self._settings.set_remember(state == QtCore.Qt.Checked)

    @QtCore.Slot(unicode)
    def _credentials_changed(self, text):
        """
        TRIGGER:
            self.ui.lnUser.textChanged
            self.ui.lnPassword.textChanged

        Update the 'enabled' status of the login button depending if we have
        all the fields needed set.
        """
        enabled = self._provider and self.get_user() and self.get_password()
        enabled = bool(enabled)  # provider can be None

        self.ui.btnLogin.setEnabled(enabled)

    def wait_for_login(self, wait):
        """
        Set the wait flag to True/False so the next time that a login action is
        requested it will wait or not.

        If we set the wait to True and we have paused a login request before,
        this will trigger a login action.

        :param wait: whether we should wait or not on the next login request.
        :type wait: bool
        """
        self._state.wait_to_login = wait

        if not wait and self._state.login_waiting:
            logger.debug("No more waiting, triggering login sequence.")
            self._do_login()

    def set_provider(self, provider):
        """
        Set the provider to use in the login sequence.

        :param provider: the provider to use.
        :type provider: unicode
        """
        self._provider = provider

    def set_remember(self, value):
        """
        Check the remember user and password checkbox

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
        Return the user that appears in the widget.

        :rtype: unicode
        """
        return self.ui.lnUser.text()

    def get_logged_user(self):
        """
        Return the current logged user or None if no user is logged in.
        The return value has the format: 'user@provider'

        :rtype: unicode or None
        """
        return self._state.full_logged_username

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
        self.ui.chkRemember.setEnabled(enabled and has_keyring())

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
        login_or_cancel = self._do_cancel
        hide_remember = enabled

        if not enabled:
            text = self.tr("Log In")
            login_or_cancel = self._do_login

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

    def _check_login(self):
        """
        Check that we have the needed fields to do the actual login: provider,
        username and password.

        :return: True if everything's good to go, False otherwise.
        :rtype: bool
        """
        provider = self._provider
        username = self.get_user()
        password = self.get_password()

        if not provider:
            self.set_status(self.tr("Please select a valid provider"))
            return False

        if not username:
            self.set_status(self.tr("Please provide a valid username"))
            return False

        if not password:
            self.set_status(self.tr("Please provide a valid password"))
            return False

        return True

    def _set_logging_in(self):
        """
        Set the status of the widget to "Logging in".
        """
        self.set_status(self.tr("Logging in..."), error=False)
        self.set_enabled(False)
        self.ui.clblErrorMsg.hide()

    def _save_credentials(self):
        """
        If the user asked to remember the credentials, we save them into the
        keyring.
        """
        provider = self._provider
        username = self.get_user()
        password = self.get_password()

        self._settings.set_provider(provider)
        if self.get_remember() and has_keyring():
            # in the keyring and in the settings
            # we store the value 'usename@provider'
            full_user_id = make_address(username, provider).encode("utf8")
            try:
                keyring = get_keyring()
                keyring.set_password(self.KEYRING_KEY,
                                     full_user_id, password.encode("utf8"))
                # Only save the username if it was saved correctly in
                # the keyring
                self._settings.set_user(full_user_id)
            except Exception as e:
                logger.exception("Problem saving data to keyring. %r" % (e,))

    def do_login(self):
        """
        Start the login sequence.
        We check that we have the needed fields to do the actual login:
        provider, username and password.
        If everything is ok we perform the login.

        Note that the actual login won't be started if you set the
        `wait_to_login` flag, it will be scheduled to get started when you set
        that flag to False.

        :return: True if the login sequence started, False otherwise.
        :rtype: bool
        """
        ok = self._provider and self.get_user() and self.get_password()

        if ok:
            self._do_login()

        return bool(ok)

    def _do_login(self):
        """
        Start the login sequence.
        """
        if self._state.wait_to_login:
            logger.debug("Login delayed, waiting...")

            self._state.login_waiting = True
            self.ui.btnLogin.setEnabled(False)
            self.ui.btnLogin.setText(self.tr("Waiting..."))
            # explicitly process events to display the button's text change.
            QtCore.QCoreApplication.processEvents(0, 10)

            return
        else:
            self._state.login_waiting = False
            self.ui.btnLogin.setEnabled(True)

        self.login_start.emit()

        provider = self._provider
        if flags.OFFLINE:
            self._do_offline_login()
            return

        # connect to the backend signals, remember to disconnect after login.
        self._backend_connect()

        if self._check_login():
            self._set_logging_in()
            self._save_credentials()
            self._backend.provider_setup(provider=provider)

    def _do_cancel(self):
        logger.debug("Cancelling log in.")

        self._backend.provider_cancel_setup()
        self._backend.user_cancel_login()
        self._set_logged_out()

    @QtCore.Slot()
    def _set_login_cancelled(self):
        """
        TRIGGERS:
            Signaler.prov_cancelled_setup

        Re-enable the login widget and display a message for the cancelled
        operation.
        """
        self.set_status(self.tr("Log in cancelled by the user."))
        self.set_enabled(True)

    @QtCore.Slot(dict)
    def _provider_setup_intermediate(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_name_resolution
            self._backend.signaler.prov_https_connection

        Handle a possible problem during the provider setup process.
        If there was a problem, display it, otherwise it does nothing.
        """
        if not data[PASSED_KEY]:
            logger.error(data[ERROR_KEY])
            self._login_problem_provider()

    @QtCore.Slot()
    def _login_problem_provider(self):
        """
        Warn the user about a problem with the provider during login.
        """
        self.set_status(self.tr("Unable to login: Problem with provider"))
        self.set_enabled(True)

    @QtCore.Slot(dict)
    def _load_provider_config(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_download_provider_info

        Once the provider config has been downloaded, start the second
        part of the bootstrapping sequence.

        :param data: result from the last stage of the
                     backend.provider_setup()
        :type data: dict
        """
        if not data[PASSED_KEY]:
            logger.error(data[ERROR_KEY])
            self._login_problem_provider()
            return

        self._backend.provider_bootstrap(provider=self._provider)

    @QtCore.Slot(dict)
    def _provider_config_loaded(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_check_api_certificate

        Once the provider configuration is loaded, this starts the SRP
        authentication
        """
        if not data[PASSED_KEY]:
            logger.error(data[ERROR_KEY])
            self._login_problem_provider()
            return

        self._backend.user_login(provider=self._provider,
                                 username=self.get_user(),
                                 password=self.get_password())

    # TODO check this!
    def _do_offline_login(self):
        logger.debug("OFFLINE mode! bypassing remote login")
        # TODO reminder, we're not handling logout for offline mode.
        self._set_logged_in()
        self._logged_in_offline = True
        self._set_label_offline()
        self.login_offline_finished.emit()

    def _set_label_offline(self):
        """
        Set the login label to reflect offline status.
        """
        # TODO: figure out what widget to use for this. Maybe the window title?

    def _set_logged_in(self):
        """
        Set the widgets to the logged in state.
        """
        fullname = make_address(self.get_user(), self._provider)
        self._state.full_logged_username = fullname
        self.ui.login_widget.hide()
        self.ui.logged_widget.show()
        self.ui.lblUser.setText(fullname)

    @QtCore.Slot()
    def _authentication_finished(self):
        """
        TRIGGERS:
            self._srp_auth.authentication_finished

        The SRP auth was successful, set the login status.
        """
        self.set_status(self.tr("Succeeded"), error=False)
        self._set_logged_in()
        self.disconnect_and_untrack()

        if not flags.OFFLINE:
            self.login_finished.emit()

    @QtCore.Slot(unicode)
    def _authentication_error(self, msg):
        """
        TRIGGERS:
            Signaler.srp_auth_error
            Signaler.srp_auth_server_error
            Signaler.srp_auth_connection_error
            Signaler.srp_auth_bad_user_or_password

        Handle the authentication errors.

        :param msg: the message to show to the user.
        :type msg: unicode
        """
        self.set_status(msg)
        self.set_enabled(True)
        self.login_failed.emit()

    def _set_logged_out(self):
        """
        Set the widgets to the logged out state.
        """
        # TODO consider "logging out offline" too... how that would be ???
        self._state.full_logged_username = None

        self.ui.login_widget.show()
        self.ui.logged_widget.hide()

        self.set_password("")
        self.set_enabled(True)
        self.set_status("", error=False)

    @QtCore.Slot()
    def do_logout(self):
        """
        TRIGGER:
            self.ui.btnLogout.clicked

        Start the logout sequence and set the widgets to the "logging out"
        state.
        """
        if self._state.full_logged_username is not None:
            self._set_logging_out()
            self._backend.user_logout()
        else:
            logger.debug("Not logged in.")

    def _set_logging_out(self, logging_out=True):
        """
        Set the status of the logout button.

        logging_out == True:
            button text -> "Logging out..."
            button enabled -> False

        logging_out == False:
            button text -> "Logout
            button enabled -> True

        :param logging_out: wether we are logging out or not.
        :type logging_out: bool
        """
        if logging_out:
            self.ui.btnLogout.setText(self.tr("Logging out..."))
            self.ui.btnLogout.setEnabled(False)
        else:
            self.ui.btnLogout.setText(self.tr("Logout"))
            self.ui.btnLogout.setEnabled(True)
            self.ui.clblErrorMsg.hide()

    @QtCore.Slot()
    def _logout_error(self):
        """
        TRIGGER:
            self._srp_auth.logout_error

        Inform the user about a logout error.
        """
        self._set_logging_out(False)
        self.set_status(self.tr("Something went wrong with the logout."))

    @QtCore.Slot()
    def _logout_ok(self):
        """
        TRIGGER:
            self._srp_auth.logout_ok

        Switch the stackedWidget back to the login stage after logging out.
        """
        self._set_logging_out(False)
        self._set_logged_out()
        self.logged_out.emit()

    def load_user_from_keyring(self, saved_user):
        """
        Try to load a user from the keyring.

        :param saved_user: the saved username as user@domain
        :type saved_user: unicode

        :return: True if the user was loaded successfully, False otherwise.
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
            u_user = saved_user.encode("utf8")
            saved_password = keyring.get_password(self.KEYRING_KEY, u_user)
        except ValueError as e:
            logger.debug("Incorrect Password. %r." % (e,))

        if saved_password is not None:
            self.set_password(saved_password)
            return True

        return False

    def _backend_connect(self):
        """
        Connect to backend signals.

        We track the signals in order to disconnect them on demand.
        """
        sig = self._leap_signaler
        conntrack = self.connect_and_track
        auth_err = self._authentication_error

        # provider_setup signals
        conntrack(sig.prov_name_resolution, self._provider_setup_intermediate)
        conntrack(sig.prov_https_connection, self._provider_setup_intermediate)
        conntrack(sig.prov_download_provider_info, self._load_provider_config)

        # provider_bootstrap signals
        conntrack(sig.prov_download_ca_cert, self._provider_setup_intermediate)
        # XXX missing check_ca_fingerprint connection
        conntrack(sig.prov_check_api_certificate, self._provider_config_loaded)

        conntrack(sig.prov_problem_with_provider, self._login_problem_provider)
        conntrack(sig.prov_cancelled_setup, self._set_login_cancelled)

        # Login signals
        conntrack(sig.srp_auth_ok, self._authentication_finished)

        auth_error = lambda: auth_err(self.tr("Unknown error."))
        conntrack(sig.srp_auth_error, auth_error)

        auth_server_error = lambda: auth_err(self.tr(
            "There was a server problem with authentication."))
        conntrack(sig.srp_auth_server_error, auth_server_error)

        auth_connection_error = lambda: auth_err(self.tr(
            "Could not establish a connection."))
        conntrack(sig.srp_auth_connection_error, auth_connection_error)

        auth_bad_user_or_password = lambda: auth_err(self.tr(
            "Invalid username or password."))
        conntrack(sig.srp_auth_bad_user_or_password, auth_bad_user_or_password)

        # Logout signals
        sig.srp_logout_ok.connect(self._logout_ok)
        sig.srp_logout_error.connect(self._logout_error)
        # sig.srp_not_logged_in_error.connect(self._not_logged_in_error)
