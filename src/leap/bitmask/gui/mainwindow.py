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

from threading import Condition
from datetime import datetime

from PySide import QtCore, QtGui
from twisted.internet import threads
from zope.proxy import ProxyBase, setProxiedObject

from leap.bitmask import __version__ as VERSION
from leap.bitmask import __version_hash__ as VERSION_HASH
from leap.bitmask.config import flags
from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.gui.loggerwindow import LoggerWindow
from leap.bitmask.gui.advanced_key_management import AdvancedKeyManagement
from leap.bitmask.gui.login import LoginWidget
from leap.bitmask.gui.preferenceswindow import PreferencesWindow
from leap.bitmask.gui.eip_preferenceswindow import EIPPreferencesWindow
from leap.bitmask.gui import statemachines
from leap.bitmask.gui.eip_status import EIPStatusWidget
from leap.bitmask.gui.mail_status import MailStatusWidget
from leap.bitmask.gui.wizard import Wizard
from leap.bitmask.gui.systray import SysTray

from leap.bitmask import provider
from leap.bitmask.platform_init import IS_WIN, IS_MAC
from leap.bitmask.platform_init.initializers import init_platform

from leap.bitmask import backend

from leap.bitmask.services import get_service_display_name

from leap.bitmask.services.mail import conductor as mail_conductor

from leap.bitmask.services import EIP_SERVICE, MX_SERVICE
from leap.bitmask.services.eip import eipconfig
from leap.bitmask.services.eip import get_openvpn_management
from leap.bitmask.services.eip.eipbootstrapper import EIPBootstrapper
from leap.bitmask.services.eip.connection import EIPConnection
from leap.bitmask.services.eip.vpnprocess import VPN
from leap.bitmask.services.eip.vpnprocess import OpenVPNAlreadyRunning
from leap.bitmask.services.eip.vpnprocess import AlienOpenVPNAlreadyRunning

from leap.bitmask.services.eip.vpnlauncher import VPNLauncherException
from leap.bitmask.services.eip.vpnlauncher import OpenVPNNotFoundException
from leap.bitmask.services.eip.linuxvpnlauncher import EIPNoPkexecAvailable
from leap.bitmask.services.eip.linuxvpnlauncher import \
    EIPNoPolkitAuthAgentAvailable
from leap.bitmask.services.eip.darwinvpnlauncher import EIPNoTunKextLoaded
from leap.bitmask.services.soledad.soledadbootstrapper import \
    SoledadBootstrapper

from leap.bitmask.util import make_address
from leap.bitmask.util.keyring_helpers import has_keyring
from leap.bitmask.util.leap_log_handler import LeapLogHandler

if IS_WIN:
    from leap.bitmask.platform_init.locks import WindowsLock
    from leap.bitmask.platform_init.locks import raise_window_ack

from leap.common.check import leap_assert
from leap.common.events import register
from leap.common.events import events_pb2 as proto

from leap.mail.imap.service.imap import IMAP_PORT

from ui_mainwindow import Ui_MainWindow

logger = logging.getLogger(__name__)


