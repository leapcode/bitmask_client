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
from leap.services.eip.eipbootstrapper import EIPBootstrapper
from leap.services.eip.eipconfig import EIPConfig
from leap.services.eip.providerbootstrapper import ProviderBootstrapper
from leap.services.soledad.soledadbootstrapper import SoledadBootstrapper
from leap.services.mail.smtpbootstrapper import SMTPBootstrapper
from leap.platform_init import IS_MAC, IS_WIN
from leap.platform_init.initializers import init_platform
from leap.services.eip.vpn import VPN
from leap.services.eip.vpnlaunchers import (VPNLauncherException,
                                            OpenVPNNotFoundException,
                                            EIPNoPkexecAvailable,
                                            EIPNoPolkitAuthAgentAvailable)
from leap.util import __version__ as VERSION

from leap.services.mail.smtpconfig import SMTPConfig

if IS_WIN:
    from leap.platform_init.locks import WindowsLock

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
                 callback=self._new_updates_available)
        register(signal=proto.RAISE_WINDOW,
                 callback=self._on_raise_window_event)
        self._quit_callback = quit_callback

        self._updates_content = ""

        if IS_MAC:
            EIP_ICONS = (
                ":/images/conn_connecting-light.png",
                ":/images/conn_connected-light.png",
                ":/images/conn_error-light.png")
        else:
            EIP_ICONS = (
                ":/images/conn_connecting.png",
                ":/images/conn_connected.png",
                ":/images/conn_error.png")

        self.CONNECTING_ICON = QtGui.QPixmap(EIP_ICONS[0])
        self.CONNECTED_ICON = QtGui.QPixmap(EIP_ICONS[1])
        self.ERROR_ICON = QtGui.QPixmap(EIP_ICONS[2])

        self.LOGGED_OUT_ICON = QtGui.QPixmap(":/images/leap-gray-big.png")
        self.LOGGED_IN_ICON = QtGui.QPixmap(":/images/leap-color-big.png")

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.lnPassword.setEchoMode(QtGui.QLineEdit.Password)

        self.ui.btnLogin.clicked.connect(self._login)
        self.ui.lnUser.returnPressed.connect(self._focus_password)
        self.ui.lnPassword.returnPressed.connect(self._login)

        self.ui.stackedWidget.setCurrentIndex(self.LOGIN_INDEX)

        self.ui.btnEipStartStop.setEnabled(False)
        self.ui.btnEipStartStop.clicked.connect(
            self._start_eip)

        # This is loaded only once, there's a bug when doing that more
        # than once
        ProviderConfig.standalone = standalone
        EIPConfig.standalone = standalone
        self._standalone = standalone
        self._provider_config = ProviderConfig()
        self._eip_config = EIPConfig()

        # This is created once we have a valid provider config
        self._srp_auth = None

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
            self._intermediate_stage)
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
        self._vpn.state_changed.connect(self._update_vpn_state)
        self._vpn.status_changed.connect(self._update_vpn_status)
        self._vpn.process_finished.connect(
            self._eip_finished)

        self.ui.chkRemember.stateChanged.connect(
            self._remember_state_changed)
        self.ui.chkRemember.setEnabled(keyring.get_keyring() is not None)

        self.ui.action_sign_out.setEnabled(False)
        self.ui.action_sign_out.triggered.connect(self._logout)
        self.ui.action_about_leap.triggered.connect(self._about)
        self.ui.action_quit.triggered.connect(self.quit)
        self.ui.action_wizard.triggered.connect(self._launch_wizard)
        self.ui.action_show_logs.triggered.connect(self._show_logger_window)
        self.raise_window.connect(self._do_raise_mainwindow)

        # Used to differentiate between real quits and close to tray
        self._really_quit = False

        self._systray = None

        self._action_eip_status = QtGui.QAction(self.tr("Encrypted internet is OFF"),
                                                self)
        self._action_eip_status.setEnabled(False)
        self._action_eip_startstop = QtGui.QAction(self.tr("Turn encryption ON"), self)
        self._action_eip_startstop.triggered.connect(
            self._stop_eip)
        self._action_eip_write = QtGui.QAction(
            QtGui.QIcon(":/images/Arrow-Up-32.png"),
            "%12.2f Kb" % (0.0,), self)
        self._action_eip_write.setEnabled(False)
        self._action_eip_read = QtGui.QAction(
            QtGui.QIcon(":/images/Arrow-Down-32.png"),
            "%12.2f Kb" % (0.0,), self)
        self._action_eip_read.setEnabled(False)

        self._action_visible = QtGui.QAction(self.tr("Hide Main Window"), self)
        self._action_visible.triggered.connect(self._toggle_visible)

        self._enabled_services = []
        self._settings = LeapSettings(standalone)

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
        if self._wizard_firstrun:
            self._settings.set_properprovider(False)
            self.quit()
        else:
            self._finish_init()

    def _launch_wizard(self):
        if self._wizard is None:
            self._wizard = Wizard(bypass_checks=self._bypass_checks)
        self._wizard.accepted.connect(self._finish_init)
        self._wizard.exec_()
        self._wizard = None

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
        Displays the window with the history of messages logged until now
        and displays the new ones on arrival.
        """
        if self._logger_window is None:
            leap_log_handler = self._get_leap_logging_handler()
            if leap_log_handler is None:
                logger.error('Leap logger handler not found')
            else:
                self._logger_window = LoggerWindow(handler=leap_log_handler)
                self._logger_window.show()
        else:
            self._logger_window.show()

    def _remember_state_changed(self, state):
        enable = True if state == QtCore.Qt.Checked else False
        self.ui.chkAutoLogin.setEnabled(enable)
        self._settings.set_remember(enable)

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
        self.ui.cmbProviders.clear()
        self.ui.cmbProviders.addItems(self._configured_providers())
        self._show_systray()
        self.show()

        if self._wizard:
            possible_username = self._wizard.get_username()
            possible_password = self._wizard.get_password()

            # select the configured provider in the combo box
            domain = self._wizard.get_domain()
            provider_index = self.ui.cmbProviders.findText(domain)
            self.ui.cmbProviders.setCurrentIndex(provider_index)

            self.ui.chkRemember.setChecked(self._wizard.get_remember())
            self._enabled_services = list(self._wizard.get_services())
            self._settings.set_enabled_services(
                self.ui.cmbProviders.currentText(),
                self._enabled_services)
            if possible_username is not None:
                self.ui.lnUser.setText(possible_username)
                self._focus_password()
            if possible_password is not None:
                self.ui.lnPassword.setText(possible_password)
                self.ui.chkRemember.setChecked(True)
                self._login()
            self._wizard = None
            self._settings.set_properprovider(True)
        else:
            if not self._settings.get_remember():
                # nothing to do here
                return

            saved_user = self._settings.get_user()
            auto_login = self._settings.get_autologin()

            try:
                username, domain = saved_user.split('@')
            except (ValueError, AttributeError) as e:
                # if the saved_user does not contain an '@' or its None
                logger.error('Username@provider malformed. %r' % (e, ))
                saved_user = None

            if saved_user is not None:
                # fill the username
                self.ui.lnUser.setText(username)

                # select the configured provider in the combo box
                provider_index = self.ui.cmbProviders.findText(domain)
                self.ui.cmbProviders.setCurrentIndex(provider_index)

                self.ui.chkRemember.setChecked(True)
                self.ui.chkAutoLogin.setEnabled(self.ui.chkRemember
                                                .isEnabled())

                saved_password = None
                try:
                    saved_password = keyring.get_password(self.KEYRING_KEY,
                                                          saved_user
                                                          .encode("utf8"))
                except ValueError, e:
                    logger.debug("Incorrect Password. %r." % (e,))

                if saved_password is not None:
                    self.ui.lnPassword.setText(saved_password.decode("utf8"))

                # Only automatically login if there is a saved user
                # and the password was retrieved right
                self.ui.chkAutoLogin.setChecked(auto_login)
                if auto_login and saved_password:
                    self._login()

    def _show_systray(self):
        """
        Sets up the systray icon
        """
        if self._systray is not None:
            self._systray.setVisible(True)
            return
        systrayMenu = QtGui.QMenu(self)
        systrayMenu.addAction(self._action_visible)
        systrayMenu.addAction(self.ui.action_sign_out)
        systrayMenu.addSeparator()
        systrayMenu.addAction(self.ui.action_quit)
        systrayMenu.addSeparator()
        systrayMenu.addAction(self._action_eip_status)
        systrayMenu.addAction(self._action_eip_startstop)
        self._systray = QtGui.QSystemTrayIcon(self)
        self._systray.setContextMenu(systrayMenu)
        self._systray.setIcon(QtGui.QIcon(self.ERROR_ICON))
        self._systray.setVisible(True)
        self._systray.activated.connect(self._toggle_visible)

    def _toggle_visible(self, reason=None):
        """
        SLOT
        TRIGGER: self._systray.activated

        Toggles the window visibility
        """
        get_action = lambda visible: (
            self.tr("Show"),
            self.tr("Hide"))[int(visible)]

        minimized = self.isMinimized()

        if reason != QtGui.QSystemTrayIcon.Context:
            # do show
            if minimized:
                self.showNormal()
            self.setVisible(not self.isVisible())

            # set labels
            visible = self.isVisible()
            self._action_visible.setText(get_action(visible))

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
        self._settings.set_autologin(self.ui.chkAutoLogin.isChecked())

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

    def _focus_password(self):
        """
        Focuses in the password lineedit
        """
        self.ui.lnPassword.setFocus()

    def _set_status(self, status, error=True):
        """
        Sets the status label at the login stage to status

        :param status: status message
        :type status: str
        """
        if error:
            status = "<font color='red'><b>%s</b></font>" % (status,)
        self.ui.lblStatus.setText(status)

    def _set_eip_status(self, status, error=False):
        """
        Sets the status label at the VPN stage to status

        :param status: status message
        :type status: str
        """
        self._systray.setToolTip(status)
        if error:
            status = "<font color='red'><b>%s</b></font>" % (status,)
        self.ui.lblEIPStatus.setText(status)

    def _login_set_enabled(self, enabled=False):
        """
        Enables or disables all the login widgets

        :param enabled: wether they should be enabled or not
        :type enabled: bool
        """
        self.ui.lnUser.setEnabled(enabled)
        self.ui.lnPassword.setEnabled(enabled)
        self.ui.btnLogin.setEnabled(enabled)
        self.ui.chkRemember.setEnabled(enabled)
        if not enabled:
            self.ui.chkAutoLogin.setEnabled(False)
        self.ui.cmbProviders.setEnabled(enabled)

    def _download_provider_config(self):
        """
        Starts the bootstrapping sequence. It will download the
        provider configuration if it's not present, otherwise will
        emit the corresponding signals inmediately
        """
        provider = self.ui.cmbProviders.currentText()

        self._provider_bootstrapper.run_provider_select_checks(
            provider,
            download_if_needed=True)

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
            provider = self.ui.cmbProviders.currentText()
            if self._provider_config.loaded() or \
                    self._provider_config.load(os.path.join("leap",
                                                            "providers",
                                                            provider,
                                                            "provider.json")):
                self._provider_bootstrapper.run_provider_setup_checks(
                    self._provider_config,
                    download_if_needed=True)
            else:
                self._set_status(
                    self.tr("Could not load provider configuration"))
                self._login_set_enabled(True)
        else:
            self._set_status(data[self._provider_bootstrapper.ERROR_KEY])
            self._login_set_enabled(True)

    def _login(self):
        """
        SLOT
        TRIGGERS:
          self.ui.btnLogin.clicked
          self.ui.lnPassword.returnPressed

        Starts the login sequence. Which involves bootstrapping the
        selected provider if the selection is valid (not empty), then
        start the SRP authentication, and as the last step
        bootstrapping the EIP service
        """
        leap_assert(self._provider_config, "We need a provider config")

        username = self.ui.lnUser.text()
        password = self.ui.lnPassword.text()
        provider = self.ui.cmbProviders.currentText()

        self._enabled_services = self._settings.get_enabled_services(
            self.ui.cmbProviders.currentText())

        if len(provider) == 0:
            self._set_status(self.tr("Please select a valid provider"))
            return

        if len(username) == 0:
            self._set_status(self.tr("Please provide a valid username"))
            return

        if len(password) == 0:
            self._set_status(self.tr("Please provide a valid Password"))
            return

        self._set_status(self.tr("Logging in..."), error=False)
        self._login_set_enabled(False)

        if self.ui.chkRemember.isChecked():
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

    def _provider_config_loaded(self, data):
        """
        SLOT
        TRIGGER: self._provider_bootstrapper.check_api_certificate

        Once the provider configuration is loaded, this starts the SRP
        authentication
        """
        leap_assert(self._provider_config, "We need a provider config!")

        if data[self._provider_bootstrapper.PASSED_KEY]:
            username = self.ui.lnUser.text().encode("utf8")
            password = self.ui.lnPassword.text().encode("utf8")

            if self._srp_auth is None:
                self._srp_auth = SRPAuth(self._provider_config)
                self._srp_auth.authentication_finished.connect(
                    self._authentication_finished)
                self._srp_auth.logout_finished.connect(
                    self._done_logging_out)

            self._login_defer = self._srp_auth.authenticate(username, password)
        else:
            self._set_status(data[self._provider_bootstrapper.ERROR_KEY])
            self._login_set_enabled(True)

    def _authentication_finished(self, ok, message):
        """
        SLOT
        TRIGGER: self._srp_auth.authentication_finished

        Once the user is properly authenticated, try starting the EIP
        service
        """
        self._set_status(message, error=not ok)
        if ok:
            self.ui.action_sign_out.setEnabled(True)
            # We leave a bit of room for the user to see the
            # "Succeeded" message and then we switch to the EIP status
            # panel
            QtCore.QTimer.singleShot(1000, self._switch_to_status)
            self._login_defer = None
        else:
            self._login_set_enabled(True)

    def _switch_to_status(self):
        """
        Changes the stackedWidget index to the EIP status one and
        triggers the eip bootstrapping
        """
        self.ui.stackedWidget.setCurrentIndex(self.EIP_STATUS_INDEX)

        self._soledad_bootstrapper.run_soledad_setup_checks(
            self._provider_config,
            self.ui.lnUser.text(),
            self.ui.lnPassword.text(),
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
            # TODO: display in the GUI
            logger.error("Soledad failed to start: %s" %
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
        else:
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
                    #self._set_eip_status(self.tr("%s does not support MX") %
                    #                    (self._provider_config.get_domain(),),
                    #                     error=True)
                else:
                    pass  # TODO: show MX status
                    #self._set_eip_status(self.tr("MX is disabled"))

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
        else:
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

                # TODO: Remove mocking!!!
                self._keymanager.fetch_keys_from_server = Mock(return_value=[])
                from leap.mail.smtp import setup_smtp_relay
                setup_smtp_relay(port=1234,
                                 keymanager=self._keymanager,
                                 smtp_host=host,
                                 smtp_port=port,
                                 smtp_username=".",
                                 smtp_password=".",
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
          self.ui.btnEipStartStop.clicked
          self._action_eip_startstop.triggered
        or called from _finish_eip_bootstrap

        Starts EIP
        """
        try:
            host, port = self._get_socket_host()
            self._vpn.start(eipconfig=self._eip_config,
                            providerconfig=self._provider_config,
                            socket_host=host,
                            socket_port=port)

            self._settings.set_defaultprovider(
                self._provider_config.get_domain())
            self.ui.btnEipStartStop.setText(self.tr("Turn Encryption OFF"))
            self.ui.btnEipStartStop.disconnect(self)
            self.ui.btnEipStartStop.clicked.connect(
                self._stop_eip)
            self._action_eip_startstop.setText(self.tr("Turn Encryption OFF"))
            self._action_eip_startstop.disconnect(self)
            self._action_eip_startstop.triggered.connect(
                self._stop_eip)
        except EIPNoPolkitAuthAgentAvailable:
            self._set_eip_status(self.tr("We could not find any "
                                         "authentication "
                                         "agent in your system.<br/>"
                                         "Make sure you have "
                                         "<b>polkit-gnome-authentication-"
                                         "agent-1</b> "
                                         "running and try again."),
                                 error=True)
        except EIPNoPkexecAvailable:
            self._set_eip_status(self.tr("We could not find <b>pkexec</b> "
                                         "in your system."),
                                 error=True)
        except OpenVPNNotFoundException:
            self._set_eip_status(self.tr("We couldn't find openvpn"),
                                 error=True)
        except VPNLauncherException as e:
            self._set_eip_status("%s" % (e,), error=True)

        self.ui.btnEipStartStop.setEnabled(True)

    def _stop_eip(self):
        self._vpn.set_should_quit()
        self._set_eip_status(self.tr("EIP has stopped"))
        self._set_eip_status_icon("error")
        self.ui.btnEipStartStop.setText(self.tr("Turn Encryption ON"))
        self.ui.btnEipStartStop.disconnect(self)
        self.ui.btnEipStartStop.clicked.connect(
            self._start_eip)
        self._action_eip_startstop.setText(self.tr("Turn Encryption ON"))
        self._action_eip_startstop.disconnect(self)
        self._action_eip_startstop.triggered.connect(
            self._start_eip)

    def _download_eip_config(self):
        """
        Starts the EIP bootstrapping sequence
        """
        leap_assert(self._eip_bootstrapper, "We need an eip bootstrapper!")
        leap_assert(self._provider_config, "We need a provider config")

        self._set_eip_status(self.tr("Checking configuration, please wait..."))

        if self._provider_config.provides_eip() and \
                self._enabled_services.count(self.OPENVPN_SERVICE) > 0:
            self._eip_bootstrapper.run_eip_setup_checks(
                self._provider_config,
                download_if_needed=True)
        else:
            if self._enabled_services.count(self.OPENVPN_SERVICE) > 0:
                self._set_eip_status(self.tr("%s does not support EIP") %
                                     (self._provider_config.get_domain(),),
                                     error=True)
            else:
                self._set_eip_status(self.tr("EIP is disabled"))
            self.ui.btnEipStartStop.setEnabled(False)

    def _set_eip_status_icon(self, status):
        """
        Given a status step from the VPN thread, set the icon properly

        :param status: status step
        :type status: str
        """
        selected_pixmap = self.ERROR_ICON
        tray_message = self.tr("Encryption is OFF")
        if status in ("WAIT", "AUTH", "GET_CONFIG",
                      "RECONNECTING", "ASSIGN_IP"):
            selected_pixmap = self.CONNECTING_ICON
            tray_message = self.tr("Turning Encryption ON")
        elif status in ("CONNECTED"):
            tray_message = self.tr("Encryption is ON")
            selected_pixmap = self.CONNECTED_ICON

        self.ui.lblVPNStatusIcon.setPixmap(selected_pixmap)
        self._systray.setIcon(QtGui.QIcon(selected_pixmap))
        self._action_eip_status.setText(tray_message)

    def _update_vpn_state(self, data):
        """
        SLOT
        TRIGGER: self._vpn.state_changed

        Updates the displayed VPN state based on the data provided by
        the VPN thread
        """
        status = data[self._vpn.STATUS_STEP_KEY]
        self._set_eip_status_icon(status)
        if status == "AUTH":
            self._set_eip_status(self.tr("VPN: Authenticating..."))
        elif status == "GET_CONFIG":
            self._set_eip_status(self.tr("VPN: Retrieving configuration..."))
        elif status == "CONNECTED":
            self._set_eip_status(self.tr("VPN: Connected!"))
        elif status == "WAIT":
            self._set_eip_status(self.tr("VPN: Waiting to start..."))
        elif status == "ASSIGN_IP":
            self._set_eip_status(self.tr("VPN: Assigning IP"))
        elif status == "ALREADYRUNNING":
            # Put the following calls in Qt's event queue, otherwise
            # the UI won't update properly
            QtCore.QTimer.singleShot(0, self._stop_eip)
            QtCore.QTimer.singleShot(0, partial(self._set_eip_status,
                                                self.tr("Unable to start VPN, "
                                                        "it's already "
                                                        "running.")))
        else:
            self._set_eip_status(status)

    def _update_vpn_status(self, data):
        """
        SLOT
        TRIGGER: self._vpn.status_changed

        Updates the download/upload labels based on the data provided
        by the VPN thread
        """
        upload = float(data[self._vpn.TUNTAP_WRITE_KEY])
        upload = upload / 1000.0
        upload_str = "%12.2f Kb" % (upload,)
        self.ui.lblUpload.setText(upload_str)
        self._action_eip_write.setText(upload_str)
        download = float(data[self._vpn.TUNTAP_READ_KEY])
        download = download / 1000.0
        download_str = "%12.2f Kb" % (download,)
        self.ui.lblDownload.setText(download_str)
        self._action_eip_read.setText(download_str)

    def _finish_eip_bootstrap(self, data):
        """
        SLOT
        TRIGGER: self._eip_bootstrapper.download_client_certificate

        Starts the VPN thread if the eip configuration is properly
        loaded
        """
        leap_assert(self._eip_config, "We need an eip config!")
        leap_assert(self._provider_config, "We need a provider config!")

        if data[self._eip_bootstrapper.PASSED_KEY] and \
                (self._eip_config.loaded() or
                 self._eip_config.load(os.path.join("leap",
                                                    "providers",
                                                    self._provider_config
                                                    .get_domain(),
                                                    "eip-service.json"))):
                self._start_eip()
        else:
            if data[self._eip_bootstrapper.PASSED_KEY]:
                self._set_eip_status(self.tr("Could not load EIP "
                                             "Configuration"), error=True)
            else:
                self._set_eip_status(data[self._eip_bootstrapper.ERROR_KEY],
                                     error=True)

    def _logout(self):
        """
        SLOT
        TRIGGER: self.ui.action_sign_out.triggered

        Starts the logout sequence
        """
        self._set_eip_status_icon("error")
        self._set_eip_status(self.tr("Signing out..."))
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
        self.ui.action_sign_out.setEnabled(False)
        self.ui.stackedWidget.setCurrentIndex(self.LOGIN_INDEX)
        self.ui.lnPassword.setText("")
        self._login_set_enabled(True)
        self._set_status("")
        self._vpn.set_should_quit()

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
            self._login_set_enabled(True)
            self._set_status(data[self._provider_bootstrapper.ERROR_KEY])

    def _eip_finished(self, exitCode):
        """
        SLOT
        TRIGGERS:
          self._vpn.process_finished

        Triggered when the EIP/VPN process finishes to set the UI
        accordingly
        """
        logger.debug("Finished VPN with exitCode %s" % (exitCode,))
        self._stop_eip()

    def _on_raise_window_event(self, req):
        """
        Callback for the raise window event
        """
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

    def _cleanup_pidfiles(self):
        """
        Removes lockfiles on a clean shutdown.

        Triggered after aboutToQuit signal.
        """
        if IS_WIN:
            lockfile = WindowsLock()
            lockfile.release_lock()

    def _cleanup_and_quit(self):
        """
        Call all the cleanup actions in a serialized way.
        Should be called from the quit function.
        """
        logger.debug('About to quit, doing cleanup...')
        self._vpn.set_should_quit()
        self._vpn.wait()
        self._cleanup_pidfiles()

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

        self.close()

        if self._login_defer:
            self._login_defer.cancel()

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
