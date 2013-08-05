# -*- coding: utf-8 -*-
# mainwindow.py
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
Main window for the leap client
"""
import logging
import os
import platform
import tempfile
from functools import partial

import keyring

from PySide import QtCore, QtGui
from twisted.internet import threads

from leap.common.check import leap_assert
from leap.common.events import register
from leap.common.events import events_pb2 as proto
from leap.config.leapsettings import LeapSettings
from leap.config.providerconfig import ProviderConfig
from leap.crypto.srpauth import SRPAuth
from leap.gui.loggerwindow import LoggerWindow
from leap.gui.wizard import Wizard
from leap.gui.login import LoginWidget
from leap.gui.statuspanel import StatusPanelWidget
from leap.services.eip.eipbootstrapper import EIPBootstrapper
from leap.services.eip.eipconfig import EIPConfig
from leap.services.eip.providerbootstrapper import ProviderBootstrapper
# XXX: Soledad might not work out of the box in Windows, issue #2932
from leap.services.soledad.soledadbootstrapper import SoledadBootstrapper
from leap.services.mail.smtpbootstrapper import SMTPBootstrapper
from leap.platform_init import IS_WIN, IS_MAC
from leap.platform_init.initializers import init_platform

from leap.services.eip.vpnprocess import VPN
from leap.services.eip.vpnprocess import OpenVPNAlreadyRunning
from leap.services.eip.vpnprocess import AlienOpenVPNAlreadyRunning

from leap.services.eip.vpnlaunchers import VPNLauncherException
from leap.services.eip.vpnlaunchers import OpenVPNNotFoundException
from leap.services.eip.vpnlaunchers import EIPNoPkexecAvailable
from leap.services.eip.vpnlaunchers import EIPNoPolkitAuthAgentAvailable
from leap.services.eip.vpnlaunchers import EIPNoTunKextLoaded

from leap.util import __version__ as VERSION
from leap.util.keyring_helpers import has_keyring

from leap.services.mail.smtpconfig import SMTPConfig

if IS_WIN:
    from leap.platform_init.locks import WindowsLock
    from leap.platform_init.locks import raise_window_ack

from ui_mainwindow import Ui_MainWindow

logger = logging.getLogger(__name__)


class MainWindow(QtGui.QMainWindow):
    """
    Main window for login and presenting status updates to the user
    """

    # StackedWidget indexes
    LOGIN_INDEX = 0
    EIP_STATUS_INDEX = 1

    # Keyring
    KEYRING_KEY = "leap_client"

    # SMTP
    PORT_KEY = "port"
    IP_KEY = "ip_address"

    OPENVPN_SERVICE = "openvpn"
    MX_SERVICE = "mx"

    # Signals
    new_updates = QtCore.Signal(object)
    raise_window = QtCore.Signal([])

    # We use this flag to detect abnormal terminations
    user_stopped_eip = False

    def __init__(self, quit_callback,
                 standalone=False, bypass_checks=False):
        """
        Constructor for the client main window

        :param quit_callback: Function to be called when closing
                              the application.
        :type quit_callback: callable

        :param standalone: Set to true if the app should use configs
                           inside its pwd
        :type standalone: bool

        :param bypass_checks: Set to true if the app should bypass
                              first round of checks for CA
                              certificates at bootstrap
        :type bypass_checks: bool
        """
        QtGui.QMainWindow.__init__(self)

        # register leap events
        register(signal=proto.UPDATER_NEW_UPDATES,
                 callback=self._new_updates_available,
                 reqcbk=lambda req, resp: None)  # make rpc call async
        register(signal=proto.RAISE_WINDOW,
                 callback=self._on_raise_window_event,
                 reqcbk=lambda req, resp: None)  # make rpc call async

        self._quit_callback = quit_callback

        self._updates_content = ""

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._settings = LeapSettings(standalone)

        self._login_widget = LoginWidget(
            self._settings,
            self.ui.stackedWidget.widget(self.LOGIN_INDEX))
        self.ui.loginLayout.addWidget(self._login_widget)

        self._login_widget.login.connect(self._login)
        self._login_widget.cancel_login.connect(self._cancel_login)
        self._login_widget.show_wizard.connect(
            self._launch_wizard)

        self.ui.btnShowLog.clicked.connect(self._show_logger_window)

        self._status_panel = StatusPanelWidget(
            self.ui.stackedWidget.widget(self.EIP_STATUS_INDEX))
        self.ui.statusLayout.addWidget(self._status_panel)

        self.ui.stackedWidget.setCurrentIndex(self.LOGIN_INDEX)

        self._status_panel.start_eip.connect(self._start_eip)
        self._status_panel.stop_eip.connect(self._stop_eip)

        # This is loaded only once, there's a bug when doing that more
        # than once
        ProviderConfig.standalone = standalone
        EIPConfig.standalone = standalone
        self._standalone = standalone
        self._provider_config = ProviderConfig()
        # Used for automatic start of EIP
        self._provisional_provider_config = ProviderConfig()
        self._eip_config = EIPConfig()

        self._already_started_eip = False

        # This is created once we have a valid provider config
        self._srp_auth = None
        self._logged_user = None

        # This thread is always running, although it's quite
        # lightweight when it's done setting up provider
        # configuration and certificate.
        self._provider_bootstrapper = ProviderBootstrapper(bypass_checks)

        # Intermediate stages, only do something if there was an error
        self._provider_bootstrapper.name_resolution.connect(
            self._intermediate_stage)
        self._provider_bootstrapper.https_connection.connect(
            self._intermediate_stage)
        self._provider_bootstrapper.download_ca_cert.connect(
            self._intermediate_stage)

        # Important stages, loads the provider config and checks
        # certificates
        self._provider_bootstrapper.download_provider_info.connect(
            self._load_provider_config)
        self._provider_bootstrapper.check_api_certificate.connect(
            self._provider_config_loaded)

        # This thread is similar to the provider bootstrapper
        self._eip_bootstrapper = EIPBootstrapper()

        self._eip_bootstrapper.download_config.connect(
            self._eip_intermediate_stage)
        self._eip_bootstrapper.download_client_certificate.connect(
            self._finish_eip_bootstrap)

        self._soledad_bootstrapper = SoledadBootstrapper()
        self._soledad_bootstrapper.download_config.connect(
            self._soledad_intermediate_stage)
        self._soledad_bootstrapper.gen_key.connect(
            self._soledad_bootstrapped_stage)

        self._smtp_bootstrapper = SMTPBootstrapper()
        self._smtp_bootstrapper.download_config.connect(
            self._smtp_bootstrapped_stage)

        self._vpn = VPN()
        self._vpn.qtsigs.state_changed.connect(
            self._status_panel.update_vpn_state)
        self._vpn.qtsigs.status_changed.connect(
            self._status_panel.update_vpn_status)
        self._vpn.qtsigs.process_finished.connect(
            self._eip_finished)

        self.ui.action_log_out.setEnabled(False)
        self.ui.action_log_out.triggered.connect(self._logout)
        self.ui.action_about_leap.triggered.connect(self._about)
        self.ui.action_quit.triggered.connect(self.quit)
        self.ui.action_wizard.triggered.connect(self._launch_wizard)
        self.ui.action_show_logs.triggered.connect(self._show_logger_window)
        self.raise_window.connect(self._do_raise_mainwindow)

        # Used to differentiate between real quits and close to tray
        self._really_quit = False

        self._systray = None

        self._action_eip_provider = QtGui.QAction(
            self.tr("No default provider"), self)
        self._action_eip_provider.setEnabled(False)
        self._action_eip_status = QtGui.QAction(
            self.tr("Encrypted internet is OFF"),
            self)
        self._action_eip_status.setEnabled(False)

        self._status_panel.set_action_eip_status(
            self._action_eip_status)

        self._action_eip_startstop = QtGui.QAction(
            self.tr("Turn OFF"), self)
        self._action_eip_startstop.triggered.connect(
            self._stop_eip)
        self._action_eip_startstop.setEnabled(False)
        self._status_panel.set_action_eip_startstop(
            self._action_eip_startstop)

        self._action_visible = QtGui.QAction(self.tr("Hide Main Window"), self)
        self._action_visible.triggered.connect(self._toggle_visible)

        self._enabled_services = []

        self._center_window()

        self.ui.lblNewUpdates.setVisible(False)
        self.ui.btnMore.setVisible(False)
        self.ui.btnMore.clicked.connect(self._updates_details)
        self.new_updates.connect(self._react_to_new_updates)

        init_platform()

        self._wizard = None
        self._wizard_firstrun = False

        self._logger_window = None

        self._bypass_checks = bypass_checks

        self._soledad = None
        self._keymanager = None

        self._login_defer = None
        self._download_provider_defer = None

        self._smtp_config = SMTPConfig()

        if self._first_run():
            self._wizard_firstrun = True
            self._wizard = Wizard(standalone=standalone,
                                  bypass_checks=bypass_checks)
            # Give this window time to finish init and then show the wizard
            QtCore.QTimer.singleShot(1, self._launch_wizard)
            self._wizard.accepted.connect(self._finish_init)
            self._wizard.rejected.connect(self._rejected_wizard)
        else:
            self._finish_init()

    def _rejected_wizard(self):
        """
        SLOT
        TRIGGERS: self._wizard.rejected

        Called if the wizard has been cancelled or closed before
        finishing.
        """
        if self._wizard_firstrun:
            self._settings.set_properprovider(False)
            self.quit()
        else:
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
            self._wizard = Wizard(bypass_checks=self._bypass_checks)
            self._wizard.accepted.connect(self._finish_init)
            self._wizard.rejected.connect(self._wizard.close)

        self.setVisible(False)
        # Do NOT use exec_, it will use a child event loop!
        # Refer to http://www.themacaque.com/?p=1067 for funny details.
        self._wizard.show()
        if IS_MAC:
            self._wizard.raise_()
        self._wizard.finished.connect(self._wizard_finished)

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
        from leap.util.leap_log_handler import LeapLogHandler
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
          self.ui.btnShowLog.clicked

        Displays the window with the history of messages logged until now
        and displays the new ones on arrival.
        """
        if self._logger_window is None:
            leap_log_handler = self._get_leap_logging_handler()
            if leap_log_handler is None:
                logger.error('Leap logger handler not found')
            else:
                self._logger_window = LoggerWindow(handler=leap_log_handler)
                self._logger_window.setVisible(
                    not self._logger_window.isVisible())
                self.ui.btnShowLog.setChecked(self._logger_window.isVisible())
        else:
            self._logger_window.setVisible(not self._logger_window.isVisible())
            self.ui.btnShowLog.setChecked(self._logger_window.isVisible())

        self._logger_window.finished.connect(self._uncheck_logger_button)

    def _uncheck_logger_button(self):
        """
        SLOT
        Sets the checked state of the loggerwindow button to false.
        """
        self.ui.btnShowLog.setChecked(False)

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
        msg = self.tr("The LEAPClient app is ready to update, please"
                      " restart the application.")

        # We assume that if there is nothing in the contents, then
        # the LEAPClient bundle is what needs updating.
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

        Also called at the end of the constructor if not first run,
        and after _rejected_wizard if not first run.

        Implements the behavior after either constructing the
        mainwindow object, loading the saved user/password, or after
        the wizard has been executed.
        """
        # XXX: May be this can be divided into two methods?

        self._login_widget.set_providers(self._configured_providers())
        self._show_systray()
        self.show()
        if IS_MAC:
            self.raise_()

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
            self._wizard = None
            self._settings.set_properprovider(True)
        else:
            self._try_autostart_eip()
            if not self._settings.get_remember():
                # nothing to do here
                return

            saved_user = self._settings.get_user()

            try:
                username, domain = saved_user.split('@')
            except (ValueError, AttributeError) as e:
                # if the saved_user does not contain an '@' or its None
                logger.error('Username@provider malformed. %r' % (e, ))
                saved_user = None

            if saved_user is not None and has_keyring():
                # fill the username
                self._login_widget.set_user(username)

                # select the configured provider in the combo box
                self._login_widget.select_provider_by_name(domain)

                self._login_widget.set_remember(True)

                saved_password = None
                try:
                    saved_password = keyring.get_password(self.KEYRING_KEY,
                                                          saved_user
                                                          .encode("utf8"))
                except ValueError, e:
                    logger.debug("Incorrect Password. %r." % (e,))

                if saved_password is not None:
                    self._login_widget.set_password(
                        saved_password.decode("utf8"))
                    self._login()

    def _try_autostart_eip(self):
        """
        Tries to autostart EIP
        """
        default_provider = self._settings.get_defaultprovider()

        if default_provider is None:
            logger.info("Cannot autostart Encrypted Internet because there is "
                        "no default provider configured")
            return

        self._action_eip_provider.setText(default_provider)

        self._enabled_services = self._settings.get_enabled_services(
            default_provider)

        if self._provisional_provider_config.load(
            os.path.join("leap",
                         "providers",
                         default_provider,
                         "provider.json")):
            self._download_eip_config()
        else:
            # XXX: Display a proper message to the user
            logger.error("Unable to load %s config, cannot autostart." %
                         (default_provider,))

    def _show_systray(self):
        """
        Sets up the systray icon
        """
        if self._systray is not None:
            self._systray.setVisible(True)
            return

        # Placeholder actions
        # They are temporary to display the tray as designed
        preferences_action = QtGui.QAction(self.tr("Preferences"), self)
        preferences_action.setEnabled(False)
        help_action = QtGui.QAction(self.tr("Help"), self)
        help_action.setEnabled(False)

        systrayMenu = QtGui.QMenu(self)
        systrayMenu.addAction(self._action_visible)
        systrayMenu.addSeparator()
        systrayMenu.addAction(self._action_eip_provider)
        systrayMenu.addAction(self._action_eip_status)
        systrayMenu.addAction(self._action_eip_startstop)
        systrayMenu.addSeparator()
        systrayMenu.addAction(preferences_action)
        systrayMenu.addAction(help_action)
        systrayMenu.addSeparator()
        systrayMenu.addAction(self.ui.action_log_out)
        systrayMenu.addAction(self.ui.action_quit)
        self._systray = QtGui.QSystemTrayIcon(self)
        self._systray.setContextMenu(systrayMenu)
        self._systray.setIcon(self._status_panel.ERROR_ICON_TRAY)
        self._systray.setVisible(True)
        self._systray.activated.connect(self._tray_activated)

        self._status_panel.set_systray(self._systray)

    def _tray_activated(self, reason=None):
        """
        SLOT
        TRIGGER: self._systray.activated

        Displays the context menu from the tray icon
        """
        get_action = lambda visible: (
            self.tr("Show Main Window"),
            self.tr("Hide Main Window"))[int(visible)]

        # set labels
        visible = self.isVisible()
        self._action_visible.setText(get_action(visible))

        context_menu = self._systray.contextMenu()
        if not IS_MAC:
            # for some reason, context_menu.show()
            # is failing in a way beyond my understanding.
            # (not working the first time it's clicked).
            # this works however.
            context_menu.exec_(self._systray.geometry().center())

    def _toggle_visible(self):
        """
        SLOT
        TRIGGER: self._action_visible.triggered

        Toggles the window visibility
        """
        if not self.isVisible():
            self.show()
            self.raise_()
        else:
            self.hide()

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

        Display the About LEAP dialog
        """
        QtGui.QMessageBox.about(
            self, self.tr("About LEAP - %s") % (VERSION,),
            self.tr("version: <b>%s</b><br>"
                    "LEAP is a non-profit dedicated to giving "
                    "all internet users access to secure "
                    "communication. Our focus is on adapting "
                    "encryption technology to make it easy to use "
                    "and widely available. "
                    "<a href=\"https://leap.se\">More about LEAP"
                    "</a>") % (VERSION,))

    def changeEvent(self, e):
        """
        Reimplements the changeEvent method to minimize to tray
        """
        if QtGui.QSystemTrayIcon.isSystemTrayAvailable() and \
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

    def _configured_providers(self):
        """
        Returns the available providers based on the file structure

        :rtype: list
        """

        # TODO: check which providers have a valid certificate among
        # other things, not just the directories
        providers = []
        try:
            providers = os.listdir(
                os.path.join(self._provider_config.get_path_prefix(),
                             "leap",
                             "providers"))
        except Exception as e:
            logger.debug("Error listing providers, assume there are none. %r"
                         % (e,))

        return providers

    def _first_run(self):
        """
        Returns True if there are no configured providers. False otherwise

        :rtype: bool
        """
        has_provider_on_disk = len(self._configured_providers()) != 0
        is_proper_provider = self._settings.get_properprovider()
        return not (has_provider_on_disk and is_proper_provider)

    def _download_provider_config(self):
        """
        Starts the bootstrapping sequence. It will download the
        provider configuration if it's not present, otherwise will
        emit the corresponding signals inmediately
        """
        provider = self._login_widget.get_selected_provider()

        pb = self._provider_bootstrapper
        d = pb.run_provider_select_checks(provider, download_if_needed=True)
        self._download_provider_defer = d

    def _load_provider_config(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.download_provider_info

        Once the provider config has been downloaded, this loads the
        self._provider_config instance with it and starts the second
        part of the bootstrapping sequence

        :param data: result from the last stage of the
        run_provider_select_checks
        :type data: dict
        """
        if data[self._provider_bootstrapper.PASSED_KEY]:
            provider = self._login_widget.get_selected_provider()

            # If there's no loaded provider or
            # we want to connect to other provider...
            if (not self._provider_config.loaded() or
                    self._provider_config.get_domain() != provider):
                self._provider_config.load(
                    os.path.join("leap", "providers",
                                 provider, "provider.json"))

            if self._provider_config.loaded():
                self._provider_bootstrapper.run_provider_setup_checks(
                    self._provider_config,
                    download_if_needed=True)
            else:
                self._login_widget.set_status(
                    self.tr("Unable to login: Problem with provider"))
                logger.error("Could not load provider configuration.")
                self._login_widget.set_enabled(True)
        else:
            self._login_widget.set_status(
                self.tr("Unable to login: Problem with provider"))
            logger.error(data[self._provider_bootstrapper.ERROR_KEY])
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
        leap_assert(self._provider_config, "We need a provider config")

        username = self._login_widget.get_user()
        password = self._login_widget.get_password()
        provider = self._login_widget.get_selected_provider()

        self._enabled_services = self._settings.get_enabled_services(
            self._login_widget.get_selected_provider())

        if len(provider) == 0:
            self._login_widget.set_status(
                self.tr("Please select a valid provider"))
            return

        if len(username) == 0:
            self._login_widget.set_status(
                self.tr("Please provide a valid username"))
            return

        if len(password) == 0:
            self._login_widget.set_status(
                self.tr("Please provide a valid Password"))
            return

        self._login_widget.set_status(self.tr("Logging in..."), error=False)
        self._login_widget.set_enabled(False)
        self._login_widget.set_cancel(True)

        if self._login_widget.get_remember() and has_keyring():
            # in the keyring and in the settings
            # we store the value 'usename@provider'
            username_domain = (username + '@' + provider).encode("utf8")
            try:
                keyring.set_password(self.KEYRING_KEY,
                                     username_domain,
                                     password.encode("utf8"))
                # Only save the username if it was saved correctly in
                # the keyring
                self._settings.set_user(username_domain)
            except Exception as e:
                logger.error("Problem saving data to keyring. %r"
                             % (e,))

        self._download_provider_config()

    def _cancel_login(self):
        """
        SLOT
        TRIGGERS:
          self._login_widget.cancel_login

        Stops the login sequence.
        """
        logger.debug("Cancelling log in.")
        self._login_widget.set_cancel(False)

        if self._download_provider_defer:
            logger.debug("Cancelling download provider defer.")
            self._download_provider_defer.cancel()

        if self._login_defer:
            logger.debug("Cancelling login defer.")
            self._login_defer.cancel()

    def _provider_config_loaded(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.check_api_certificate

        Once the provider configuration is loaded, this starts the SRP
        authentication
        """
        leap_assert(self._provider_config, "We need a provider config!")

        if data[self._provider_bootstrapper.PASSED_KEY]:
            username = self._login_widget.get_user().encode("utf8")
            password = self._login_widget.get_password().encode("utf8")

            if self._srp_auth is None:
                self._srp_auth = SRPAuth(self._provider_config)
                self._srp_auth.authentication_finished.connect(
                    self._authentication_finished)
                self._srp_auth.logout_finished.connect(
                    self._done_logging_out)

            # TODO: Add errback!
            self._login_defer = self._srp_auth.authenticate(username, password)
        else:
            self._login_widget.set_status(
                "Unable to login: Problem with provider")
            logger.error(data[self._provider_bootstrapper.ERROR_KEY])
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
            self.ui.action_log_out.setEnabled(True)
            # We leave a bit of room for the user to see the
            # "Succeeded" message and then we switch to the EIP status
            # panel
            QtCore.QTimer.singleShot(1000, self._switch_to_status)
            self._login_defer = None
        else:
            self._login_widget.set_enabled(True)

    def _switch_to_status(self):
        """
        Changes the stackedWidget index to the EIP status one and
        triggers the eip bootstrapping
        """
        if not self._already_started_eip:
            self._status_panel.set_provider(
                "%s@%s" % (self._login_widget.get_user(),
                           self._get_best_provider_config().get_domain()))

        self.ui.stackedWidget.setCurrentIndex(self.EIP_STATUS_INDEX)

        self._soledad_bootstrapper.run_soledad_setup_checks(
            self._provider_config,
            self._login_widget.get_user(),
            self._login_widget.get_password(),
            download_if_needed=True)

        self._download_eip_config()

    def _soledad_intermediate_stage(self, data):
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
            # TODO: display in the GUI:
            # should pass signal to a slot in status_panel
            # that sets the global status
            logger.warning("Soledad failed to start: %s" %
                           (data[self._soledad_bootstrapper.ERROR_KEY],))

    def _soledad_bootstrapped_stage(self, data):
        """
        SLOT
        TRIGGERS:
          self._soledad_bootstrapper.gen_key

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.

        :param data: result from the bootstrapping stage for Soledad
        :type data: dict
        """
        passed = data[self._soledad_bootstrapper.PASSED_KEY]
        if not passed:
            logger.error(data[self._soledad_bootstrapper.ERROR_KEY])
            return

        logger.debug("Done bootstrapping Soledad")

        self._soledad = self._soledad_bootstrapper.soledad
        self._keymanager = self._soledad_bootstrapper.keymanager

        if self._provider_config.provides_mx() and \
                self._enabled_services.count(self.MX_SERVICE) > 0:
            self._smtp_bootstrapper.run_smtp_setup_checks(
                self._provider_config,
                self._smtp_config,
                True)
        else:
            if self._enabled_services.count(self.MX_SERVICE) > 0:
                pass  # TODO: show MX status
                #self._status_panel.set_eip_status(
                #    self.tr("%s does not support MX") %
                #    (self._provider_config.get_domain(),),
                #                     error=True)
            else:
                pass  # TODO: show MX status
                #self._status_panel.set_eip_status(
                #    self.tr("MX is disabled"))

    # Service control methods: eip

    def _smtp_bootstrapped_stage(self, data):
        """
        SLOT
        TRIGGERS:
          self._smtp_bootstrapper.download_config

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.

        :param data: result from the bootstrapping stage for Soledad
        :type data: dict
        """
        passed = data[self._smtp_bootstrapper.PASSED_KEY]
        if not passed:
            logger.error(data[self._smtp_bootstrapper.ERROR_KEY])
            return
        logger.debug("Done bootstrapping SMTP")

        hosts = self._smtp_config.get_hosts()
        # TODO: handle more than one host and define how to choose
        if len(hosts) > 0:
            hostname = hosts.keys()[0]
            logger.debug("Using hostname %s for SMTP" % (hostname,))
            host = hosts[hostname][self.IP_KEY].encode("utf-8")
            port = hosts[hostname][self.PORT_KEY]
            # TODO: pick local smtp port in a better way
            # TODO: Make the encrypted_only configurable

            from leap.mail.smtp import setup_smtp_relay
            client_cert = self._eip_config.get_client_cert_path(
                self._provider_config)
            setup_smtp_relay(port=1234,
                             keymanager=self._keymanager,
                             smtp_host=host,
                             smtp_port=port,
                             smtp_cert=client_cert,
                             smtp_key=client_cert,
                             encrypted_only=False)

    def _get_socket_host(self):
        """
        Returns the socket and port to be used for VPN

        :rtype: tuple (str, str) (host, port)
        """

        # TODO: make this properly multiplatform

        if platform.system() == "Windows":
            host = "localhost"
            port = "9876"
        else:
            host = os.path.join(tempfile.mkdtemp(prefix="leap-tmp"),
                                'openvpn.socket')
            port = "unix"

        return host, port

    def _start_eip(self):
        """
        SLOT
        TRIGGERS:
          self._status_panel.start_eip
          self._action_eip_startstop.triggered
        or called from _finish_eip_bootstrap

        Starts EIP
        """
        self._status_panel.eip_pre_up()
        self.user_stopped_eip = False
        provider_config = self._get_best_provider_config()

        try:
            host, port = self._get_socket_host()
            self._vpn.start(eipconfig=self._eip_config,
                            providerconfig=provider_config,
                            socket_host=host,
                            socket_port=port)

            self._settings.set_defaultprovider(
                provider_config.get_domain())

            provider = provider_config.get_domain()
            if self._logged_user is not None:
                provider = "%s@%s" % (self._logged_user, provider)

            self._status_panel.set_provider(provider)

            self._action_eip_provider.setText(provider_config.get_domain())

            self._status_panel.eip_started()

            self._action_eip_startstop.setText(self.tr("Turn OFF"))
            self._action_eip_startstop.disconnect(self)
            self._action_eip_startstop.triggered.connect(
                self._stop_eip)
        except EIPNoPolkitAuthAgentAvailable:
            self._status_panel.set_global_status(
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
            self._status_panel.set_global_status(
                self.tr("Encrypted Internet cannot be started because "
                        "the tuntap extension is not installed properly "
                        "in your system."))
            self._set_eipstatus_off()
        except EIPNoPkexecAvailable:
            self._status_panel.set_global_status(
                self.tr("We could not find <b>pkexec</b> "
                        "in your system."),
                error=True)
            self._set_eipstatus_off()
        except OpenVPNNotFoundException:
            self._status_panel.set_global_status(
                self.tr("We could not find openvpn binary."),
                error=True)
            self._set_eipstatus_off()
        except OpenVPNAlreadyRunning as e:
            self._status_panel.set_global_status(
                self.tr("Another openvpn instance is already running, and "
                        "could not be stopped."),
                error=True)
            self._set_eipstatus_off()
        except AlienOpenVPNAlreadyRunning as e:
            self._status_panel.set_global_status(
                self.tr("Another openvpn instance is already running, and "
                        "could not be stopped because it was not launched by "
                        "LEAP. Please stop it and try again."),
                error=True)
            self._set_eipstatus_off()
        except VPNLauncherException as e:
            # XXX We should implement again translatable exceptions so
            # we can pass a translatable string to the panel (usermessage attr)
            self._status_panel.set_global_status("%s" % (e,), error=True)
            self._set_eipstatus_off()
        else:
            self._already_started_eip = True

    def _set_eipstatus_off(self):
        """
        Sets eip status to off
        """
        self._status_panel.set_eip_status(self.tr("OFF"), error=True)
        self._status_panel.set_eip_status_icon("error")
        self._status_panel.set_startstop_enabled(True)
        self._status_panel.eip_stopped()

        self._set_action_eipstart_off()

    def _set_action_eipstart_off(self):
        """
        Sets eip startstop action to OFF status.
        """
        self._action_eip_startstop.setText(self.tr("Turn ON"))
        self._action_eip_startstop.disconnect(self)
        self._action_eip_startstop.triggered.connect(
            self._start_eip)

    def _stop_eip(self, abnormal=False):
        """
        SLOT
        TRIGGERS:
          self._status_panel.stop_eip
          self._action_eip_startstop.triggered
        or called from _eip_finished

        Stops vpn process and makes gui adjustments to reflect
        the change of state.

        :param abnormal: whether this was an abnormal termination.
        :type abnormal: bool
        """
        if abnormal:
            logger.warning("Abnormal EIP termination.")

        self.user_stopped_eip = True
        self._vpn.terminate()

        self._set_eipstatus_off()

        self._already_started_eip = False
        self._settings.set_defaultprovider(None)
        if self._logged_user:
            self._status_panel.set_provider(
                "%s@%s" % (self._logged_user,
                           self._get_best_provider_config().get_domain()))

    def _get_best_provider_config(self):
        """
        Returns the best ProviderConfig to use at a moment. We may
        have to use self._provider_config or
        self._provisional_provider_config depending on the start
        status.

        :rtype: ProviderConfig
        """
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

    def _download_eip_config(self):
        """
        Starts the EIP bootstrapping sequence
        """
        leap_assert(self._eip_bootstrapper, "We need an eip bootstrapper!")

        provider_config = self._get_best_provider_config()

        if provider_config.provides_eip() and \
                self._enabled_services.count(self.OPENVPN_SERVICE) > 0 and \
                not self._already_started_eip:

            self._status_panel.set_eip_status(
                self.tr("Starting..."))
            self._eip_bootstrapper.run_eip_setup_checks(
                provider_config,
                download_if_needed=True)
            self._already_started_eip = True
        elif not self._already_started_eip:
            if self._enabled_services.count(self.OPENVPN_SERVICE) > 0:
                self._status_panel.set_eip_status(
                    self.tr("Not supported"),
                    error=True)
            else:
                self._status_panel.set_eip_status(self.tr("Disabled"))
            self._status_panel.set_startstop_enabled(False)

    def _finish_eip_bootstrap(self, data):
        """
        SLOT
        TRIGGER: self._eip_bootstrapper.download_client_certificate

        Starts the VPN thread if the eip configuration is properly
        loaded
        """
        leap_assert(self._eip_config, "We need an eip config!")

        provider_config = self._get_best_provider_config()

        domain = provider_config.get_domain()

        if data[self._eip_bootstrapper.PASSED_KEY] and \
                (self._eip_config.loaded() or
                 self._eip_config.load(os.path.join("leap",
                                                    "providers",
                                                    domain,
                                                    "eip-service.json"))):
                self._start_eip()
        else:
            if data[self._eip_bootstrapper.PASSED_KEY]:
                self._status_panel.set_eip_status(
                    self.tr("Could not load Encrypted Internet "
                            "Configuration."),
                    error=True)
            else:
                self._status_panel.set_eip_status(
                    data[self._eip_bootstrapper.ERROR_KEY],
                    error=True)
            self._already_started_eip = False

    def _logout(self):
        """
        SLOT
        TRIGGER: self.ui.action_log_out.triggered

        Starts the logout sequence
        """
        # XXX: If other defers are doing authenticated stuff, this
        # might conflict with those. CHECK!
        threads.deferToThread(self._srp_auth.logout)

    def _done_logging_out(self, ok, message):
        """
        SLOT
        TRIGGER: self._srp_auth.logout_finished

        Switches the stackedWidget back to the login stage after
        logging out
        """
        self._logged_user = None
        self.ui.action_log_out.setEnabled(False)
        self.ui.stackedWidget.setCurrentIndex(self.LOGIN_INDEX)
        self._login_widget.set_password("")
        self._login_widget.set_enabled(True)
        self._login_widget.set_status("")

    def _intermediate_stage(self, data):
        """
        SLOT
        TRIGGERS:
          self._provider_bootstrapper.name_resolution
          self._provider_bootstrapper.https_connection
          self._provider_bootstrapper.download_ca_cert
          self._eip_bootstrapper.download_config

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.
        """
        passed = data[self._provider_bootstrapper.PASSED_KEY]
        if not passed:
            self._login_widget.set_cancel(False)
            self._login_widget.set_enabled(True)
            self._login_widget.set_status(
                self.tr("Unable to connect: Problem with provider"))
            logger.error(data[self._provider_bootstrapper.ERROR_KEY])

    def _eip_intermediate_stage(self, data):
        """
        SLOT
        TRIGGERS:
          self._eip_bootstrapper.download_config

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.
        """
        passed = data[self._provider_bootstrapper.PASSED_KEY]
        if not passed:
            self._login_widget.set_status(
                self.tr("Unable to connect: Problem with provider"))
            logger.error(data[self._provider_bootstrapper.ERROR_KEY])
            self._already_started_eip = False

    def _eip_finished(self, exitCode):
        """
        SLOT
        TRIGGERS:
          self._vpn.process_finished

        Triggered when the EIP/VPN process finishes to set the UI
        accordingly.
        """
        logger.info("VPN process finished with exitCode %s..."
                    % (exitCode,))

        # Ideally we would have the right exit code here,
        # but the use of different wrappers (pkexec, cocoasudo) swallows
        # the openvpn exit code so we get zero exit in some cases  where we
        # shouldn't. As a workaround we just use a flag to indicate
        # a purposeful switch off, and mark everything else as unexpected.

        # In the near future we should trigger a native notification from here,
        # since the user really really wants to know she is unprotected asap.
        # And the right thing to do will be to fail-close.

        # TODO we should have a way of parsing the latest lines in the vpn
        # log buffer so we can have a more precise idea of which type
        # of error did we have (server side, local problem, etc)
        abnormal = True

        # XXX check if these exitCodes are pkexec/cocoasudo specific
        if exitCode in (126, 127):
            self._status_panel.set_global_status(
                self.tr("Encrypted Internet could not be launched "
                        "because you did not authenticate properly."),
                error=True)
            self._vpn.killit()
        elif exitCode != 0 or not self.user_stopped_eip:
            self._status_panel.set_global_status(
                self.tr("Encrypted Internet finished in an "
                        "unexpected manner!"), error=True)
        else:
            abnormal = False
        if exitCode == 0 and IS_MAC:
            # XXX remove this warning after I fix cocoasudo.
            logger.warning("The above exit code MIGHT BE WRONG.")
        self._stop_eip(abnormal)

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

        if self._srp_auth is not None:
            if self._srp_auth.get_session_id() is not None or \
               self._srp_auth.get_token() is not None:
                # XXX this can timeout after loong time: See #3368
                self._srp_auth.logout()

        if self._soledad:
            logger.debug("Closing soledad...")
            self._soledad.close()
        else:
            logger.error("No instance of soledad was found.")

        logger.debug('Cleaning pidfiles')
        self._cleanup_pidfiles()

        logger.debug('Terminating vpn')
        self._vpn.terminate(shutdown=True)

    def quit(self):
        """
        Cleanup and tidely close the main window before quitting.
        """
        self._cleanup_and_quit()

        self._really_quit = True

        if self._wizard:
            self._wizard.close()

        if self._logger_window:
            self._logger_window.close()

        if self._login_defer:
            logger.debug("Cancelling login defer.")
            self._login_defer.cancel()

        if self._download_provider_defer:
            logger.debug("Cancelling download provider defer.")
            self._download_provider_defer.cancel()

        self.close()

        if self._quit_callback:
            self._quit_callback()

        logger.debug('Bye.')


if __name__ == "__main__":
    import signal

    def sigint_handler(*args, **kwargs):
        logger.debug('SIGINT catched. shutting down...')
        mainwindow = args[0]
        mainwindow.quit()

    import sys

    logger = logging.getLogger(name='leap')
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    app = QtGui.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()

    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sigint = partial(sigint_handler, mainwindow)
    signal.signal(signal.SIGINT, sigint)

    sys.exit(app.exec_())
