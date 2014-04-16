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

from leap.bitmask.services.eip.connection import EIPConnection
from leap.bitmask.services import get_service_display_name, EIP_SERVICE
from leap.bitmask.platform_init import IS_LINUX
from leap.bitmask.util.averages import RateMovingAverage
from leap.common.check import leap_assert_type

from ui_eip_status import Ui_EIPStatus

logger = logging.getLogger(__name__)


class EIPStatusWidget(QtGui.QWidget):
    """
    EIP Status widget that displays the current state of the EIP service
    """
    DISPLAY_TRAFFIC_RATES = True
    RATE_STR = "%1.2f KB/s"
    TOTAL_STR = "%1.2f Kb"

    eip_connection_connected = QtCore.Signal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self._systray = None
        self._eip_status_menu = None

        self.ui = Ui_EIPStatus()
        self.ui.setupUi(self)

        self.eipconnection = EIPConnection()

        # set systray tooltip status
        self._eip_status = ""
        self._service_name = get_service_display_name(EIP_SERVICE)

        self.ui.eip_bandwidth.hide()

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

        # Action for the systray
        self._eip_disabled_action = QtGui.QAction(
            "{0} is {1}".format(self._service_name, self.tr("disabled")), self)

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
        TRIGGER: self.ui.btnUpload.clicked
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
        Sets the action_eip_startstop to use.

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
        Hides the status box and disables the start/stop button.
        """
        self.set_startstop_enabled(False)

    @QtCore.Slot()
    def disable_eip_start(self):
        """
        Triggered when a default provider_config has not been found.
        Disables the start button and adds instructions to the user.
        """
        #logger.debug('Hiding EIP start button')
        # you might be tempted to change this for a .setEnabled(False).
        # it won't work. it's under the claws of the state machine.
        # probably the best thing would be to make a conditional
        # transition there, but that's more involved.
        self.eip_button.hide()
        msg = self.tr("You must login to use {0}".format(self._service_name))
        self.eip_label.setText(msg)
        self._eip_status_menu.setTitle("{0} is {1}".format(
            self._service_name, self.tr("disabled")))

        # Replace EIP tray menu with an action that displays a "disabled" text
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
        #logger.debug('Showing EIP start button')
        self.eip_button.show()

        # Restore the eip action menu
        menu = self._systray.contextMenu()
        menu.removeAction(self._eip_disabled_action)
        self._eip_status_menu.menuAction().setVisible(True)

    # XXX disable (later) --------------------------
    def set_eip_status(self, status, error=False):
        """
        Sets the status label at the VPN stage to status

        :param status: status message
        :type status: str or unicode
        :param error: if the status is an erroneous one, then set this
                      to True
        :type error: bool
        """
        leap_assert_type(error, bool)
        if error:
            logger.error(status)
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
        self.ui.btnEipStartStop.setText(self.tr("Turn OFF"))
        self.ui.btnEipStartStop.disconnect(self)
        self.ui.btnEipStartStop.clicked.connect(
            self.eipconnection.qtsigs.do_connect_signal)

    # XXX disable -----------------------------
    def eip_stopped(self):
        """
        Sets the state of the widget to how it should look after EIP
        has stopped
        """
        # XXX should connect this to EIPConnection.disconnected_signal
        self._reset_traffic_rates()
        # XXX disable -----------------------------
        self.ui.btnEipStartStop.setText(self.tr("Turn ON"))
        self.ui.btnEipStartStop.disconnect(self)
        self.ui.btnEipStartStop.clicked.connect(
            self.eipconnection.qtsigs.do_disconnect_signal)

        self.ui.eip_bandwidth.hide()
        self.ui.lblEIPMessage.setText(
            self.tr("Traffic is being routed in the clear"))
        self.ui.lblEIPStatus.show()

    @QtCore.Slot(dict)
    def update_vpn_status(self, data=None):
        """
            TRIGGER: Signaler.eip_status_changed

        Updates the download/upload labels based on the data provided by the
        VPN thread.
        If data is None, we just will refresh the display based on the previous
        data.

        :param data: a dictionary with the tcp/udp write and read totals.
        :type data: dict
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
            TRIGGER: Signaler.eip_state_changed

        Updates the displayed VPN state based on the data provided by
        the VPN thread.

        Emits:
            If the vpn_state is connected, we emit EIPConnection.qtsigs.
            connected_signal
        """
        self.set_eip_status_icon(vpn_state)
        if vpn_state == "CONNECTED":
            self.ui.eip_bandwidth.show()
            self.ui.lblEIPStatus.hide()

            # XXX should be handled by the state machine too.
            self.eip_connection_connected.emit()

        # XXX should lookup vpn_state map in EIPConnection
        elif vpn_state == "AUTH":
            self.set_eip_status(self.tr("Authenticating..."))
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
            QtCore.QTimer.singleShot(
                0, self.eipconnection.qtsigs.do_disconnect_signal)
            msg = self.tr("Unable to start VPN, it's already running.")
            QtCore.QTimer.singleShot(0, partial(self.set_eip_status, msg))
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

    def set_provider(self, provider):
        self._provider = provider
        self.ui.lblEIPMessage.setText(
            self.tr("Route traffic through: {0}").format(self._provider))
