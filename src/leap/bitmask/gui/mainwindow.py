# -*- coding: utf-8 -*-
# mainwindow.py
# Copyright (C) 2013, 2014 LEAP
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
Main window for Bitmask.
"""
import logging
import time

from datetime import datetime

import psutil

from PySide import QtCore, QtGui

from leap.bitmask import __version__ as VERSION
from leap.bitmask import __version_hash__ as VERSION_HASH

# TODO: we should use a more granular signaling instead of passing error/ok as
# a result.
from leap.bitmask.backend.leapbackend import ERROR_KEY, PASSED_KEY

from leap.bitmask.config import flags
from leap.bitmask.config.leapsettings import LeapSettings

from leap.bitmask.gui.advanced_key_management import AdvancedKeyManagement
from leap.bitmask.gui.eip_preferenceswindow import EIPPreferencesWindow
from leap.bitmask.gui.eip_status import EIPStatusWidget
from leap.bitmask.gui.loggerwindow import LoggerWindow
from leap.bitmask.gui.login import LoginWidget
from leap.bitmask.gui.mail_status import MailStatusWidget
from leap.bitmask.gui.preferenceswindow import PreferencesWindow
from leap.bitmask.gui.systray import SysTray
from leap.bitmask.gui.wizard import Wizard

from leap.bitmask.platform_init import IS_WIN, IS_MAC, IS_LINUX
from leap.bitmask.platform_init.initializers import init_platform
from leap.bitmask.platform_init.initializers import init_signals

from leap.bitmask.backend.backend_proxy import BackendProxy
from leap.bitmask.backend.leapsignaler import LeapSignaler

from leap.bitmask.services.eip import conductor as eip_conductor
from leap.bitmask.services.mail import conductor as mail_conductor

from leap.bitmask.services import EIP_SERVICE, MX_SERVICE

from leap.bitmask.util import autostart, make_address
from leap.bitmask.util.keyring_helpers import has_keyring
from leap.bitmask.logs.leap_log_handler import LeapLogHandler

if IS_WIN:
    from leap.bitmask.platform_init.locks import WindowsLock
    from leap.bitmask.platform_init.locks import raise_window_ack

from leap.common.events import register
from leap.common.events import events_pb2 as proto

from leap.mail.imap.service.imap import IMAP_PORT

from ui_mainwindow import Ui_MainWindow

QtDelayedCall = QtCore.QTimer.singleShot
logger = logging.getLogger(__name__)


class MainWindow(QtGui.QMainWindow):
    """
    Main window for login and presenting status updates to the user
    """
    # Signals
    eip_needs_login = QtCore.Signal([])
    offline_mode_bypass_login = QtCore.Signal([])
    new_updates = QtCore.Signal(object)
    raise_window = QtCore.Signal([])
    soledad_ready = QtCore.Signal([])
    logout = QtCore.Signal([])
    all_services_stopped = QtCore.Signal()

    # We use this flag to detect abnormal terminations
    user_stopped_eip = False

    # We give EIP some time to come up before starting soledad anyway
    EIP_START_TIMEOUT = 60000  # in milliseconds

    # We give the services some time to a halt before forcing quit.
    SERVICES_STOP_TIMEOUT = 20000  # in milliseconds

    def __init__(self, start_hidden=False, backend_pid=None):
        """
        Constructor for the client main window

        :param start_hidden: Set to true if the app should not show the window
                             but just the tray.
        :type start_hidden: bool
        """
        QtGui.QMainWindow.__init__(self)
        autostart.set_autostart(True)

        # register leap events ########################################
        register(signal=proto.UPDATER_NEW_UPDATES,
                 callback=self._new_updates_available,
                 reqcbk=lambda req, resp: None)  # make rpc call async
        register(signal=proto.RAISE_WINDOW,
                 callback=self._on_raise_window_event,
                 reqcbk=lambda req, resp: None)  # make rpc call async
        # end register leap events ####################################

        self._updates_content = ""

        # setup UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.menuBar().setNativeMenuBar(not IS_LINUX)

        self._backend = BackendProxy()

        # periodically check if the backend is alive
        self._backend_checker = QtCore.QTimer(self)
        self._backend_checker.timeout.connect(self._check_backend_status)
        self._backend_checker.start(2000)

        self._leap_signaler = LeapSignaler()
        self._leap_signaler.start()

        self._settings = LeapSettings()
        # gateway = self._settings.get_selected_gateway(provider)
        # self._backend.settings_set_selected_gateway(provider, gateway)

        # Login Widget
        self._login_widget = LoginWidget(self._settings, self)
        self.ui.loginLayout.addWidget(self._login_widget)

        # Mail Widget
        self._mail_status = MailStatusWidget(self)
        self.ui.mailLayout.addWidget(self._mail_status)

        # Qt Signal Connections #####################################
        # TODO separate logic from ui signals.

        self._login_widget.login.connect(self._login)
        self._login_widget.cancel_login.connect(self._cancel_login)
        self._login_widget.show_wizard.connect(self._launch_wizard)
        self._login_widget.logout.connect(self._logout)

        # EIP Control redux #########################################
        self._eip_conductor = eip_conductor.EIPConductor(
            self._settings, self._backend, self._leap_signaler)
        self._eip_status = EIPStatusWidget(self, self._eip_conductor,
                                           self._leap_signaler)

        init_signals.eip_missing_helpers.connect(
            self._disable_eip_missing_helpers)

        self.ui.eipLayout.addWidget(self._eip_status)
        self._eip_conductor.add_eip_widget(self._eip_status)

        self._eip_conductor.connect_signals()
        self._eip_conductor.qtsigs.connected_signal.connect(
            self._on_eip_connection_connected)
        self._eip_conductor.qtsigs.connected_signal.connect(
            self._maybe_run_soledad_setup_checks)

        self.offline_mode_bypass_login.connect(
            self._maybe_run_soledad_setup_checks)

        self.eip_needs_login.connect(self._eip_status.disable_eip_start)
        self.eip_needs_login.connect(self._disable_eip_start_action)

        self._already_started_eip = False
        self._trying_to_start_eip = False

        self._already_started_eip = False
        self._soledad_started = False

        # This is created once we have a valid provider config
        self._srp_auth = None
        self._logged_user = None
        self._logged_in_offline = False

        # Set used to track the services being stopped and need wait.
        self._services_being_stopped = {}

        # used to know if we are in the final steps of quitting
        self._quitting = False
        self._finally_quitting = False

        self._backend_connected_signals = []
        self._backend_connect()

        self.ui.action_preferences.triggered.connect(self._show_preferences)
        self.ui.action_eip_preferences.triggered.connect(
            self._show_eip_preferences)
        self.ui.action_about_leap.triggered.connect(self._about)
        self.ui.action_quit.triggered.connect(self.quit)
        self.ui.action_wizard.triggered.connect(self._launch_wizard)
        self.ui.action_show_logs.triggered.connect(self._show_logger_window)
        self.ui.action_help.triggered.connect(self._help)
        self.ui.action_create_new_account.triggered.connect(
            self._launch_wizard)

        self.ui.action_advanced_key_management.triggered.connect(
            self._show_AKM)

        if IS_MAC:
            self.ui.menuFile.menuAction().setText(self.tr("File"))

        self.raise_window.connect(self._do_raise_mainwindow)

        # Used to differentiate between real quits and close to tray
        self._really_quit = False

        self._systray = None

        # XXX separate actions into a different module.
        self._action_mail_status = QtGui.QAction(self.tr("Mail is OFF"), self)
        self._mail_status.set_action_mail_status(self._action_mail_status)

        self._action_eip_startstop = QtGui.QAction("", self)
        self._eip_status.set_action_eip_startstop(self._action_eip_startstop)

        self._action_visible = QtGui.QAction(self.tr("Hide Main Window"), self)
        self._action_visible.triggered.connect(self._toggle_visible)

        # disable buttons for now, may come back later.
        # self.ui.btnPreferences.clicked.connect(self._show_preferences)
        # self.ui.btnEIPPreferences.clicked.connect(self._show_eip_preferences)

        self._enabled_services = []
        self._ui_mx_visible = True
        self._ui_eip_visible = True

        self._provider_details = None

        # last minute UI manipulations

        self._center_window()
        self.ui.lblNewUpdates.setVisible(False)
        self.ui.btnMore.setVisible(False)
        #########################################
        # We hide this in height temporarily too
        self.ui.lblNewUpdates.resize(0, 0)
        self.ui.btnMore.resize(0, 0)
        #########################################
        self.ui.btnMore.clicked.connect(self._updates_details)
        if flags.OFFLINE is True:
            self._set_label_offline()

        # Services signals/slots connection
        self.new_updates.connect(self._react_to_new_updates)

        # XXX should connect to mail_conductor.start_mail_service instead
        self.soledad_ready.connect(self._start_smtp_bootstrapping)
        self.soledad_ready.connect(self._start_imap_service)
        # ################################ end Qt Signals connection ########

        init_platform()

        self._wizard = None
        self._wizard_firstrun = False

        self._logger_window = None

        self._start_hidden = start_hidden
        self._backend_pid = backend_pid

        self._mail_conductor = mail_conductor.MailConductor(self._backend)
        self._mail_conductor.connect_mail_signals(self._mail_status)

        self.logout.connect(self._mail_conductor.stop_mail_services)

        # Eip machine is a public attribute where the state machine for
        # the eip connection will be available to the different components.
        # Remember that this will not live in the  +1600LOC mainwindow for
        # all the eternity, so at some point we will be moving this to
        # the EIPConductor or some other clever component that we will
        # instantiate from here.

        # start event machines
        # TODO should encapsulate all actions into one object
        self._eip_conductor.start_eip_machine(
            action=self._action_eip_startstop)
        self._mail_conductor.start_mail_machine()

        if self._first_run():
            self._wizard_firstrun = True
            self._disconnect_and_untrack()
            self._wizard = Wizard(backend=self._backend,
                                  leap_signaler=self._leap_signaler)
            # Give this window time to finish init and then show the wizard
            QtDelayedCall(1, self._launch_wizard)
            self._wizard.accepted.connect(self._finish_init)
            self._wizard.rejected.connect(self._rejected_wizard)
        else:
            # during finish_init, we disable the eip start button
            # so this has to be done after eip_machine is started
            self._finish_init()

    def _not_logged_in_error(self):
        """
        Handle the 'not logged in' backend error if we try to do an operation
        that requires to be logged in.
        """
        logger.critical("You are trying to do an operation that requires "
                        "log in first.")
        QtGui.QMessageBox.critical(
            self, self.tr("Application error"),
            self.tr("You are trying to do an operation "
                    "that requires logging in first."))

    def _connect_and_track(self, signal, method):
        """
        Helper to connect signals and keep track of them.

        :param signal: the signal to connect to.
        :type signal: QtCore.Signal
        :param method: the method to call when the signal is triggered.
        :type method: callable, Slot or Signal
        """
        self._backend_connected_signals.append((signal, method))
        signal.connect(method)

    def _backend_bad_call(self, data):
        """
        Callback for debugging bad backend calls

        :param data: data from the backend about the problem
        :type data: str
        """
        logger.error("Bad call to the backend:")
        logger.error(data)

    @QtCore.Slot()
    def _check_backend_status(self):
        """
        TRIGGERS:
            self._backend_checker.timeout

        Check that the backend is running. Otherwise show an error to the user.
        """
        online = self._backend.online
        if not online:
            logger.critical("Backend is not online.")
            QtGui.QMessageBox.critical(
                self, self.tr("Application error"),
                self.tr("There is a problem contacting the backend, please "
                        "restart Bitmask."))
            self._backend_checker.stop()

    def _backend_connect(self, only_tracked=False):
        """
        Connect to backend signals.

        We track some signals in order to disconnect them on demand.
        For instance, in the wizard we need to connect to some signals that are
        already connected in the mainwindow, so to avoid conflicts we do:
            - disconnect signals needed in wizard (`_disconnect_and_untrack`)
            - use wizard
            - reconnect disconnected signals (we use the `only_tracked` param)

        :param only_tracked: whether or not we should connect only the signals
                             that we are tracking to disconnect later.
        :type only_tracked: bool
        """
        sig = self._leap_signaler
        conntrack = self._connect_and_track
        auth_err = self._authentication_error

        conntrack(sig.prov_name_resolution, self._intermediate_stage)
        conntrack(sig.prov_https_connection, self._intermediate_stage)
        conntrack(sig.prov_download_ca_cert, self._intermediate_stage)
        conntrack(sig.prov_download_provider_info, self._load_provider_config)
        conntrack(sig.prov_check_api_certificate, self._provider_config_loaded)
        conntrack(sig.prov_check_api_certificate, self._get_provider_details)

        conntrack(sig.prov_problem_with_provider, self._login_problem_provider)
        conntrack(sig.prov_cancelled_setup, self._set_login_cancelled)

        conntrack(sig.prov_get_details, self._provider_get_details)

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
        conntrack(sig.srp_logout_ok, self._logout_ok)
        conntrack(sig.srp_logout_error, self._logout_error)
        conntrack(sig.srp_not_logged_in_error, self._not_logged_in_error)

        # EIP bootstrap signals
        conntrack(sig.eip_config_ready, self._eip_intermediate_stage)
        conntrack(sig.eip_client_certificate_ready, self._finish_eip_bootstrap)

        ###################################################
        # Add tracked signals above this, untracked below!
        ###################################################
        if only_tracked:
            return

        # We don't want to disconnect some signals so don't track them:

        sig.backend_bad_call.connect(self._backend_bad_call)

        sig.prov_unsupported_client.connect(self._needs_update)
        sig.prov_unsupported_api.connect(self._incompatible_api)
        sig.prov_get_all_services.connect(self._provider_get_all_services)

        # EIP start signals ==============================================

        self._eip_conductor.connect_backend_signals()
        sig.eip_can_start.connect(self._backend_can_start_eip)
        sig.eip_cannot_start.connect(self._backend_cannot_start_eip)

        sig.eip_dns_error.connect(self._eip_dns_error)

        sig.eip_get_gateway_country_code.connect(self._set_eip_provider)
        sig.eip_no_gateway.connect(self._set_eip_provider)

        # ==================================================================

        # Soledad signals
        # TODO delegate connection to soledad bootstrapper
        sig.soledad_bootstrap_failed.connect(
            self._mail_status.set_soledad_failed)
        sig.soledad_bootstrap_finished.connect(self._on_soledad_ready)

        sig.soledad_offline_failed.connect(
            self._mail_status.set_soledad_failed)
        sig.soledad_offline_finished.connect(self._on_soledad_ready)

        sig.soledad_invalid_auth_token.connect(
            self._mail_status.set_soledad_invalid_auth_token)

        # TODO: connect this with something
        # sig.soledad_cancelled_bootstrap.connect()

    def _disconnect_and_untrack(self):
        """
        Helper to disconnect the tracked signals.

        Some signals are emitted from the wizard, and we want to
        ignore those.
        """
        for signal, method in self._backend_connected_signals:
            try:
                signal.disconnect(method)
            except RuntimeError:
                pass  # Signal was not connected

        self._backend_connected_signals = []

    @QtCore.Slot()
    def _rejected_wizard(self):
        """
        TRIGGERS:
            self._wizard.rejected

        Called if the wizard has been cancelled or closed before
        finishing.
        This is executed for the first run wizard only. Any other execution of
        the wizard won't reach this point.
        """
        providers = self._settings.get_configured_providers()
        has_provider_on_disk = len(providers) != 0
        if not has_provider_on_disk:
            # if we don't have any provider configured (included a pinned
            # one) we can't use the application, so quit.
            self.quit()
        else:
            # This happens if the user finishes the provider
            # setup but does not register
            self._wizard = None
            self._backend_connect(only_tracked=True)
            if self._wizard_firstrun:
                self._finish_init()

    @QtCore.Slot()
    def _launch_wizard(self):
        """
        TRIGGERS:
            self._login_widget.show_wizard
            self.ui.action_wizard.triggered

        Also called in first run.

        Launches the wizard, creating the object itself if not already
        there.
        """
        if self._wizard is None:
            self._disconnect_and_untrack()
            self._wizard = Wizard(backend=self._backend,
                                  leap_signaler=self._leap_signaler)
            self._wizard.accepted.connect(self._finish_init)
            self._wizard.rejected.connect(self._rejected_wizard)

        self.setVisible(False)
        # Do NOT use exec_, it will use a child event loop!
        # Refer to http://www.themacaque.com/?p=1067 for funny details.
        self._wizard.show()
        if IS_MAC:
            self._wizard.raise_()
        self._wizard.finished.connect(self._wizard_finished)
        self._settings.set_skip_first_run(True)

    @QtCore.Slot()
    def _wizard_finished(self):
        """
        TRIGGERS:
            self._wizard.finished

        Called when the wizard has finished.
        """
        self.setVisible(True)

    def _get_leap_logging_handler(self):
        """
        Gets the leap handler from the top level logger

        :return: a logging handler or None
        :rtype: LeapLogHandler or None
        """
        # TODO this can be a function, does not need
        # to be a method.
        leap_logger = logging.getLogger('leap')
        for h in leap_logger.handlers:
            if isinstance(h, LeapLogHandler):
                return h
        return None

    @QtCore.Slot()
    def _show_logger_window(self):
        """
        TRIGGERS:
            self.ui.action_show_logs.triggered

        Displays the window with the history of messages logged until now
        and displays the new ones on arrival.
        """
        if self._logger_window is None:
            leap_log_handler = self._get_leap_logging_handler()
            if leap_log_handler is None:
                logger.error('Leap logger handler not found')
                return
            else:
                self._logger_window = LoggerWindow(handler=leap_log_handler)
                self._logger_window.setVisible(
                    not self._logger_window.isVisible())
        else:
            self._logger_window.setVisible(not self._logger_window.isVisible())

    @QtCore.Slot()
    def _show_AKM(self):
        """
        TRIGGERS:
            self.ui.action_advanced_key_management.triggered

        Displays the Advanced Key Management dialog.
        """
        domain = self._login_widget.get_selected_provider()
        logged_user = "{0}@{1}".format(self._logged_user, domain)

        details = self._provider_details
        mx_provided = False
        if details is not None:
            mx_provided = MX_SERVICE in details['services']

        # XXX: handle differently not logged in user?
        akm = AdvancedKeyManagement(self, mx_provided, logged_user,
                                    self._backend, self._soledad_started)
        akm.show()

    @QtCore.Slot()
    def _show_preferences(self):
        """
        TRIGGERS:
            self.ui.btnPreferences.clicked (disabled for now)
            self.ui.action_preferences

        Displays the preferences window.
        """
        user = self._logged_user
        domain = self._login_widget.get_selected_provider()
        mx_provided = False
        if self._provider_details is not None:
            mx_provided = MX_SERVICE in self._provider_details['services']
        preferences = PreferencesWindow(self, user, domain, self._backend,
                                        self._soledad_started, mx_provided,
                                        self._leap_signaler)

        self.soledad_ready.connect(preferences.set_soledad_ready)
        preferences.show()
        preferences.preferences_saved.connect(self._update_eip_enabled_status)

    @QtCore.Slot()
    def _update_eip_enabled_status(self):
        """
        TRIGGER:
            PreferencesWindow.preferences_saved

        Enable or disable the EIP start/stop actions and stop EIP if the user
        disabled that service.

        :returns: if the eip actions were enabled or disabled
        :rtype: bool
        """
        settings = self._settings
        default_provider = settings.get_defaultprovider()

        if default_provider is None:
            logger.warning("Trying to update eip enabled status but there's no"
                           " default provider. Disabling EIP for the time"
                           " being...")
            self._backend_cannot_start_eip()
            return

        self._trying_to_start_eip = settings.get_autostart_eip()
        self._backend.eip_can_start(domain=default_provider)

        # If we don't want to start eip, we leave everything
        # initialized to quickly start it
        if not self._trying_to_start_eip:
            self._backend.eip_setup(provider=default_provider,
                                    skip_network=True)

    def _backend_can_start_eip(self):
        """
        TRIGGER:
            self._backend.signaler.eip_can_start

        If EIP can be started right away, and the client is configured
        to do so, start it. Otherwise it leaves everything in place
        for the user to click Turn ON.
        """
        settings = self._settings
        default_provider = settings.get_defaultprovider()
        enabled_services = []
        if default_provider is not None:
            enabled_services = settings.get_enabled_services(default_provider)

        eip_enabled = False
        if EIP_SERVICE in enabled_services:
            eip_enabled = True
            if default_provider is not None:
                self._eip_status.enable_eip_start()
                self._eip_status.set_eip_status("")
            else:
                # we don't have an usable provider
                # so the user needs to log in first
                self._eip_status.disable_eip_start()
        else:
            self._eip_status.disable_eip_start()
            self._eip_status.set_eip_status(self.tr("Disabled"))

        if eip_enabled and self._trying_to_start_eip:
            self._trying_to_start_eip = False
            self._try_autostart_eip()

    def _backend_cannot_start_eip(self):
        """
        TRIGGER:
            self._backend.signaler.eip_cannot_start

        If EIP can't be started right away, get the UI to what it
        needs to look like and waits for a proper login/eip bootstrap.
        """
        settings = self._settings
        default_provider = settings.get_defaultprovider()
        enabled_services = []
        if default_provider is not None:
            enabled_services = settings.get_enabled_services(default_provider)

        if EIP_SERVICE in enabled_services:
            # we don't have a usable provider
            # so the user needs to log in first
            self._eip_status.disable_eip_start()
        else:
            self._eip_status.disable_eip_start()
            self._eip_status.set_eip_status(self.tr("Disabled"))

    @QtCore.Slot()
    def _disable_eip_missing_helpers(self):
        """
        TRIGGERS:
            init_signals.missing_helpers

        Set the missing_helpers flag, so we can disable EIP.
        """
        self._eip_status.missing_helpers = True

    @QtCore.Slot()
    def _show_eip_preferences(self):
        """
        TRIGGERS:
            self.ui.btnEIPPreferences.clicked
            self.ui.action_eip_preferences (disabled for now)

        Displays the EIP preferences window.
        """
        domain = self._login_widget.get_selected_provider()
        pref = EIPPreferencesWindow(self, domain,
                                    self._backend, self._leap_signaler)
        pref.show()

    #
    # updates
    #

    def _new_updates_available(self, req):
        """
        Callback for the new updates event

        :param req: Request type
        :type req: leap.common.events.events_pb2.SignalRequest
        """
        self.new_updates.emit(req)

    @QtCore.Slot(object)
    def _react_to_new_updates(self, req):
        """
        TRIGGERS:
            self.new_updates

        Displays the new updates label and sets the updates_content

        :param req: Request type
        :type req: leap.common.events.events_pb2.SignalRequest
        """
        self.moveToThread(QtCore.QCoreApplication.instance().thread())
        self.ui.lblNewUpdates.setVisible(True)
        self.ui.btnMore.setVisible(True)
        self._updates_content = req.content

    @QtCore.Slot()
    def _updates_details(self):
        """
        TRIGGERS:
            self.ui.btnMore.clicked

        Parses and displays the updates details
        """
        msg = self.tr("The Bitmask app is ready to update, please"
                      " restart the application.")

        # We assume that if there is nothing in the contents, then
        # the Bitmask bundle is what needs updating.
        if len(self._updates_content) > 0:
            files = self._updates_content.split(", ")
            files_str = ""
            for f in files:
                final_name = f.replace("/data/", "")
                final_name = final_name.replace(".thp", "")
                files_str += final_name
                files_str += "\n"
            msg += self.tr(" The following components will be updated:\n%s") \
                % (files_str,)

        QtGui.QMessageBox.information(self,
                                      self.tr("Updates available"),
                                      msg)

    @QtCore.Slot()
    def _finish_init(self):
        """
        TRIGGERS:
            self._wizard.accepted

        Also called at the end of the constructor if not first run.

        Implements the behavior after either constructing the
        mainwindow object, loading the saved user/password, or after
        the wizard has been executed.
        """
        # XXX: May be this can be divided into two methods?

        providers = self._settings.get_configured_providers()
        self._login_widget.set_providers(providers)
        self._show_systray()

        if not self._start_hidden:
            self.show()
            if IS_MAC:
                self.raise_()

        self._show_hide_unsupported_services()

        if self._wizard:
            possible_username = self._wizard.get_username()
            possible_password = self._wizard.get_password()

            # select the configured provider in the combo box
            domain = self._wizard.get_domain()
            self._login_widget.select_provider_by_name(domain)

            self._login_widget.set_remember(self._wizard.get_remember())
            self._enabled_services = list(self._wizard.get_services())
            self._settings.set_enabled_services(
                self._login_widget.get_selected_provider(),
                self._enabled_services)
            if possible_username is not None:
                self._login_widget.set_user(possible_username)
            if possible_password is not None:
                self._login_widget.set_password(possible_password)
                self._login()
            else:
                self.eip_needs_login.emit()

            self._wizard = None
            self._backend_connect(only_tracked=True)
        else:
            self._update_eip_enabled_status()

            domain = self._settings.get_provider()
            if domain is not None:
                self._login_widget.select_provider_by_name(domain)

            if not self._settings.get_remember():
                # nothing to do here
                return

            saved_user = self._settings.get_user()

            if saved_user is not None and has_keyring():
                if self._login_widget.load_user_from_keyring(saved_user):
                    self._login()

    def _show_hide_unsupported_services(self):
        """
        Given a set of configured providers, it creates a set of
        available services among all of them and displays the service
        widgets of only those.

        This means, for example, that with just one provider with EIP
        only, the mail widget won't be displayed.
        """
        providers = self._settings.get_configured_providers()

        self._backend.provider_get_all_services(providers=providers)

    def _provider_get_all_services(self, services):
        self._set_eip_visible(EIP_SERVICE in services)
        self._set_mx_visible(MX_SERVICE in services)

    def _set_mx_visible(self, visible):
        """
        Change the visibility of MX_SERVICE related UI components.

        :param visible: whether the components should be visible or not.
        :type visible: bool
        """
        # only update visibility if it is something to change
        if self._ui_mx_visible ^ visible:
            self.ui.mailWidget.setVisible(visible)
            self.ui.lineUnderEmail.setVisible(visible)
            self._action_mail_status.setVisible(visible)
            self._ui_mx_visible = visible

    def _set_eip_visible(self, visible):
        """
        Change the visibility of EIP_SERVICE related UI components.

        :param visible: whether the components should be visible or not.
        :type visible: bool
        """
        # NOTE: we use xor to avoid the code being run if the visibility hasn't
        # changed. This is meant to avoid the eip menu being displayed floating
        # around at start because the systray isn't rendered yet.
        if self._ui_eip_visible ^ visible:
            self.ui.eipWidget.setVisible(visible)
            self.ui.lineUnderEIP.setVisible(visible)
            self._eip_menu.setVisible(visible)
            self._ui_eip_visible = visible

    def _set_label_offline(self):
        """
        Set the login label to reflect offline status.
        """
        provider = ""
        if not self._logged_in_offline:
            provider = self.ui.lblLoginProvider.text()

        self.ui.lblLoginProvider.setText(provider + self.tr(" (offline mode)"))

    #
    # systray
    #

    def _show_systray(self):
        """
        Sets up the systray icon
        """
        if self._systray is not None:
            self._systray.setVisible(True)
            return

        # Placeholder action
        # It is temporary to display the tray as designed
        help_action = QtGui.QAction(self.tr("Help"), self)
        help_action.setEnabled(False)

        systrayMenu = QtGui.QMenu(self)
        systrayMenu.addAction(self._action_visible)
        systrayMenu.addSeparator()

        eip_status_label = "{0}: {1}".format(
            self._eip_conductor.eip_name, self.tr("OFF"))
        self._eip_menu = eip_menu = systrayMenu.addMenu(eip_status_label)
        eip_menu.addAction(self._action_eip_startstop)
        self._eip_status.set_eip_status_menu(eip_menu)
        systrayMenu.addSeparator()
        systrayMenu.addAction(self._action_mail_status)
        systrayMenu.addSeparator()
        systrayMenu.addAction(self.ui.action_quit)
        self._systray = SysTray(self)
        self._systray.setContextMenu(systrayMenu)
        self._systray.setIcon(self._eip_status.ERROR_ICON_TRAY)
        self._systray.setVisible(True)
        self._systray.activated.connect(self._tray_activated)

        self._mail_status.set_systray(self._systray)
        self._eip_status.set_systray(self._systray)

        if self._start_hidden:
            hello = lambda: self._systray.showMessage(
                self.tr('Hello!'),
                self.tr('Bitmask has started in the tray.'))
            # we wait for the systray to be ready
            QtDelayedCall(1000, hello)

    @QtCore.Slot(int)
    def _tray_activated(self, reason=None):
        """
        TRIGGERS:
            self._systray.activated

        :param reason: the reason why the tray got activated.
        :type reason: int

        Displays the context menu from the tray icon
        """
        self._update_hideshow_menu()

        context_menu = self._systray.contextMenu()
        if not IS_MAC:
            # for some reason, context_menu.show()
            # is failing in a way beyond my understanding.
            # (not working the first time it's clicked).
            # this works however.
            context_menu.exec_(self._systray.geometry().center())

    def _update_hideshow_menu(self):
        """
        Updates the Hide/Show main window menu text based on the
        visibility of the window.
        """
        get_action = lambda visible: (
            self.tr("Show Main Window"),
            self.tr("Hide Main Window"))[int(visible)]

        # set labels
        visible = self.isVisible() and self.isActiveWindow()
        self._action_visible.setText(get_action(visible))

    @QtCore.Slot()
    def _toggle_visible(self):
        """
        TRIGGERS:
            self._action_visible.triggered

        Toggles the window visibility
        """
        visible = self.isVisible() and self.isActiveWindow()

        if not visible:
            QtGui.QApplication.setQuitOnLastWindowClosed(True)
            self.show()
            if IS_LINUX:
                # On ubuntu, activateWindow doesn't work reliably, so
                # we do the following as a workaround. See
                # https://bugreports.qt-project.org/browse/QTBUG-24932
                # for more details
                QtGui.QX11Info.setAppUserTime(0)
            self.activateWindow()
            self.raise_()
        else:
            # We set this in order to avoid dialogs shutting down the
            # app on close, as they will be the only visible window.
            # e.g.: PreferencesWindow, LoggerWindow
            QtGui.QApplication.setQuitOnLastWindowClosed(False)
            self.hide()

        # Wait a bit until the window visibility has changed so
        # the menu is set with the correct value.
        QtDelayedCall(500, self._update_hideshow_menu)

    def _center_window(self):
        """
        Centers the mainwindow based on the desktop geometry
        """
        geometry = self._settings.get_geometry()
        state = self._settings.get_windowstate()

        if geometry is None:
            app = QtGui.QApplication.instance()
            width = app.desktop().width()
            height = app.desktop().height()
            window_width = self.size().width()
            window_height = self.size().height()
            x = (width / 2.0) - (window_width / 2.0)
            y = (height / 2.0) - (window_height / 2.0)
            self.move(x, y)
        else:
            self.restoreGeometry(geometry)

        if state is not None:
            self.restoreState(state)

    @QtCore.Slot()
    def _about(self):
        """
        TRIGGERS:
            self.ui.action_about_leap.triggered

        Display the About Bitmask dialog
        """
        today = datetime.now().date()
        greet = ("Happy New 1984!... or not ;)<br><br>"
                 if today.month == 1 and today.day < 15 else "")
        QtGui.QMessageBox.about(
            self, self.tr("About Bitmask - %s") % (VERSION,),
            self.tr("Version: <b>%s</b> (%s)<br>"
                    "<br>%s"
                    "Bitmask is the Desktop client application for "
                    "the LEAP platform, supporting encrypted internet "
                    "proxy, secure email, and secure chat (coming soon).<br>"
                    "<br>"
                    "LEAP is a non-profit dedicated to giving "
                    "all internet users access to secure "
                    "communication. Our focus is on adapting "
                    "encryption technology to make it easy to use "
                    "and widely available. <br>"
                    "<br>"
                    "<a href='https://leap.se'>More about LEAP"
                    "</a>") % (VERSION, VERSION_HASH[:10], greet))

    @QtCore.Slot()
    def _help(self):
        """
        TRIGGERS:
            self.ui.action_help.triggered

        Display the Bitmask help dialog.
        """
        # TODO: don't hardcode!
        smtp_port = 2013

        url = ("<a href='https://addons.mozilla.org/es/thunderbird/"
               "addon/bitmask/'>bitmask addon</a>")

        msg = self.tr(
            "<strong>Instructions to use mail:</strong><br>"
            "If you use Thunderbird you can use the Bitmask extension helper. "
            "Search for 'Bitmask' in the add-on manager or download it "
            "from: {0}.<br><br>"
            "You can configure Bitmask manually with these options:<br>"
            "<em>"
            "   Incoming -> IMAP, port: {1}<br>"
            "   Outgoing -> SMTP, port: {2}<br>"
            "   Username -> your bitmask username.<br>"
            "   Password -> does not matter, use any text. "
            " Just don't leave it empty and don't use your account's password."
            "</em>").format(url, IMAP_PORT, smtp_port)
        QtGui.QMessageBox.about(self, self.tr("Bitmask Help"), msg)

    def _needs_update(self):
        """
        Display a warning dialog to inform the user that the app needs update.
        """
        url = "https://dl.bitmask.net/"
        msg = self.tr(
            "The current client version is not supported "
            "by this provider.<br>"
            "Please update to latest version.<br><br>"
            "You can get the latest version from "
            "<a href='{0}'>{1}</a>").format(url, url)
        QtGui.QMessageBox.warning(self, self.tr("Update Needed"), msg)

    def _incompatible_api(self):
        """
        Display a warning dialog to inform the user that the provider has an
        incompatible API.
        """
        msg = self.tr(
            "This provider is not compatible with the client.<br><br>"
            "Error: API version incompatible.")
        QtGui.QMessageBox.warning(self, self.tr("Incompatible Provider"), msg)

    def changeEvent(self, e):
        """
        Reimplements the changeEvent method to minimize to tray
        """
        if not IS_MAC and \
           QtGui.QSystemTrayIcon.isSystemTrayAvailable() and \
           e.type() == QtCore.QEvent.WindowStateChange and \
           self.isMinimized():
            self._toggle_visible()
            e.accept()
            return
        QtGui.QMainWindow.changeEvent(self, e)

    def closeEvent(self, e):
        """
        Reimplementation of closeEvent to close to tray
        """
        if not e.spontaneous():
            # if the system requested the `close` then we should quit.
            self.quit()
            return

        if QtGui.QSystemTrayIcon.isSystemTrayAvailable() and \
                not self._really_quit:
            self._toggle_visible()
            e.ignore()
            return

        self._settings.set_geometry(self.saveGeometry())
        self._settings.set_windowstate(self.saveState())

        QtGui.QMainWindow.closeEvent(self, e)

    def _first_run(self):
        """
        Returns True if there are no configured providers. False otherwise

        :rtype: bool
        """
        providers = self._settings.get_configured_providers()
        has_provider_on_disk = len(providers) != 0
        skip_first_run = self._settings.get_skip_first_run()
        return not (has_provider_on_disk and skip_first_run)

    def _download_provider_config(self):
        """
        Starts the bootstrapping sequence. It will download the
        provider configuration if it's not present, otherwise will
        emit the corresponding signals inmediately
        """
        domain = self._login_widget.get_selected_provider()
        self._backend.provider_setup(provider=domain)

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
        if data[PASSED_KEY]:
            selected_provider = self._login_widget.get_selected_provider()
            self._backend.provider_bootstrap(provider=selected_provider)
        else:
            logger.error(data[ERROR_KEY])
            self._login_problem_provider()

    @QtCore.Slot()
    def _login_problem_provider(self):
        """
        Warns the user about a problem with the provider during login.
        """
        self._login_widget.set_status(
            self.tr("Unable to login: Problem with provider"))
        self._login_widget.set_enabled(True)

    @QtCore.Slot()
    def _login(self):
        """
        TRIGGERS:
            self._login_widget.login

        Starts the login sequence. Which involves bootstrapping the
        selected provider if the selection is valid (not empty), then
        start the SRP authentication, and as the last step
        bootstrapping the EIP service
        """
        # TODO most of this could ve handled by the login widget,
        # but we'd have to move lblLoginProvider into the widget itself,
        # instead of having it as a top-level attribute.
        if flags.OFFLINE is True:
            logger.debug("OFFLINE mode! bypassing remote login")
            # TODO reminder, we're not handling logout for offline
            # mode.
            self._login_widget.logged_in()
            self._logged_in_offline = True
            self._set_label_offline()
            self.offline_mode_bypass_login.emit()
        else:
            self.ui.action_create_new_account.setEnabled(False)
            if self._login_widget.start_login():
                self._download_provider_config()

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
        self._login_widget.set_status(msg)
        self._login_widget.set_enabled(True)
        self.ui.action_create_new_account.setEnabled(True)

    @QtCore.Slot()
    def _cancel_login(self):
        """
        TRIGGERS:
            self._login_widget.cancel_login

        Stops the login sequence.
        """
        logger.debug("Cancelling log in.")
        self._cancel_ongoing_defers()

    def _cancel_ongoing_defers(self):
        """
        Cancel the running defers to avoid app blocking.
        """
        # XXX: Should we stop all the backend defers?
        self._backend.provider_cancel_setup()
        self._backend.user_cancel_login()
        self._backend.soledad_cancel_bootstrap()
        self._backend.soledad_close()

        self._soledad_started = False

    @QtCore.Slot()
    def _set_login_cancelled(self):
        """
        TRIGGERS:
            Signaler.prov_cancelled_setup fired by
            self._backend.provider_cancel_setup()

        This method re-enables the login widget and display a message for
        the cancelled operation.
        """
        self._login_widget.set_status(self.tr("Log in cancelled by the user."))
        self._login_widget.set_enabled(True)

    @QtCore.Slot(dict)
    def _provider_config_loaded(self, data):
        """
        TRIGGERS:
            self._backend.signaler.prov_check_api_certificate

        Once the provider configuration is loaded, this starts the SRP
        authentication
        """
        if data[PASSED_KEY]:
            username = self._login_widget.get_user()
            password = self._login_widget.get_password()

            self._show_hide_unsupported_services()

            domain = self._login_widget.get_selected_provider()
            self._backend.user_login(provider=domain,
                                     username=username, password=password)
        else:
            logger.error(data[ERROR_KEY])
            self._login_problem_provider()

    @QtCore.Slot()
    def _authentication_finished(self):
        """
        TRIGGERS:
            self._srp_auth.authentication_finished

        Once the user is properly authenticated, try starting the EIP
        service
        """
        self._login_widget.set_status(self.tr("Succeeded"), error=False)

        self._logged_user = self._login_widget.get_user()
        user = self._logged_user
        domain = self._login_widget.get_selected_provider()
        full_user_id = make_address(user, domain)
        self._mail_conductor.userid = full_user_id
        self._start_eip_bootstrap()
        self.ui.action_create_new_account.setEnabled(True)

        # if soledad/mail is enabled:
        if MX_SERVICE in self._enabled_services:
            btn_enabled = self._login_widget.set_logout_btn_enabled
            btn_enabled(False)
            sig = self._leap_signaler
            sig.soledad_bootstrap_failed.connect(lambda: btn_enabled(True))
            sig.soledad_bootstrap_finished.connect(lambda: btn_enabled(True))

        if MX_SERVICE not in self._provider_details['services']:
            self._set_mx_visible(False)

    def _start_eip_bootstrap(self):
        """
        Changes the stackedWidget index to the EIP status one and
        triggers the eip bootstrapping.
        """

        self._login_widget.logged_in()
        domain = self._login_widget.get_selected_provider()
        self.ui.lblLoginProvider.setText(domain)

        self._enabled_services = self._settings.get_enabled_services(domain)

        # TODO separate UI from logic.
        if self._provides_mx_and_enabled():
            self._mail_status.about_to_start()
        else:
            self._mail_status.set_disabled()

        self._maybe_start_eip()

    @QtCore.Slot()
    def _get_provider_details(self):
        """
        TRIGGERS:
            prov_check_api_certificate

        Set the attributes to know if the EIP and MX services are supported
        and enabled.
        This is triggered right after the provider has been set up.
        """
        domain = self._login_widget.get_selected_provider()
        lang = QtCore.QLocale.system().name()
        self._backend.provider_get_details(domain=domain, lang=lang)

    @QtCore.Slot()
    def _provider_get_details(self, details):
        """
        Set the details for the just downloaded provider.

        :param details: the details of the provider.
        :type details: dict
        """
        self._provider_details = details

    def _provides_mx_and_enabled(self):
        """
        Defines if the current provider provides mx and if we have it enabled.

        :returns: True if provides and is enabled, False otherwise
        :rtype: bool
        """
        domain = self._login_widget.get_selected_provider()
        enabled_services = self._settings.get_enabled_services(domain)

        mx_enabled = MX_SERVICE in enabled_services
        mx_provided = False
        if self._provider_details is not None:
            mx_provided = MX_SERVICE in self._provider_details['services']

        return mx_enabled and mx_provided

    def _provides_eip_and_enabled(self):
        """
        Defines if the current provider provides eip and if we have it enabled.

        :returns: True if provides and is enabled, False otherwise
        :rtype: bool
        """
        domain = self._login_widget.get_selected_provider()
        enabled_services = self._settings.get_enabled_services(domain)

        eip_enabled = EIP_SERVICE in enabled_services
        eip_provided = False
        if self._provider_details is not None:
            eip_provided = EIP_SERVICE in self._provider_details['services']

        return eip_enabled and eip_provided

    def _maybe_run_soledad_setup_checks(self):
        """
        Conditionally start Soledad.
        """
        # TODO split.
        if not self._provides_mx_and_enabled() and not flags.OFFLINE:
            logger.debug("Provider does not offer MX, but it is enabled.")
            return

        username = self._login_widget.get_user()
        password = unicode(self._login_widget.get_password())
        provider_domain = self._login_widget.get_selected_provider()

        if flags.OFFLINE:
            full_user_id = make_address(username, provider_domain)
            uuid = self._settings.get_uuid(full_user_id)
            self._mail_conductor.userid = full_user_id

            if uuid is None:
                # We don't need more visibility at the moment,
                # this is mostly for internal use/debug for now.
                logger.warning("Sorry! Log-in at least one time.")
                return
            self._backend.soledad_load_offline(username=full_user_id,
                                               password=password, uuid=uuid)
        else:
            if self._logged_user is not None:
                domain = self._login_widget.get_selected_provider()
                self._backend.soledad_bootstrap(username=username,
                                                domain=domain,
                                                password=password)

    ###################################################################
    # Service control methods: soledad

    @QtCore.Slot()
    def _on_soledad_ready(self):
        """
        TRIGGERS:
            Signaler.soledad_bootstrap_finished

        Actions to take when Soledad is ready.
        """
        logger.debug("Done bootstrapping Soledad")

        self._soledad_started = True
        self.soledad_ready.emit()

    ###################################################################
    # Service control methods: smtp

    @QtCore.Slot()
    def _start_smtp_bootstrapping(self):
        """
        TRIGGERS:
            self.soledad_ready
        """
        if flags.OFFLINE is True:
            logger.debug("not starting smtp in offline mode")
            return

        if self._provides_mx_and_enabled():
            self._mail_conductor.start_smtp_service(download_if_needed=True)

    ###################################################################
    # Service control methods: imap

    @QtCore.Slot()
    def _start_imap_service(self):
        """
        TRIGGERS:
            self.soledad_ready
        """
        # TODO in the OFFLINE mode we should also modify the  rules
        # in the mail state machine so it shows that imap is active
        # (but not smtp since it's not yet ready for offline use)
        if self._provides_mx_and_enabled() or flags.OFFLINE:
            self._mail_conductor.start_imap_service()

    # end service control methods (imap)

    ###################################################################
    # Service control methods: eip

    @QtCore.Slot()
    def _disable_eip_start_action(self):
        """
        Disables the EIP start action in the systray menu.
        """
        self._action_eip_startstop.setEnabled(False)

    @QtCore.Slot()
    def _enable_eip_start_action(self):
        """
        Enables the EIP start action in the systray menu.
        """
        self._action_eip_startstop.setEnabled(True)
        self._eip_status.enable_eip_start()

    @QtCore.Slot()
    def _on_eip_connection_connected(self):
        """
        TRIGGERS:
            self._eip_conductor.qtsigs.connected_signal

        This is a little workaround for connecting the vpn-connected
        signal that currently is beeing processed under status_panel.
        After the refactor to EIPConductor this should not be necessary.
        """
        self._already_started_eip = True

        domain = self._login_widget.get_selected_provider()
        self._settings.set_defaultprovider(domain)

        self._backend.eip_get_gateway_country_code(domain=domain)

        # check for connectivity
        self._backend.eip_check_dns(domain=domain)

    @QtCore.Slot()
    def _set_eip_provider(self, country_code=None):
        """
        TRIGGERS:
            Signaler.eip_get_gateway_country_code
            Signaler.eip_no_gateway

        Set the current provider and country code in the eip status widget.
        """
        domain = self._login_widget.get_selected_provider()
        self._eip_status.set_provider(domain, country_code)

    @QtCore.Slot()
    def _eip_dns_error(self):
        """
        Trigger this if we don't have a working DNS resolver.
        """
        domain = self._login_widget.get_selected_provider()
        msg = self.tr(
            "The server at {0} can't be found, because the DNS lookup "
            "failed. DNS is the network service that translates a "
            "website's name to its Internet address. Either your computer "
            "is having trouble connecting to the network, or you are "
            "missing some helper files that are needed to securely use "
            "DNS while {1} is active. To install these helper files, quit "
            "this application and start it again."
        ).format(domain, self._eip_conductor.eip_name)

        QtGui.QMessageBox.critical(self, self.tr("Connection Error"), msg)

    def _try_autostart_eip(self):
        """
        Tries to autostart EIP
        """
        settings = self._settings
        default_provider = settings.get_defaultprovider()
        self._enabled_services = settings.get_enabled_services(
            default_provider)

        if settings.get_autostart_eip():
            self._maybe_start_eip(autostart=True)

    # eip boostrapping, config etc...

    def _maybe_start_eip(self, autostart=False):
        """
        Start the EIP bootstrapping sequence if the client is configured to
        do so.

        :param autostart: we are autostarting EIP when this is True
        :type autostart: bool
        """
        # during autostart we assume that the provider provides EIP
        if autostart:
            should_start = EIP_SERVICE in self._enabled_services
        else:
            should_start = self._provides_eip_and_enabled()

        missing_helpers = self._eip_status.missing_helpers
        already_started = self._already_started_eip
        can_start = (should_start
                     and not already_started
                     and not missing_helpers)

        if can_start:
            if self._eip_status.is_cold_start:
                self._backend.tear_fw_down()
            # XXX this should be handled by the state machine.
            self._enable_eip_start_action()
            self._eip_status.set_eip_status(
                self.tr("Starting..."))
            self._eip_status.eip_button.setEnabled(False)

            domain = self._login_widget.get_selected_provider()
            self._backend.eip_setup(provider=domain)

            self._already_started_eip = True
            # we want to start soledad anyway after a certain timeout if eip
            # fails to come up
            QtDelayedCall(self.EIP_START_TIMEOUT,
                          self._maybe_run_soledad_setup_checks)
        else:
            if not self._already_started_eip:
                if EIP_SERVICE in self._enabled_services:
                    if missing_helpers:
                        msg = self.tr(
                            "Disabled: missing helper files")
                    else:
                        msg = self.tr("Not supported"),
                    self._eip_status.set_eip_status(msg, error=True)
                else:
                    msg = self.tr("Disabled")
                    self._eip_status.disable_eip_start()
                    self._eip_status.set_eip_status(msg)
            # eip will not start, so we start soledad anyway
            self._maybe_run_soledad_setup_checks()

    @QtCore.Slot(dict)
    def _finish_eip_bootstrap(self, data):
        """
        TRIGGERS:
            self._backend.signaler.eip_client_certificate_ready

        Start the VPN thread if the eip configuration is properly
        loaded.
        """
        passed = data[PASSED_KEY]

        if not passed:
            error_msg = self.tr("There was a problem with the provider")
            self._eip_status.set_eip_status(error_msg, error=True)
            logger.error(data[ERROR_KEY])
            self._already_started_eip = False
            return

        # DO START EIP Connection!
        self._eip_conductor.do_connect()

    @QtCore.Slot(dict)
    def _eip_intermediate_stage(self, data):
        # TODO missing param documentation
        """
        TRIGGERS:
            self._backend.signaler.eip_config_ready

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.
        """
        passed = data[PASSED_KEY]
        if not passed:
            self._login_widget.set_status(
                self.tr("Unable to connect: Problem with provider"))
            logger.error(data[ERROR_KEY])
            self._already_started_eip = False
            self._eip_status.aborted()

    # end of EIP methods ---------------------------------------------

    @QtCore.Slot()
    def _logout(self):
        """
        TRIGGERS:
            self._login_widget.logout

        Starts the logout sequence
        """
        self._cancel_ongoing_defers()

        # XXX: If other defers are doing authenticated stuff, this
        # might conflict with those. CHECK!
        self._backend.user_logout()
        self.logout.emit()

    @QtCore.Slot()
    def _logout_error(self):
        """
        TRIGGER:
            self._srp_auth.logout_error

        Inform the user about a logout error.
        """
        self._login_widget.done_logout()
        self.ui.lblLoginProvider.setText(self.tr("Login"))
        self._login_widget.set_status(
            self.tr("Something went wrong with the logout."))

    @QtCore.Slot()
    def _logout_ok(self):
        """
        TRIGGER:
            self._srp_auth.logout_ok

        Switches the stackedWidget back to the login stage after
        logging out
        """
        self._login_widget.done_logout()
        self.ui.lblLoginProvider.setText(self.tr("Login"))

        self._logged_user = None
        self._login_widget.logged_out()
        self._mail_status.mail_state_disabled()

        self._show_hide_unsupported_services()

    @QtCore.Slot(dict)
    def _intermediate_stage(self, data):
        # TODO this method name is confusing as hell.
        """
        TRIGGERS:
            self._backend.signaler.prov_name_resolution
            self._backend.signaler.prov_https_connection
            self._backend.signaler.prov_download_ca_cert

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.
        """
        passed = data[PASSED_KEY]
        if not passed:
            logger.error(data[ERROR_KEY])
            self._login_problem_provider()

    #
    # window handling methods
    #

    def _on_raise_window_event(self, req):
        """
        Callback for the raise window event
        """
        if IS_WIN:
            raise_window_ack()
        self.raise_window.emit()

    @QtCore.Slot()
    def _do_raise_mainwindow(self):
        """
        TRIGGERS:
            self._on_raise_window_event

        Triggered when we receive a RAISE_WINDOW event.
        """
        TOPFLAG = QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(self.windowFlags() | TOPFLAG)
        self.show()
        self.setWindowFlags(self.windowFlags() & ~TOPFLAG)
        self.show()
        if IS_MAC:
            self.raise_()

    #
    # cleanup and quit methods
    #

    def _stop_services(self):
        """
        Stop services and cancel ongoing actions (if any).
        """
        logger.debug('About to quit, doing cleanup.')

        self._cancel_ongoing_defers()

        self._services_being_stopped = set(('imap', 'eip'))

        imap_stopped = lambda: self._remove_service('imap')
        self._leap_signaler.imap_stopped.connect(imap_stopped)

        eip_stopped = lambda: self._remove_service('eip')
        self._leap_signaler.eip_stopped.connect(eip_stopped)

        logger.debug('Stopping mail services')
        self._backend.imap_stop_service()
        self._backend.smtp_stop_service()

        if self._logged_user is not None:
            logger.debug("Doing logout")
            self._backend.user_logout()

        logger.debug('Terminating vpn')
        self._backend.eip_stop(shutdown=True)

    def quit(self):
        """
        Start the quit sequence and wait for services to finish.
        Cleanup and close the main window before quitting.
        """
        if self._quitting:
            return

        autostart.set_autostart(False)

        self._quitting = True

        # first thing to do quitting, hide the mainwindow and show tooltip.
        self.hide()
        if self._systray is not None:
            self._systray.showMessage(
                self.tr('Quitting...'),
                self.tr('Bitmask is quitting, please wait.'))

        # explicitly process events to display tooltip immediately
        QtCore.QCoreApplication.processEvents(0, 10)

        # Close other windows if any.
        if self._wizard:
            self._wizard.close()

        if self._logger_window:
            self._logger_window.close()

        # Set this in case that the app is hidden
        QtGui.QApplication.setQuitOnLastWindowClosed(True)

        self._really_quit = True

        if not self._backend.online:
            self.final_quit()
            return

        self._stop_services()

        # call final quit when all the services are stopped
        self.all_services_stopped.connect(self.final_quit)
        # or if we reach the timeout
        QtDelayedCall(self.SERVICES_STOP_TIMEOUT, self.final_quit)

    def _backend_kill(self):
        """
        Send a kill signal to the backend process.
        This is called if the backend does not respond to requests.
        """
        if self._backend_pid is not None:
            logger.debug("Killing backend")
            psutil.Process(self._backend_pid).kill()

    @QtCore.Slot()
    def _remove_service(self, service):
        """
        Remove the given service from the waiting list and check if we have
        running services that we need to wait until we quit.
        Emit self.all_services_stopped signal if we don't need to keep waiting.

        :param service: the service that we want to remove
        :type service: str
        """
        self._services_being_stopped.discard(service)

        if not self._services_being_stopped:
            logger.debug("All services stopped.")
            self.all_services_stopped.emit()

    @QtCore.Slot()
    def final_quit(self):
        """
        Final steps to quit the app, starting from here we don't care about
        running services or user interaction, just quitting.
        """
        # We can reach here because all the services are stopped or because a
        # timeout was triggered. Since we want to run this only once, we exit
        # if this is called twice.
        if self._finally_quitting:
            return

        logger.debug('Final quit...')
        self._finally_quitting = True

        if self._backend.online:
            logger.debug('Closing soledad...')
            self._backend.soledad_close()

        self._leap_signaler.stop()

        if self._backend.online:
            self._backend.stop()
        else:
            self._backend_kill()

        time.sleep(0.05)  # give the thread a little time to finish.

        # Remove lockfiles on a clean shutdown.
        logger.debug('Cleaning pidfiles')
        if IS_WIN:
            WindowsLock.release_all_locks()

        self.close()
