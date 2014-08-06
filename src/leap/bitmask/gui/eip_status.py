# -*- coding: utf-8 -*-
# eip_status.py
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
EIP Status Panel widget implementation
"""
import logging

from datetime import datetime
from functools import partial

from PySide import QtCore, QtGui

from leap.bitmask.services import get_service_display_name, EIP_SERVICE
from leap.bitmask.platform_init import IS_LINUX
from leap.bitmask.util.averages import RateMovingAverage
from leap.common.check import leap_assert_type

from ui_eip_status import Ui_EIPStatus

QtDelayedCall = QtCore.QTimer.singleShot
logger = logging.getLogger(__name__)


class EIPStatusWidget(QtGui.QWidget):
    """
    EIP Status widget that displays the current state of the EIP service
    """
    DISPLAY_TRAFFIC_RATES = True
    RATE_STR = "%1.2f KB/s"
    TOTAL_STR = "%1.2f Kb"

    def __init__(self, parent, eip_conductor, leap_signaler):
        """
        :param parent: the parent of the widget.
        :type parent: QObject

        :param eip_conductor: an EIPConductor object.
        :type eip_conductor: EIPConductor
        """
        QtGui.QWidget.__init__(self, parent)

        self._systray = None
        self._eip_status_menu = None

        self.ui = Ui_EIPStatus()
        self.ui.setupUi(self)

        self._leap_signaler = leap_signaler

        self.eip_conductor = eip_conductor
        self.eipconnection = eip_conductor.eip_connection

        # set systray tooltip status
        self._eip_status = ""
        self._service_name = get_service_display_name(EIP_SERVICE)

        self.ui.eip_bandwidth.hide()
        self.hide_fw_down_button()
        self.hide_eip_cancel_button()
        self.ui.btnFwDown.clicked.connect(
            self._on_fw_down_button_clicked)
        self.ui.btnEipCancel.clicked.connect(
            self._on_eip_cancel_button_clicked)

        # Set the EIP status icons
        self.CONNECTING_ICON = None
        self.CONNECTED_ICON = None
        self.ERROR_ICON = None
        self.CONNECTING_ICON_TRAY = None
        self.CONNECTED_ICON_TRAY = None
        self.ERROR_ICON_TRAY = None
        self._set_eip_icons()

        self._set_traffic_rates()
        self._make_status_clickable()

        self._provider = ""
        self.is_restart = False
        self.is_cold_start = True
        self.user_cancelled = False

        self.missing_helpers = False

        # Action for the systray
        self._eip_disabled_action = QtGui.QAction(
            "{0} is {1}".format(self._service_name, self.tr("disabled")), self)

    def connect_backend_signals(self):
        """
        Connect backend signals.
        """
        signaler = self._leap_signaler

        signaler.eip_openvpn_already_running.connect(
            self._on_eip_openvpn_already_running)
        signaler.eip_alien_openvpn_already_running.connect(
            self._on_eip_alien_openvpn_already_running)
        signaler.eip_openvpn_not_found_error.connect(
            self._on_eip_openvpn_not_found_error)
        signaler.eip_vpn_launcher_exception.connect(
            self._on_eip_vpn_launcher_exception)
        signaler.eip_no_polkit_agent_error.connect(
            self._on_eip_no_polkit_agent_error)
        signaler.eip_connection_aborted.connect(
            self._on_eip_connection_aborted)
        signaler.eip_no_pkexec_error.connect(self._on_eip_no_pkexec_error)
        signaler.eip_no_tun_kext_error.connect(self._on_eip_no_tun_kext_error)

        signaler.eip_state_changed.connect(self.update_vpn_state)
        signaler.eip_status_changed.connect(self.update_vpn_status)

        # XXX we cannot connect this signal now because
        # it interferes with the proper notifications during restarts
        # without available network.
        # signaler.eip_network_unreachable.connect(
        #     self._on_eip_network_unreachable)

    def _make_status_clickable(self):
        """
        Makes upload and download figures clickable.
        """
        onclicked = self._on_VPN_status_clicked
        self.ui.btnUpload.clicked.connect(onclicked)
        self.ui.btnDownload.clicked.connect(onclicked)

    @QtCore.Slot()
    def _on_VPN_status_clicked(self):
        """
        TRIGGERS:
            self.ui.btnUpload.clicked
            self.ui.btnDownload.clicked

        Toggles between rate and total throughput display for vpn
        status figures.
        """
        self.DISPLAY_TRAFFIC_RATES = not self.DISPLAY_TRAFFIC_RATES
        self.update_vpn_status()  # refresh

    def _set_traffic_rates(self):
        """
        Initializes up and download rates.
        """
        self._up_rate = RateMovingAverage()
        self._down_rate = RateMovingAverage()

        self.ui.btnUpload.setText(self.RATE_STR % (0,))
        self.ui.btnDownload.setText(self.RATE_STR % (0,))

    def _reset_traffic_rates(self):
        """
        Resets up and download rates, and cleans up the labels.
        """
        self._up_rate.reset()
        self._down_rate.reset()
        self.update_vpn_status()

    def _update_traffic_rates(self, up, down):
        """
        Updates up and download rates.

        :param up: upload total.
        :type up: int
        :param down: download total.
        :type down: int
        """
        ts = datetime.now()
        self._up_rate.append((ts, up))
        self._down_rate.append((ts, down))

    def _get_traffic_rates(self):
        """
        Gets the traffic rates (in KB/s).

        :returns: a tuple with the (up, down) rates
        :rtype: tuple
        """
        up = self._up_rate
        down = self._down_rate

        return (up.get_average(), down.get_average())

    def _get_traffic_totals(self):
        """
        Gets the traffic total throughput (in Kb).

        :returns: a tuple with the (up, down) totals
        :rtype: tuple
        """
        up = self._up_rate
        down = self._down_rate

        return (up.get_total(), down.get_total())

    def _set_eip_icons(self):
        """
        Sets the EIP status icons for the main window and for the tray

        MAC   : dark icons
        LINUX : dark icons in window, light icons in tray
        WIN   : light icons
        """
        EIP_ICONS = EIP_ICONS_TRAY = (
            ":/images/black/32/wait.png",
            ":/images/black/32/on.png",
            ":/images/black/32/off.png")

        if IS_LINUX:
            EIP_ICONS_TRAY = (
                ":/images/white/32/wait.png",
                ":/images/white/32/on.png",
                ":/images/white/32/off.png")

        self.CONNECTING_ICON = QtGui.QPixmap(EIP_ICONS[0])
        self.CONNECTED_ICON = QtGui.QPixmap(EIP_ICONS[1])
        self.ERROR_ICON = QtGui.QPixmap(EIP_ICONS[2])

        self.CONNECTING_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[0])
        self.CONNECTED_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[1])
        self.ERROR_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[2])

    # Systray and actions

    def set_systray(self, systray):
        """
        Sets the systray object to use and adds the service line for EIP.

        :param systray: Systray object
        :type systray: QtGui.QSystemTrayIcon
        """
        leap_assert_type(systray, QtGui.QSystemTrayIcon)
        self._systray = systray
        eip_status = self.tr("{0}: OFF").format(self._service_name)
        self._systray.set_service_tooltip(EIP_SERVICE, eip_status)

    def _update_systray_tooltip(self):
        """
        Updates the system tray tooltip using the eip status.
        """
        if self._systray is not None:
            eip_status = u"{0}: {1}".format(
                self._service_name, self._eip_status)
            self._systray.set_service_tooltip(EIP_SERVICE, eip_status)

    def set_action_eip_startstop(self, action_eip_startstop):
        """
        Set the action_eip_startstop to use.

        :param action_eip_startstop: action_eip_status to be used
        :type action_eip_startstop: QtGui.QAction
        """
        self._action_eip_startstop = action_eip_startstop

    def set_eip_status_menu(self, eip_status_menu):
        """
        Sets the eip_status_menu to use.

        :param eip_status_menu: eip_status_menu to be used
        :type eip_status_menu: QtGui.QMenu
        """
        leap_assert_type(eip_status_menu, QtGui.QMenu)
        self._eip_status_menu = eip_status_menu

    # EIP status ---

    @property
    def eip_button(self):
        return self.ui.btnEipStartStop

    @property
    def eip_label(self):
        return self.ui.lblEIPStatus

    def eip_pre_up(self):
        """
        Triggered when the app activates eip.
        Disables the start/stop button.
        """
        # XXX hack -- we show the cancel button instead.
        self.ui.btnEipStartStop.hide()
        self.set_startstop_enabled(False)
        msg = self.tr("Encrypted Internet is starting")
        self.set_eip_message(msg)

    @QtCore.Slot()
    def disable_eip_start(self):
        """
        Triggered when a default provider_config has not been found.
        Disables the start button and adds instructions to the user.
        """
        # XXX this name is unfortunate. "disable" is also applied to a
        # pushbutton being grayed out.

        logger.debug('Hiding EIP start button')
        # you might be tempted to change this for a .setEnabled(False).
        # it won't work. it's under the claws of the state machine.
        # probably the best thing would be to make a conditional
        # transition there, but that's more involved.
        self.eip_button.hide()
        if self.missing_helpers:
            msg = self.tr(
                "<font color=red>Disabled: missing helper files</font>")
        else:
            msg = self.tr(
                "You must login to use {0}".format(self._service_name))
        self.eip_label.setText(msg)
        self._eip_status_menu.setTitle("{0} is {1}".format(
            self._service_name, self.tr("disabled")))

        # Replace EIP tray menu with an action that displays a "disabled" text
        if self.isVisible():
            menu = self._systray.contextMenu()
            menu.insertAction(
                self._eip_status_menu.menuAction(),
                self._eip_disabled_action)
            self._eip_status_menu.menuAction().setVisible(False)

    @QtCore.Slot()
    def enable_eip_start(self):
        """
        Triggered after a successful login.
        Enables the start button.
        """
        # logger.debug('Showing EIP start button')
        self.eip_button.show()
        self.hide_eip_cancel_button()

        # Restore the eip action menu
        menu = self._systray.contextMenu()
        menu.removeAction(self._eip_disabled_action)
        if self.isVisible():
            self._eip_status_menu.menuAction().setVisible(True)

    def set_eip_message(self, message):
        """
        Set the EIP Widget main message.

        :param message: the message to set in the widget
        :type message: str or unicode
        """
        self.ui.lblEIPMessage.setText(message)
        self.ui.lblEIPMessage.show()

    def set_eip_status(self, status, error=False):
        """
        Set the status label at the VPN stage to status.

        :param status: status message
        :type status: str or unicode
        :param error: if the status is an erroneous one, then set this
                      to True
        :type error: bool
        """
        leap_assert_type(error, bool)
        if error:
            logger.error(status)
            self.hide_eip_cancel_button()
        else:
            logger.debug(status)
        self._eip_status = status
        if error:
            status = "<font color='red'>%s</font>" % (status,)
        self.ui.lblEIPStatus.setText(status)
        self.ui.lblEIPStatus.show()
        self._update_systray_tooltip()

    # XXX disable ---------------------------------
    def set_startstop_enabled(self, value):
        """
        Enable or disable btnEipStartStop and _action_eip_startstop
        based on value

        :param value: True for enabled, False otherwise
        :type value: bool
        """
        # TODO use disable_eip_start instead
        # this should be handled by the state machine
        leap_assert_type(value, bool)
        self.ui.btnEipStartStop.setEnabled(value)
        self._action_eip_startstop.setEnabled(value)

    # XXX disable -----------------------------
    def eip_started(self):
        """
        Sets the state of the widget to how it should look after EIP
        has started
        """
        self.ui.btnEipStartStop.disconnect(self)
        self.ui.btnEipStartStop.clicked.connect(
            self.eipconnection.qtsigs.do_connect_signal)

    def hide_fw_down_button(self):
        """
        Hide firewall-down button.
        """
        self.ui.btnFwDown.hide()

    def show_fw_down_button(self):
        """
        Enable firewall-down button.
        """
        retry_msg = self.tr("Retry")
        self.ui.btnEipStartStop.setText(retry_msg)
        self._action_eip_startstop.setText(retry_msg)
        self.ui.btnFwDown.show()

    def _on_fw_down_button_clicked(self):
        """
        Raise a signal for tearing down the firewall, and hide the button
        afterwards.
        """
        self.eip_conductor._backend.tear_fw_down()
        QtDelayedCall(50, self.hide_fw_down_button)

        # XXX do actual check
        msg = "Traffic is being routed in the clear."
        self.ui.btnEipStartStop.setText(self.tr("Turn ON"))
        self.set_eip_message(msg)
        self.set_eip_status("")

    def hide_eip_cancel_button(self):
        """
        Hide eip-cancel button.
        """
        self.ui.btnEipCancel.hide()

    def show_eip_cancel_button(self):
        """
        Show eip-cancel button.
        """
        self.ui.btnEipCancel.show()
        self.user_cancelled = False

    def _on_eip_cancel_button_clicked(self):
        """
        Call backend to kill the openvpn process with root privileges.
        """
        self.eip_conductor.cancelled = True
        self.eip_conductor._backend.bitmask_root_vpn_down()
        self.user_cancelled = True
        self.hide_eip_cancel_button()

    @QtCore.Slot(dict)
    def eip_stopped(self, restart=False, failed=False):
        """
        TRIGGERS:
            EIPConductor.qtsigs.disconnected_signal

        Sets the state of the widget to how it should look after EIP
        has stopped
        """
        self.set_country_code("")
        self._reset_traffic_rates()
        self.ui.eip_bandwidth.hide()

        if self.user_cancelled:
            self.eip_conductor._backend.tear_fw_down()
            self.eip_button.show()
            failed = False

        # This is assuming the firewall works correctly, but we should test fw
        # status positively.
        # Or better call it from the conductor...

        clear_traffic = self.tr("Traffic is being routed in the clear.")
        unreachable_net = self.tr("Network is unreachable.")
        failed_msg = self.tr("Error connecting")

        if restart:
            msg = unreachable_net
        elif failed:
            msg = failed_msg
        else:
            msg = clear_traffic

        self.set_eip_message(msg)
        self.ui.lblEIPStatus.show()
        self.show()

    def eip_failed_to_connect(self):
        """
        Update EIP messages with error during (re)connection.
        """
        msg = self.tr("Error connecting.")
        self.ui.lblEIPMessage.setText(msg)
        self.ui.lblEIPStatus.show()
        self.set_eip_status(self.tr("Bitmask is blocking "
                                    "unencrypted traffic."))
        self.show_fw_down_button()

    @QtCore.Slot(dict)
    def update_vpn_status(self, data=None):
        """
        TRIGGERS:
            Signaler.eip_status_changed

        Updates the download/upload labels based on the data provided by the
        VPN thread.
        If data is None, we just will refresh the display based on the previous
        data.

        :param data: a tuple with download/upload totals (download, upload).
        :type data: tuple
        """
        if data is not None:
            try:
                upload, download = map(float, data)
                self._update_traffic_rates(upload, download)
            except Exception:
                # discard invalid data
                return

        if self.DISPLAY_TRAFFIC_RATES:
            uprate, downrate = self._get_traffic_rates()
            upload_str = self.RATE_STR % (uprate,)
            download_str = self.RATE_STR % (downrate,)

        else:  # display total throughput
            uptotal, downtotal = self._get_traffic_totals()
            upload_str = self.TOTAL_STR % (uptotal,)
            download_str = self.TOTAL_STR % (downtotal,)

        self.ui.btnUpload.setText(upload_str)
        self.ui.btnDownload.setText(download_str)

    @QtCore.Slot(dict)
    def update_vpn_state(self, vpn_state):
        """
        TRIGGERS:
            Signaler.eip_state_changed

        Updates the displayed VPN state based on the data provided by
        the VPN thread.

        :param vpn_state: the state of the VPN
        :type vpn_state: dict

        Emits:
            If the vpn_state is connected, we emit EIPConnection.qtsigs.
            connected_signal
        """
        self.set_eip_status_icon(vpn_state)
        if vpn_state == "CONNECTED":
            self.ui.eip_bandwidth.show()
            self.ui.lblEIPStatus.hide()

            # XXX should be handled by the state machine too.
            # --- is this currently being sent?
            self.eipconnection.qtsigs.connected_signal.emit()
            self._on_eip_connected()
            self.is_cold_start = False
            self.hide_eip_cancel_button()
            self.eip_button.show()

        # XXX should lookup vpn_state map in EIPConnection
        elif vpn_state == "AUTH":
            self.set_eip_status(self.tr("Authenticating..."))

            # XXX should be handled by a future state machine instead.
            self.show_eip_cancel_button()
            # we wipe up any previous error info in the EIP message
            # when we detect vpn authentication is happening
            msg = self.tr("Encrypted Internet is starting")
            self.set_eip_message(msg)
        elif vpn_state == "GET_CONFIG":
            self.set_eip_status(self.tr("Retrieving configuration..."))
        elif vpn_state == "WAIT":
            self.set_eip_status(self.tr("Waiting to start..."))
        elif vpn_state == "ASSIGN_IP":
            self.set_eip_status(self.tr("Assigning IP"))
        elif vpn_state == "RECONNECTING":
            self.set_eip_status(self.tr("Reconnecting..."))
        elif vpn_state == "ALREADYRUNNING":
            # Put the following calls in Qt's event queue, otherwise
            # the UI won't update properly
            # self.send_disconnect_signal()
            QtDelayedCall(
                0, self.eipconnection.qtsigns.do_disconnect_signal.emit)
            msg = self.tr("Unable to start VPN, it's already running.")
            QtDelayedCall(0, partial(self.set_eip_status, msg))
        else:
            self.set_eip_status(vpn_state)

    def set_eip_icon(self, icon):
        """
        Sets the icon to display for EIP

        :param icon: icon to display
        :type icon: QPixmap
        """
        self.ui.lblVPNStatusIcon.setPixmap(icon)

    def set_eip_status_icon(self, status):
        """
        Given a status step from the VPN thread, set the icon properly

        :param status: status step
        :type status: str
        """
        selected_pixmap = self.ERROR_ICON
        selected_pixmap_tray = self.ERROR_ICON_TRAY
        tray_message = self.tr("{0}: OFF".format(self._service_name))
        if status in ("WAIT", "AUTH", "GET_CONFIG",
                      "RECONNECTING", "ASSIGN_IP"):
            selected_pixmap = self.CONNECTING_ICON
            selected_pixmap_tray = self.CONNECTING_ICON_TRAY
            tray_message = self.tr("{0}: Starting...").format(
                self._service_name)
        elif status in ("CONNECTED"):
            tray_message = self.tr("{0}: ON".format(self._service_name))
            selected_pixmap = self.CONNECTED_ICON
            selected_pixmap_tray = self.CONNECTED_ICON_TRAY
            self._eip_status = 'ON'
            self._update_systray_tooltip()

        self.set_eip_icon(selected_pixmap)
        self._systray.setIcon(QtGui.QIcon(selected_pixmap_tray))
        self._eip_status_menu.setTitle(tray_message)

    def set_provider(self, provider, country_code):
        """
        Set the provider used right now, name and flag (if available).

        :param provider: the provider in use.
        :type provider: str
        :param country_code: the country code of the gateway in use.
        :type country_code: str
        """
        self._provider = provider

        self.ui.lblEIPMessage.setText(
            self.tr("Routing traffic through: <b>{0}</b>").format(
                provider))

        if country_code is not None:
            self.set_country_code(country_code)

    def set_country_code(self, code):
        """
        Set the pixmap of the given country code

        :param code: the country code
        :type code: str
        """
        if code is not None and len(code) == 2:
            img = ":/images/countries/%s.png" % (code.lower(),)
        else:
            img = None
        cc = self.ui.lblGatewayCountryCode
        cc.setPixmap(QtGui.QPixmap(img))
        cc.setToolTip(code)

    def aborted(self):
        """
        Notify the state machine that EIP was aborted for some reason.
        """
        # signal connection_aborted to state machine:
        qtsigs = self.eipconnection.qtsigs
        qtsigs.connection_aborted_signal.emit()

    #
    # Slots for signals
    #

    @QtCore.Slot()
    def _on_eip_connection_aborted(self):
        """
        TRIGGERS:
            Signaler.eip_connection_aborted
        """
        # TODO this name is very misleading, since there's a generic signal
        # that's called connection_aborted / connection_died...
        # should rename to something more specific about missing config.
        logger.error("Tried to start EIP but cannot find any "
                     "available provider!")

        eip_status_label = self.tr("Could not load {0} configuration.")
        eip_status_label = eip_status_label.format(
            self.eip_conductor.eip_name)
        self.set_eip_status(eip_status_label, error=True)

        self.aborted()

    def _on_eip_openvpn_already_running(self):
        self.set_eip_status(
            self.tr("Another openvpn instance is already running, and "
                    "could not be stopped."),
            error=True)
        self.set_eipstatus_off()

        self.aborted()

    def _on_eip_alien_openvpn_already_running(self):
        self.set_eip_status(
            self.tr("Another openvpn instance is already running, and "
                    "could not be stopped because it was not launched by "
                    "Bitmask. Please stop it and try again."),
            error=True)
        self.set_eipstatus_off()

        self.aborted()

    def _on_eip_openvpn_not_found_error(self):
        self.set_eip_status(
            self.tr("We could not find openvpn binary."),
            error=True)
        self.set_eipstatus_off()

        self.aborted()

    def _on_eip_vpn_launcher_exception(self):
        # XXX We should implement again translatable exceptions so
        # we can pass a translatable string to the panel (usermessage attr)
        # FIXME this logic should belong to the backend, not to this
        # widget.
        self.set_eipstatus_off()

        st = self.tr("VPN Launcher error. See the logs for more info.")
        self.set_eip_status(st, error=True)

        msg = self.tr("Encrypted Internet failed to start")
        self.set_eip_message(msg)
        self.show_fw_down_button()

        self.aborted()

    def _on_eip_no_polkit_agent_error(self):
        self.set_eip_status(
            # XXX this should change to polkit-kde where
            # applicable.
            self.tr("We could not find any authentication agent in your "
                    "system.<br/>Make sure you have"
                    "<b>polkit-gnome-authentication-agent-1</b> running and"
                    "try again."),
            error=True)
        self.set_eipstatus_off()

        self.aborted()

    def _on_eip_no_pkexec_error(self):
        self.set_eip_status(
            self.tr("We could not find <b>pkexec</b> in your system."),
            error=True)
        self.set_eipstatus_off()

        self.aborted()

    def _on_eip_no_tun_kext_error(self):
        self.set_eip_status(
            self.tr("{0} cannot be started because the tuntap extension is "
                    "not installed properly in your "
                    "system.").format(self.eip_conductor.eip_name))
        self.set_eipstatus_off()

        self.aborted()

    def _on_eip_connected(self):
        """
        Reconnect the disconnecting signal when we are just connected,
        so that we restore the disconnecting -> stop behaviour.
        """
        self.eip_conductor.reconnect_stop_signal()

    @QtCore.Slot()
    def _on_eip_network_unreachable(self):
        """
        TRIGGERS:
            self._eip_connection.qtsigs.network_unreachable

        Displays a "network unreachable" error in the EIP status panel.
        """
        self.set_eip_status(self.tr("Network is unreachable"),
                            error=True)
        self.set_eip_status_icon("error")

    def set_eipstatus_off(self, error=True):
        # XXX this should be handled by the state machine.
        """
        Sets eip status to off
        """
        self.set_eip_status("", error=error)
        self.set_eip_status_icon("error")

import eipstatus_rc
assert(eipstatus_rc)