class MainWindow(QtGui.QMainWindow):
    """
    Main window for login and presenting status updates to the user
    """

    # StackedWidget indexes
    LOGIN_INDEX = 0
    EIP_STATUS_INDEX = 1

    # Signals
    eip_needs_login = QtCore.Signal([])
    offline_mode_bypass_login = QtCore.Signal([])
    new_updates = QtCore.Signal(object)
    raise_window = QtCore.Signal([])
    soledad_ready = QtCore.Signal([])
    mail_client_logged_in = QtCore.Signal([])
    logout = QtCore.Signal([])

    # We use this flag to detect abnormal terminations
    user_stopped_eip = False

    # We give EIP some time to come up before starting soledad anyway
    EIP_TIMEOUT = 60000  # in milliseconds

    # We give each service some time to come to a halt before forcing quit
    SERVICE_STOP_TIMEOUT = 20

    def __init__(self, quit_callback,
                 openvpn_verb=1,
                 bypass_checks=False):
        """
        Constructor for the client main window

        :param quit_callback: Function to be called when closing
                              the application.
        :type quit_callback: callable

        :param bypass_checks: Set to true if the app should bypass
                              first round of checks for CA
                              certificates at bootstrap
        :type bypass_checks: bool
        """
        QtGui.QMainWindow.__init__(self)

        # register leap events ########################################
        register(signal=proto.UPDATER_NEW_UPDATES,
                 callback=self._new_updates_available,
                 reqcbk=lambda req, resp: None)  # make rpc call async
        register(signal=proto.RAISE_WINDOW,
                 callback=self._on_raise_window_event,
                 reqcbk=lambda req, resp: None)  # make rpc call async
        register(signal=proto.IMAP_CLIENT_LOGIN,
                 callback=self._on_mail_client_logged_in,
                 reqcbk=lambda req, resp: None)  # make rpc call async
        # end register leap events ####################################

        self._quit_callback = quit_callback
        self._updates_content = ""

        # setup UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._backend = backend.Backend(bypass_checks)
        self._backend.start()

        self._settings = LeapSettings()

        self._login_widget = LoginWidget(
            self._settings,
            self)
        self.ui.loginLayout.addWidget(self._login_widget)

        # Qt Signal Connections #####################################
        # TODO separate logic from ui signals.

        self._login_widget.login.connect(self._login)
        self._login_widget.cancel_login.connect(self._cancel_login)
        self._login_widget.show_wizard.connect(self._launch_wizard)
        self._login_widget.logout.connect(self._logout)

        self._eip_status = EIPStatusWidget(self)
        self.ui.eipLayout.addWidget(self._eip_status)
        self._login_widget.logged_in_signal.connect(
            self._eip_status.enable_eip_start)
        self._login_widget.logged_in_signal.connect(
            self._enable_eip_start_action)

        self._mail_status = MailStatusWidget(self)
        self.ui.mailLayout.addWidget(self._mail_status)

        self._eip_connection = EIPConnection()

        # XXX this should be handled by EIP Conductor
        self._eip_connection.qtsigs.connecting_signal.connect(
            self._start_eip)
        self._eip_connection.qtsigs.disconnecting_signal.connect(
            self._stop_eip)

        self._eip_status.eip_connection_connected.connect(
            self._on_eip_connected)
        self._eip_status.eip_connection_connected.connect(
            self._maybe_run_soledad_setup_checks)
        self.offline_mode_bypass_login.connect(
            self._maybe_run_soledad_setup_checks)

        self.eip_needs_login.connect(
            self._eip_status.disable_eip_start)
        self.eip_needs_login.connect(
            self._disable_eip_start_action)

        # This is loaded only once, there's a bug when doing that more
        # than once
        # XXX HACK!! But we need it as long as we are using
        # provider_config in here
        self._provider_config = (
            self._backend._components["provider"]._provider_config)
        # Used for automatic start of EIP
        self._provisional_provider_config = ProviderConfig()
        self._eip_config = eipconfig.EIPConfig()

        self._already_started_eip = False
        self._already_started_soledad = False

        # This is created once we have a valid provider config
        self._srp_auth = None
        self._logged_user = None
        self._logged_in_offline = False

        self._backend_connect()

        # This thread is similar to the provider bootstrapper
        self._eip_bootstrapper = EIPBootstrapper()

        # EIP signals ---- move to eip conductor.
        # TODO change the name of "download_config" signal to
        # something less confusing (config_ready maybe)
        self._eip_bootstrapper.download_config.connect(
            self._eip_intermediate_stage)
        self._eip_bootstrapper.download_client_certificate.connect(
            self._finish_eip_bootstrap)

        self._vpn = VPN(openvpn_verb=openvpn_verb)

        # connect vpn process signals
        self._vpn.qtsigs.state_changed.connect(
            self._eip_status.update_vpn_state)
        self._vpn.qtsigs.status_changed.connect(
            self._eip_status.update_vpn_status)
        self._vpn.qtsigs.process_finished.connect(
            self._eip_finished)
        self._vpn.qtsigs.network_unreachable.connect(
            self._on_eip_network_unreachable)
        self._vpn.qtsigs.process_restart_tls.connect(
            self._do_eip_restart)
        self._vpn.qtsigs.process_restart_ping.connect(
            self._do_eip_restart)

        self._soledad_bootstrapper = SoledadBootstrapper()
        self._soledad_bootstrapper.download_config.connect(
            self._soledad_intermediate_stage)
        self._soledad_bootstrapper.gen_key.connect(
            self._soledad_bootstrapped_stage)
        self._soledad_bootstrapper.local_only_ready.connect(
            self._soledad_bootstrapped_stage)
        self._soledad_bootstrapper.soledad_timeout.connect(
            self._retry_soledad_connection)
        self._soledad_bootstrapper.soledad_failed.connect(
            self._mail_status.set_soledad_failed)

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

        # XXX separate actions into a different
        # module.
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
        self.mail_client_logged_in.connect(self._fetch_incoming_mail)
        self.logout.connect(self._stop_imap_service)
        self.logout.connect(self._stop_smtp_service)

        ################################# end Qt Signals connection ########

        init_platform()

        self._wizard = None
        self._wizard_firstrun = False

        self._logger_window = None

        self._bypass_checks = bypass_checks

        # We initialize Soledad and Keymanager instances as
        # transparent proxies, so we can pass the reference freely
        # around.
        self._soledad = ProxyBase(None)
        self._keymanager = ProxyBase(None)

        self._login_defer = None
        self._download_provider_defer = None

        self._mail_conductor = mail_conductor.MailConductor(
            self._soledad, self._keymanager)
        self._mail_conductor.connect_mail_signals(self._mail_status)

        # Eip machine is a public attribute where the state machine for
        # the eip connection will be available to the different components.
        # Remember that this will not live in the  +1600LOC mainwindow for
        # all the eternity, so at some point we will be moving this to
        # the EIPConductor or some other clever component that we will
        # instantiate from here.

        self.eip_machine = None
        # start event machines
        self.start_eip_machine()
        self._mail_conductor.start_mail_machine()

        self._eip_name = get_service_display_name(EIP_SERVICE)

        if self._first_run():
            self._wizard_firstrun = True
            self._backend_disconnect()
            self._wizard = Wizard(backend=self._backend,
                                  bypass_checks=bypass_checks)
            # Give this window time to finish init and then show the wizard
            QtCore.QTimer.singleShot(1, self._launch_wizard)
            self._wizard.accepted.connect(self._finish_init)
            self._wizard.rejected.connect(self._rejected_wizard)
        else:
            # during finish_init, we disable the eip start button
            # so this has to be done after eip_machine is started
            self._finish_init()

    def _backend_connect(self):
        """
        Helper to connect to backend signals
        """
        sig = self._backend.signaler
        sig.prov_name_resolution.connect(self._intermediate_stage)
        sig.prov_https_connection.connect(self._intermediate_stage)
        sig.prov_download_ca_cert.connect(self._intermediate_stage)

        sig.prov_download_provider_info.connect(self._load_provider_config)
        sig.prov_check_api_certificate.connect(self._provider_config_loaded)

        # Only used at login, no need to disconnect this like we do
        # with the other
        sig.prov_problem_with_provider.connect(self._login_problem_provider)

        sig.prov_unsupported_client.connect(self._needs_update)
        sig.prov_unsupported_api.connect(self._incompatible_api)

    def _backend_disconnect(self):
        """
        Helper to disconnect from backend signals.

        Some signals are emitted from the wizard, and we want to
        ignore those.
        """
        sig = self._backend.signaler
        sig.prov_name_resolution.disconnect(self._intermediate_stage)
        sig.prov_https_connection.disconnect(self._intermediate_stage)
        sig.prov_download_ca_cert.disconnect(self._intermediate_stage)

        sig.prov_download_provider_info.disconnect(self._load_provider_config)
        sig.prov_check_api_certificate.disconnect(self._provider_config_loaded)

    def _rejected_wizard(self):
        """
        SLOT
        TRIGGERS: self._wizard.rejected

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
            self._backend_connect()
            if self._wizard_firstrun:
                self._finish_init()

    def _launch_wizard(self):
        """
        SLOT
        TRIGGERS:
          self._login_widget.show_wizard
          self.ui.action_wizard.triggered

        Also called in first run.

        Launches the wizard, creating the object itself if not already
        there.
        """
        if self._wizard is None:
            self._backend_disconnect()
            self._wizard = Wizard(backend=self._backend,
                                  bypass_checks=self._bypass_checks)
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

    def _wizard_finished(self):
        """
        SLOT
        TRIGGERS
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

    def _show_logger_window(self):
        """
        SLOT
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

    def _show_AKM(self):
        """
        SLOT
        TRIGGERS:
            self.ui.action_advanced_key_management.triggered

        Displays the Advanced Key Management dialog.
        """
        domain = self._login_widget.get_selected_provider()
        logged_user = "{0}@{1}".format(self._logged_user, domain)
        self._akm = AdvancedKeyManagement(
            logged_user, self._keymanager, self._soledad)
        self._akm.show()

    def _show_preferences(self):
        """
        SLOT
        TRIGGERS:
          self.ui.btnPreferences.clicked (disabled for now)
          self.ui.action_preferences

        Displays the preferences window.
        """
        preferences = PreferencesWindow(
            self, self._srp_auth, self._provider_config, self._soledad,
            self._login_widget.get_selected_provider())

        self.soledad_ready.connect(preferences.set_soledad_ready)
        preferences.show()
        preferences.preferences_saved.connect(self._update_eip_enabled_status)

    def _update_eip_enabled_status(self):
        """
        SLOT
        TRIGGER:
            PreferencesWindow.preferences_saved

        Enable or disable the EIP start/stop actions and stop EIP if the user
        disabled that service.

        :returns: if the eip actions were enabled or disabled
        :rtype: bool
        """
        settings = self._settings
        default_provider = settings.get_defaultprovider()
        enabled_services = []
        if default_provider is not None:
            enabled_services = settings.get_enabled_services(default_provider)

        eip_enabled = False
        if EIP_SERVICE in enabled_services:
            should_autostart = settings.get_autostart_eip()
            if should_autostart and default_provider is not None:
                self._eip_status.enable_eip_start()
                self._eip_status.set_eip_status("")
                eip_enabled = True
            else:
                # we don't have an usable provider
                # so the user needs to log in first
                self._eip_status.disable_eip_start()
        else:
            self._stop_eip()
            self._eip_status.disable_eip_start()
            self._eip_status.set_eip_status(self.tr("Disabled"))

        return eip_enabled

    def _show_eip_preferences(self):
        """
        SLOT
        TRIGGERS:
          self.ui.btnEIPPreferences.clicked
          self.ui.action_eip_preferences (disabled for now)

        Displays the EIP preferences window.
        """
        EIPPreferencesWindow(self).show()

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

    def _react_to_new_updates(self, req):
        """
        SLOT
        TRIGGER: self._new_updates_available

        Displays the new updates label and sets the updates_content
        """
        self.moveToThread(QtCore.QCoreApplication.instance().thread())
        self.ui.lblNewUpdates.setVisible(True)
        self.ui.btnMore.setVisible(True)
        self._updates_content = req.content

    def _updates_details(self):
        """
        SLOT
        TRIGGER: self.ui.btnMore.clicked

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

    def _finish_init(self):
        """
        SLOT
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
        self.show()
        if IS_MAC:
            self.raise_()

        self._hide_unsupported_services()

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
            self._backend_connect()
        else:
            self._try_autostart_eip()

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

    def _hide_unsupported_services(self):
        """
        Given a set of configured providers, it creates a set of
        available services among all of them and displays the service
        widgets of only those.

        This means, for example, that with just one provider with EIP
        only, the mail widget won't be displayed.
        """
        providers = self._settings.get_configured_providers()

        services = set()

        for prov in providers:
            provider_config = ProviderConfig()
            loaded = provider_config.load(
                provider.get_provider_path(prov))
            if loaded:
                for service in provider_config.get_services():
                    services.add(service)

        self.ui.eipWidget.setVisible(EIP_SERVICE in services)
        self.ui.mailWidget.setVisible(MX_SERVICE in services)

    def _set_label_offline(self):
        """
        Set the login label to reflect offline status.
        """
        if self._logged_in_offline:
            provider = ""
        else:
            provider = self.ui.lblLoginProvider.text()

        self.ui.lblLoginProvider.setText(
            provider +
            self.tr(" (offline mode)"))

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

        eip_status_label = "{0}: {1}".format(self._eip_name, self.tr("OFF"))
        eip_menu = systrayMenu.addMenu(eip_status_label)
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

    def _tray_activated(self, reason=None):
        """
        SLOT
        TRIGGER: self._systray.activated

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

    def _toggle_visible(self):
        """
        SLOT
        TRIGGER: self._action_visible.triggered

        Toggles the window visibility
        """
        visible = self.isVisible() and self.isActiveWindow()

        if not visible:
            QtGui.QApplication.setQuitOnLastWindowClosed(True)
            self.show()
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
        QtCore.QTimer.singleShot(500, self._update_hideshow_menu)

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

    def _about(self):
        """
        SLOT
        TRIGGERS: self.ui.action_about_leap.triggered

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

    def _help(self):
        """
        SLOT
        TRIGGERS: self.ui.action_help.triggered

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
        # XXX should rename this provider, name clash.
        provider = self._login_widget.get_selected_provider()
        self._backend.setup_provider(provider)

    def _load_provider_config(self, data):
        """
        SLOT
        TRIGGER: self._backend.signaler.prov_download_provider_info

        Once the provider config has been downloaded, this loads the
        self._provider_config instance with it and starts the second
        part of the bootstrapping sequence

        :param data: result from the last stage of the
                     run_provider_select_checks
        :type data: dict
        """
        if data[self._backend.PASSED_KEY]:
            selected_provider = self._login_widget.get_selected_provider()
            self._backend.provider_bootstrap(selected_provider)
        else:
            logger.error(data[self._backend.ERROR_KEY])
            self._login_widget.set_enabled(True)

    def _login_problem_provider(self):
        """
        Warns the user about a problem with the provider during login.
        """
        self._login_widget.set_status(
            self.tr("Unable to login: Problem with provider"))
        self._login_widget.set_enabled(True)

    def _login(self):
        """
        SLOT
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
            leap_assert(self._provider_config, "We need a provider config")
            if self._login_widget.start_login():
                self._download_provider_config()

    def _cancel_login(self):
        """
        SLOT
        TRIGGERS:
          self._login_widget.cancel_login

        Stops the login sequence.
        """
        logger.debug("Cancelling log in.")

        if self._download_provider_defer:
            logger.debug("Cancelling download provider defer.")
            self._download_provider_defer.cancel()

        if self._login_defer:
            logger.debug("Cancelling login defer.")
            self._login_defer.cancel()

        self._login_widget.set_status(self.tr("Log in cancelled by the user."))

    def _provider_config_loaded(self, data):
        """
        SLOT
        TRIGGER: self._backend.signaler.prov_check_api_certificate

        Once the provider configuration is loaded, this starts the SRP
        authentication
        """
        leap_assert(self._provider_config, "We need a provider config!")

        if data[self._backend.PASSED_KEY]:
            username = self._login_widget.get_user()
            password = self._login_widget.get_password()

            self._hide_unsupported_services()

            if self._srp_auth is None:
                self._srp_auth = SRPAuth(self._provider_config)
                self._srp_auth.authentication_finished.connect(
                    self._authentication_finished)
                self._srp_auth.logout_finished.connect(
                    self._done_logging_out)

            # TODO Add errback!
            self._login_defer = self._srp_auth.authenticate(username, password)
        else:
            self._login_widget.set_status(
                "Unable to login: Problem with provider")
            logger.error(data[self._backend.ERROR_KEY])
            self._login_widget.set_enabled(True)

    def _authentication_finished(self, ok, message):
        """
        SLOT
        TRIGGER: self._srp_auth.authentication_finished

        Once the user is properly authenticated, try starting the EIP
        service
        """
        # In general we want to "filter" likely complicated error
        # messages, but in this case, the messages make more sense as
        # they come. Since they are "Unknown user" or "Unknown
        # password"
        self._login_widget.set_status(message, error=not ok)

        if ok:
            self._logged_user = self._login_widget.get_user()
            user = self._logged_user
            domain = self._provider_config.get_domain()
            full_user_id = make_address(user, domain)
            self._mail_conductor.userid = full_user_id
            self._login_defer = None
            self._start_eip_bootstrap()
        else:
            self._login_widget.set_enabled(True)

    def _start_eip_bootstrap(self):
        """
        Changes the stackedWidget index to the EIP status one and
        triggers the eip bootstrapping.
        """

        self._login_widget.logged_in()
        provider = self._provider_config.get_domain()
        self.ui.lblLoginProvider.setText(provider)

        self._enabled_services = self._settings.get_enabled_services(
            self._provider_config.get_domain())

        # TODO separate UI from logic.
        if self._provider_config.provides_mx() and \
           self._enabled_services.count(MX_SERVICE) > 0:
            self._mail_status.about_to_start()
        else:
            self._mail_status.set_disabled()

        self._maybe_start_eip()

    def _maybe_run_soledad_setup_checks(self):
        """
        Conditionally start Soledad.
        """
        # TODO split.
        if self._already_started_soledad is True:
            return

        username = self._login_widget.get_user()
        password = unicode(self._login_widget.get_password())
        provider_domain = self._login_widget.get_selected_provider()

        sb = self._soledad_bootstrapper
        if flags.OFFLINE is True:
            provider_domain = self._login_widget.get_selected_provider()
            sb._password = password

            self._provisional_provider_config.load(
                provider.get_provider_path(provider_domain))

            full_user_id = make_address(username, provider_domain)
            uuid = self._settings.get_uuid(full_user_id)
            self._mail_conductor.userid = full_user_id

            if uuid is None:
                # We don't need more visibility at the moment,
                # this is mostly for internal use/debug for now.
                logger.warning("Sorry! Log-in at least one time.")
                return
            fun = sb.load_offline_soledad
            fun(full_user_id, password, uuid)
        else:
            provider_config = self._provider_config

            if self._logged_user is not None:
                fun = sb.run_soledad_setup_checks
                fun(provider_config, username, password,
                    download_if_needed=True)

    ###################################################################
    # Service control methods: soledad

    def _soledad_intermediate_stage(self, data):
        # TODO missing param docstring
        """
        SLOT
        TRIGGERS:
          self._soledad_bootstrapper.download_config

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.
        """
        passed = data[self._soledad_bootstrapper.PASSED_KEY]
        if not passed:
            # TODO display in the GUI:
            # should pass signal to a slot in status_panel
            # that sets the global status
            logger.error("Soledad failed to start: %s" %
                         (data[self._soledad_bootstrapper.ERROR_KEY],))
            self._retry_soledad_connection()

    def _retry_soledad_connection(self):
        """
        Retries soledad connection.
        """
        # XXX should move logic to soledad boostrapper itself
        logger.debug("Retrying soledad connection.")
        if self._soledad_bootstrapper.should_retry_initialization():
            self._soledad_bootstrapper.increment_retries_count()
            # XXX should cancel the existing socket --- this
            # is avoiding a clean termination.
            threads.deferToThread(
                self._soledad_bootstrapper.load_and_sync_soledad)
        else:
            logger.warning("Max number of soledad initialization "
                           "retries reached.")

    def _soledad_bootstrapped_stage(self, data):
        """
        SLOT
        TRIGGERS:
          self._soledad_bootstrapper.gen_key
          self._soledad_bootstrapper.local_only_ready

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.

        :param data: result from the bootstrapping stage for Soledad
        :type data: dict
        """
        passed = data[self._soledad_bootstrapper.PASSED_KEY]
        if not passed:
            # TODO should actually *display* on the panel.
            logger.debug("ERROR on soledad bootstrapping:")
            logger.error("%r" % data[self._soledad_bootstrapper.ERROR_KEY])
            return

        logger.debug("Done bootstrapping Soledad")

        # Update the proxy objects to point to
        # the initialized instances.
        setProxiedObject(self._soledad,
                         self._soledad_bootstrapper.soledad)
        setProxiedObject(self._keymanager,
                         self._soledad_bootstrapper.keymanager)

        # Ok, now soledad is ready, so we can allow other things that
        # depend on soledad to start.

        # this will trigger start_imap_service
        # and start_smtp_boostrapping
        self.soledad_ready.emit()

    ###################################################################
    # Service control methods: smtp

    @QtCore.Slot()
    def _start_smtp_bootstrapping(self):
        """
        SLOT
        TRIGGERS:
            self.soledad_ready
        """
        if flags.OFFLINE is True:
            logger.debug("not starting smtp in offline mode")
            return

        # TODO for simmetry, this should be called start_smtp_service
        # (and delegate all the checks to the conductor)
        if self._provider_config.provides_mx() and \
                self._enabled_services.count(MX_SERVICE) > 0:
            self._mail_conductor.smtp_bootstrapper.run_smtp_setup_checks(
                self._provider_config,
                self._mail_conductor.smtp_config,
                download_if_needed=True)

    # XXX --- should remove from here, and connecte directly to the state
    # machine.
    @QtCore.Slot()
    def _stop_smtp_service(self):
        """
        SLOT
        TRIGGERS:
            self.logout
        """
        # TODO call stop_mail_service
        self._mail_conductor.stop_smtp_service()

    ###################################################################
    # Service control methods: imap

    @QtCore.Slot()
    def _start_imap_service(self):
        """
        SLOT
        TRIGGERS:
            self.soledad_ready
        """
        # TODO in the OFFLINE mode we should also modify the  rules
        # in the mail state machine so it shows that imap is active
        # (but not smtp since it's not yet ready for offline use)
        start_fun = self._mail_conductor.start_imap_service
        if flags.OFFLINE is True:
            provider_domain = self._login_widget.get_selected_provider()
            self._provider_config.load(
                provider.get_provider_path(provider_domain))
        provides_mx = self._provider_config.provides_mx()

        if flags.OFFLINE is True and provides_mx:
            start_fun()
            return

        enabled_services = self._enabled_services
        if self._provider_config.provides_mx() and \
                enabled_services.count(MX_SERVICE) > 0:
            start_fun()

    def _on_mail_client_logged_in(self, req):
        """
        Triggers qt signal when client login event is received.
        """
        self.mail_client_logged_in.emit()

    @QtCore.Slot()
    def _fetch_incoming_mail(self):
        """
        SLOT
        TRIGGERS:
            self.mail_client_logged_in
        """
        # TODO connect signal directly!!!
        self._mail_conductor.fetch_incoming_mail()

    @QtCore.Slot()
    def _stop_imap_service(self):
        """
        SLOT
        TRIGGERS:
            self.logout
        """
        cv = Condition()
        cv.acquire()
        # TODO call stop_mail_service
        threads.deferToThread(self._mail_conductor.stop_imap_service, cv)
        # and wait for it to be stopped
        logger.debug('Waiting for imap service to stop.')
        cv.wait(self.SERVICE_STOP_TIMEOUT)

    # end service control methods (imap)

    ###################################################################
    # Service control methods: eip

    def start_eip_machine(self):
        """
        Initializes and starts the EIP state machine
        """
        button = self._eip_status.eip_button
        action = self._action_eip_startstop
        label = self._eip_status.eip_label
        builder = statemachines.ConnectionMachineBuilder(self._eip_connection)
        eip_machine = builder.make_machine(button=button,
                                           action=action,
                                           label=label)
        self.eip_machine = eip_machine
        self.eip_machine.start()
        logger.debug('eip machine started')

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

    @QtCore.Slot()
    def _on_eip_connected(self):
        """
        SLOT
        TRIGGERS:
            self._eip_status.eip_connection_connected
        Emits the EIPConnection.qtsigs.connected_signal

        This is a little workaround for connecting the vpn-connected
        signal that currently is beeing processed under status_panel.
        After the refactor to EIPConductor this should not be necessary.
        """
        self._eip_connection.qtsigs.connected_signal.emit()

    def _try_autostart_eip(self):
        """
        Tries to autostart EIP
        """
        settings = self._settings

        if not self._update_eip_enabled_status():
            return

        default_provider = settings.get_defaultprovider()
        self._enabled_services = settings.get_enabled_services(
            default_provider)

        loaded = self._provisional_provider_config.load(
            provider.get_provider_path(default_provider))
        if loaded:
            # XXX I think we should not try to re-download config every time,
            # it adds some delay.
            # Maybe if it's the first run in a session,
            # or we can try only if it fails.
            self._maybe_start_eip()
        else:
            # XXX: Display a proper message to the user
            self.eip_needs_login.emit()
            logger.error("Unable to load %s config, cannot autostart." %
                         (default_provider,))

    @QtCore.Slot()
    def _start_eip(self):
        """
        SLOT
        TRIGGERS:
          self._eip_connection.qtsigs.do_connect_signal
          (via state machine)
        or called from _finish_eip_bootstrap

        Starts EIP
        """
        provider_config = self._get_best_provider_config()
        provider = provider_config.get_domain()
        self._eip_status.eip_pre_up()
        self.user_stopped_eip = False

        # until we set an option in the preferences window,
        # we'll assume that by default we try to autostart.
        # If we switch it off manually, it won't try the next
        # time.
        self._settings.set_autostart_eip(True)

        loaded = eipconfig.load_eipconfig_if_needed(
            provider_config, self._eip_config, provider)

        if not loaded:
            eip_status_label = self.tr("Could not load {0} configuration.")
            eip_status_label = eip_status_label.format(self._eip_name)
            self._eip_status.set_eip_status(eip_status_label, error=True)
            # signal connection aborted to state machine
            qtsigs = self._eip_connection.qtsigs
            qtsigs.connection_aborted_signal.emit()
            logger.error("Tried to start EIP but cannot find any "
                         "available provider!")
            return

        try:
            # XXX move this to EIPConductor
            host, port = get_openvpn_management()
            self._vpn.start(eipconfig=self._eip_config,
                            providerconfig=provider_config,
                            socket_host=host,
                            socket_port=port)
            self._settings.set_defaultprovider(provider)

            # XXX move to the state machine too
            self._eip_status.set_provider(provider)

        # TODO refactor exceptions so they provide translatable
        # usef-facing messages.
        except EIPNoPolkitAuthAgentAvailable:
            self._eip_status.set_eip_status(
                # XXX this should change to polkit-kde where
                # applicable.
                self.tr("We could not find any "
                        "authentication "
                        "agent in your system.<br/>"
                        "Make sure you have "
                        "<b>polkit-gnome-authentication-"
                        "agent-1</b> "
                        "running and try again."),
                error=True)
            self._set_eipstatus_off()
        except EIPNoTunKextLoaded:
            self._eip_status.set_eip_status(
                self.tr("{0} cannot be started because "
                        "the tuntap extension is not installed properly "
                        "in your system.").format(self._eip_name))
            self._set_eipstatus_off()
        except EIPNoPkexecAvailable:
            self._eip_status.set_eip_status(
                self.tr("We could not find <b>pkexec</b> "
                        "in your system."),
                error=True)
            self._set_eipstatus_off()
        except OpenVPNNotFoundException:
            self._eip_status.set_eip_status(
                self.tr("We could not find openvpn binary."),
                error=True)
            self._set_eipstatus_off()
        except OpenVPNAlreadyRunning as e:
            self._eip_status.set_eip_status(
                self.tr("Another openvpn instance is already running, and "
                        "could not be stopped."),
                error=True)
            self._set_eipstatus_off()
        except AlienOpenVPNAlreadyRunning as e:
            self._eip_status.set_eip_status(
                self.tr("Another openvpn instance is already running, and "
                        "could not be stopped because it was not launched by "
                        "Bitmask. Please stop it and try again."),
                error=True)
            self._set_eipstatus_off()
        except VPNLauncherException as e:
            # XXX We should implement again translatable exceptions so
            # we can pass a translatable string to the panel (usermessage attr)
            self._eip_status.set_eip_status("%s" % (e,), error=True)
            self._set_eipstatus_off()
        else:
            self._already_started_eip = True

    @QtCore.Slot()
    def _stop_eip(self):
        """
        SLOT
        TRIGGERS:
          self._eip_connection.qtsigs.do_disconnect_signal
          (via state machine)
        or called from _eip_finished

        Stops vpn process and makes gui adjustments to reflect
        the change of state.

        :param abnormal: whether this was an abnormal termination.
        :type abnormal: bool
        """
        self.user_stopped_eip = True
        self._vpn.terminate()

        self._set_eipstatus_off(False)
        self._already_started_eip = False

        logger.debug('Setting autostart to: False')
        self._settings.set_autostart_eip(False)

        if self._logged_user:
            self._eip_status.set_provider(
                make_address(
                    self._logged_user,
                    self._get_best_provider_config().get_domain()))
        self._eip_status.eip_stopped()

    @QtCore.Slot()
    def _on_eip_network_unreachable(self):
        # XXX Should move to EIP Conductor
        """
        SLOT
        TRIGGERS:
            self._eip_connection.qtsigs.network_unreachable

        Displays a "network unreachable" error in the EIP status panel.
        """
        self._eip_status.set_eip_status(self.tr("Network is unreachable"),
                                        error=True)
        self._eip_status.set_eip_status_icon("error")

    @QtCore.Slot()
    def _do_eip_restart(self):
        # XXX Should move to EIP Conductor
        """
        SLOT
            self._eip_connection.qtsigs.process_restart

        Restart the connection.
        """
        # for some reason, emitting the do_disconnect/do_connect
        # signals hangs the UI.
        self._stop_eip()
        QtCore.QTimer.singleShot(2000, self._start_eip)

    def _set_eipstatus_off(self, error=True):
        """
        Sets eip status to off
        """
        # XXX this should be handled by the state machine.
        self._eip_status.set_eip_status("", error=error)
        self._eip_status.set_eip_status_icon("error")

    def _eip_finished(self, exitCode):
        """
        SLOT
        TRIGGERS:
          self._vpn.process_finished

        Triggered when the EIP/VPN process finishes to set the UI
        accordingly.

        Ideally we would have the right exit code here,
        but the use of different wrappers (pkexec, cocoasudo) swallows
        the openvpn exit code so we get zero exit in some cases  where we
        shouldn't. As a workaround we just use a flag to indicate
        a purposeful switch off, and mark everything else as unexpected.

        In the near future we should trigger a native notification from here,
        since the user really really wants to know she is unprotected asap.
        And the right thing to do will be to fail-close.

        :param exitCode: the exit code of the eip process.
        :type exitCode: int
        """
        # TODO move to EIPConductor.
        # TODO Add error catching to the openvpn log observer
        # so we can have a more precise idea of which type
        # of error did we have (server side, local problem, etc)

        logger.info("VPN process finished with exitCode %s..."
                    % (exitCode,))

        qtsigs = self._eip_connection.qtsigs
        signal = qtsigs.disconnected_signal

        # XXX check if these exitCodes are pkexec/cocoasudo specific
        if exitCode in (126, 127):
            eip_status_label = self.tr(
                "{0} could not be launched "
                "because you did not authenticate properly.")
            eip_status_label = eip_status_label.format(self._eip_name)
            self._eip_status.set_eip_status(eip_status_label, error=True)
            self._vpn.killit()
            signal = qtsigs.connection_aborted_signal

        elif exitCode != 0 or not self.user_stopped_eip:
            eip_status_label = self.tr("{0} finished in an unexpected manner!")
            eip_status_label = eip_status_label.format(self._eip_name)
            self._eip_status.set_eip_status(eip_status_label, error=True)
            signal = qtsigs.connection_died_signal

        if exitCode == 0 and IS_MAC:
            # XXX remove this warning after I fix cocoasudo.
            logger.warning("The above exit code MIGHT BE WRONG.")

        # We emit signals to trigger transitions in the state machine:
        signal.emit()

    # eip boostrapping, config etc...

    def _maybe_start_eip(self):
        """
        Start the EIP bootstrapping sequence if the client is configured to
        do so.
        """
        leap_assert(self._eip_bootstrapper, "We need an eip bootstrapper!")

        provider_config = self._get_best_provider_config()

        if provider_config.provides_eip() and \
                self._enabled_services.count(EIP_SERVICE) > 0 and \
                not self._already_started_eip:

            # XXX this should be handled by the state machine.
            self._eip_status.set_eip_status(
                self.tr("Starting..."))
            self._eip_bootstrapper.run_eip_setup_checks(
                provider_config,
                download_if_needed=True)
            self._already_started_eip = True
            # we want to start soledad anyway after a certain timeout if eip
            # fails to come up
            QtCore.QTimer.singleShot(
                self.EIP_TIMEOUT,
                self._maybe_run_soledad_setup_checks)
        else:
            if not self._already_started_eip:
                if self._enabled_services.count(EIP_SERVICE) > 0:
                    self._eip_status.set_eip_status(
                        self.tr("Not supported"),
                        error=True)
                else:
                    self._eip_status.disable_eip_start()
                    self._eip_status.set_eip_status(self.tr("Disabled"))
            # eip will not start, so we start soledad anyway
            self._maybe_run_soledad_setup_checks()

    def _finish_eip_bootstrap(self, data):
        """
        SLOT
        TRIGGER: self._eip_bootstrapper.download_client_certificate

        Starts the VPN thread if the eip configuration is properly
        loaded
        """
        leap_assert(self._eip_config, "We need an eip config!")
        passed = data[self._eip_bootstrapper.PASSED_KEY]

        if not passed:
            error_msg = self.tr("There was a problem with the provider")
            self._eip_status.set_eip_status(error_msg, error=True)
            logger.error(data[self._eip_bootstrapper.ERROR_KEY])
            self._already_started_eip = False
            return

        provider_config = self._get_best_provider_config()
        domain = provider_config.get_domain()

        # XXX  move check to _start_eip ?
        loaded = eipconfig.load_eipconfig_if_needed(
            provider_config, self._eip_config, domain)

        if loaded:
            # DO START EIP Connection!
            self._eip_connection.qtsigs.do_connect_signal.emit()
        else:
            eip_status_label = self.tr("Could not load {0} configuration.")
            eip_status_label = eip_status_label.format(self._eip_name)
            self._eip_status.set_eip_status(eip_status_label, error=True)

    def _eip_intermediate_stage(self, data):
        # TODO missing param
        """
        SLOT
        TRIGGERS:
          self._eip_bootstrapper.download_config

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.
        """
        passed = data[self._backend.PASSED_KEY]
        if not passed:
            self._login_widget.set_status(
                self.tr("Unable to connect: Problem with provider"))
            logger.error(data[self._backend.ERROR_KEY])
            self._already_started_eip = False

    # end of EIP methods ---------------------------------------------

    def _get_best_provider_config(self):
        """
        Returns the best ProviderConfig to use at a moment. We may
        have to use self._provider_config or
        self._provisional_provider_config depending on the start
        status.

        :rtype: ProviderConfig
        """
        # TODO move this out of gui.
        leap_assert(self._provider_config is not None or
                    self._provisional_provider_config is not None,
                    "We need a provider config")

        provider_config = None
        if self._provider_config.loaded():
            provider_config = self._provider_config
        elif self._provisional_provider_config.loaded():
            provider_config = self._provisional_provider_config
        else:
            leap_assert(False, "We could not find any usable ProviderConfig.")

        return provider_config

    @QtCore.Slot()
    def _logout(self):
        """
        SLOT
        TRIGGER: self._login_widget.logout

        Starts the logout sequence
        """
        self._soledad_bootstrapper.cancel_bootstrap()
        setProxiedObject(self._soledad, None)

        # reset soledad status flag
        self._already_started_soledad = False

        # XXX: If other defers are doing authenticated stuff, this
        # might conflict with those. CHECK!
        threads.deferToThread(self._srp_auth.logout)
        self.logout.emit()

    def _done_logging_out(self, ok, message):
        # TODO missing params in docstring
        """
        SLOT
        TRIGGER: self._srp_auth.logout_finished

        Switches the stackedWidget back to the login stage after
        logging out
        """
        self._login_widget.done_logout()
        self.ui.lblLoginProvider.setText(self.tr("Login"))

        if ok:
            self._logged_user = None
            self._login_widget.logged_out()
            self._mail_status.mail_state_disabled()

        else:
            self._login_widget.set_status(
                self.tr("Something went wrong with the logout."))

    def _intermediate_stage(self, data):
        # TODO this method name is confusing as hell.
        """
        SLOT
        TRIGGERS:
          self._backend.signaler.prov_name_resolution
          self._backend.signaler.prov_https_connection
          self._backend.signaler.prov_download_ca_cert
          self._eip_bootstrapper.download_config

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.
        """
        passed = data[self._backend.PASSED_KEY]
        if not passed:
            self._login_widget.set_enabled(True)
            self._login_widget.set_status(
                self.tr("Unable to connect: Problem with provider"))
            logger.error(data[self._backend.ERROR_KEY])

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

    def _do_raise_mainwindow(self):
        """
        SLOT
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

    def _cleanup_pidfiles(self):
        """
        Removes lockfiles on a clean shutdown.

        Triggered after aboutToQuit signal.
        """
        if IS_WIN:
            WindowsLock.release_all_locks()

    def _cleanup_and_quit(self):
        """
        Call all the cleanup actions in a serialized way.
        Should be called from the quit function.
        """
        logger.debug('About to quit, doing cleanup...')

        self._stop_imap_service()

        if self._srp_auth is not None:
            if self._srp_auth.get_session_id() is not None or \
               self._srp_auth.get_token() is not None:
                # XXX this can timeout after loong time: See #3368
                self._srp_auth.logout()

        if self._soledad_bootstrapper.soledad is not None:
            logger.debug("Closing soledad...")
            self._soledad_bootstrapper.soledad.close()
        else:
            logger.error("No instance of soledad was found.")

        logger.debug('Terminating vpn')
        self._vpn.terminate(shutdown=True)

        if self._login_defer:
            logger.debug("Cancelling login defer.")
            self._login_defer.cancel()

        if self._download_provider_defer:
            logger.debug("Cancelling download provider defer.")
            self._download_provider_defer.cancel()

        # TODO missing any more cancels?

        logger.debug('Cleaning pidfiles')
        self._cleanup_pidfiles()

    def quit(self):
        """
        Cleanup and tidely close the main window before quitting.
        """
        # TODO separate the shutting down of services from the
        # UI stuff.

        # Set this in case that the app is hidden
        QtGui.QApplication.setQuitOnLastWindowClosed(True)

        self._backend.stop()
        self._cleanup_and_quit()
        self._really_quit = True

        if self._wizard:
            self._wizard.close()

        if self._logger_window:
            self._logger_window.close()

        self.close()

        if self._quit_callback:
            self._quit_callback()

        logger.debug('Bye.')
