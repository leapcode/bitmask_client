# -*- coding: utf-8 -*-
# statuspanel.py
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
Status Panel widget implementation
"""
import logging

from datetime import datetime
from functools import partial
from PySide import QtCore, QtGui

from ui_statuspanel import Ui_StatusPanel

from leap.common.check import leap_assert_type
from leap.services.eip.vpnprocess import VPNManager
from leap.platform_init import IS_WIN, IS_LINUX
from leap.util import first

logger = logging.getLogger(__name__)


class RateMovingAverage(object):
    """
    Moving window average for calculating
    upload and download rates.
    """
    SAMPLE_SIZE = 5

    def __init__(self):
        """
        Initializes an empty array of fixed size
        """
        self.reset()

    def reset(self):
        self._data = [None for i in xrange(self.SAMPLE_SIZE)]

    def append(self, x):
        """
        Appends a new data point to the collection.

        :param x: A tuple containing timestamp and traffic points
                  in the form (timestamp, traffic)
        :type x: tuple
        """
        self._data.pop(0)
        self._data.append(x)

    def get(self):
        """
        Gets the collection.
        """
        return self._data

    def get_average(self):
        """
        Gets the moving average.
        """
        data = filter(None, self.get())
        traff = [traffic for (ts, traffic) in data]
        times = [ts for (ts, traffic) in data]

        deltatraffic = traff[-1] - first(traff)
        deltat = (times[-1] - first(times)).seconds

        try:
            rate = float(deltatraffic) / float(deltat) / 1024
        except ZeroDivisionError:
            rate = 0
        return rate


class StatusPanelWidget(QtGui.QWidget):
    """
    Status widget that displays the current state of the LEAP services
    """

    start_eip = QtCore.Signal()
    stop_eip = QtCore.Signal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self._systray = None
        self._action_eip_status = None

        self.ui = Ui_StatusPanel()
        self.ui.setupUi(self)

        self.ui.btnEipStartStop.setEnabled(False)
        self.ui.btnEipStartStop.clicked.connect(
            self.start_eip)

        self.hide_status_box()

        # Set the EIP status icons
        self.CONNECTING_ICON = None
        self.CONNECTED_ICON = None
        self.ERROR_ICON = None
        self.CONNECTING_ICON_TRAY = None
        self.CONNECTED_ICON_TRAY = None
        self.ERROR_ICON_TRAY = None
        self._set_eip_icons()

        self._set_traffic_rates()

    def _set_traffic_rates(self):
        """
        Initializes up and download rates.
        """
        self._up_rate = RateMovingAverage()
        self._down_rate = RateMovingAverage()

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
        Gets the traffic rates.

        :returns: a tuple with the (up, down) rates
        :rtype: tuple
        """
        up = self._up_rate
        down = self._down_rate

        return (up.get_average(), down.get_average())

    def _set_eip_icons(self):
        """
        Sets the EIP status icons for the main window and for the tray

        MAC   : dark icons
        LINUX : dark icons in window, light icons in tray
        WIN   : light icons
        """
        EIP_ICONS = EIP_ICONS_TRAY = (
            ":/images/conn_connecting-light.png",
            ":/images/conn_connected-light.png",
            ":/images/conn_error-light.png")

        if IS_LINUX:
            EIP_ICONS_TRAY = (
                ":/images/conn_connecting.png",
                ":/images/conn_connected.png",
                ":/images/conn_error.png")
        elif IS_WIN:
            EIP_ICONS = EIP_ICONS_TRAY = (
                ":/images/conn_connecting.png",
                ":/images/conn_connected.png",
                ":/images/conn_error.png")

        self.CONNECTING_ICON = QtGui.QPixmap(EIP_ICONS[0])
        self.CONNECTED_ICON = QtGui.QPixmap(EIP_ICONS[1])
        self.ERROR_ICON = QtGui.QPixmap(EIP_ICONS[2])

        self.CONNECTING_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[0])
        self.CONNECTED_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[1])
        self.ERROR_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[2])

    def set_systray(self, systray):
        """
        Sets the systray object to use.

        :param systray: Systray object
        :type systray: QtGui.QSystemTrayIcon
        """
        leap_assert_type(systray, QtGui.QSystemTrayIcon)
        self._systray = systray

    def set_action_eip_startstop(self, action_eip_startstop):
        """
        Sets the action_eip_startstop to use.

        :param action_eip_startstop: action_eip_status to be used
        :type action_eip_startstop: QtGui.QAction
        """
        self._action_eip_startstop = action_eip_startstop

    def set_action_eip_status(self, action_eip_status):
        """
        Sets the action_eip_status to use.

        :param action_eip_status: action_eip_status to be used
        :type action_eip_status: QtGui.QAction
        """
        leap_assert_type(action_eip_status, QtGui.QAction)
        self._action_eip_status = action_eip_status

    def set_global_status(self, status, error=False):
        """
        Sets the global status label.

        :param status: status message
        :type status: str or unicode
        :param error: if the status is an erroneous one, then set this
                      to True
        :type error: bool
        """
        leap_assert_type(error, bool)
        if error:
            status = "<font color='red'><b>%s</b></font>" % (status,)
        self.ui.lblGlobalStatus.setText(status)
        self.ui.globalStatusBox.show()

    def hide_status_box(self):
        """
        Hide global status box.
        """
        self.ui.globalStatusBox.hide()

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

        self._systray.setToolTip(status)
        if error:
            status = "<font color='red'>%s</font>" % (status,)
        self.ui.lblEIPStatus.setText(status)

    def set_startstop_enabled(self, value):
        """
        Enable or disable btnEipStartStop and _action_eip_startstop
        based on value

        :param value: True for enabled, False otherwise
        :type value: bool
        """
        leap_assert_type(value, bool)
        self.ui.btnEipStartStop.setEnabled(value)
        self._action_eip_startstop.setEnabled(value)

    def eip_pre_up(self):
        """
        Triggered when the app activates eip.
        Hides the status box and disables the start/stop button.
        """
        self.hide_status_box()
        self.set_startstop_enabled(False)

    def eip_started(self):
        """
        Sets the state of the widget to how it should look after EIP
        has started
        """
        self.ui.btnEipStartStop.setText(self.tr("Turn OFF"))
        self.ui.btnEipStartStop.disconnect(self)
        self.ui.btnEipStartStop.clicked.connect(
            self.stop_eip)

    def eip_stopped(self):
        """
        Sets the state of the widget to how it should look after EIP
        has stopped
        """
        self.ui.btnEipStartStop.setText(self.tr("Turn ON"))
        self.ui.btnEipStartStop.disconnect(self)
        self.ui.btnEipStartStop.clicked.connect(
            self.start_eip)

    def set_icon(self, icon):
        """
        Sets the icon to display for EIP

        :param icon: icon to display
        :type icon: QPixmap
        """
        self.ui.lblVPNStatusIcon.setPixmap(icon)

    def update_vpn_status(self, data):
        """
        SLOT
        TRIGGER: VPN.status_changed

        Updates the download/upload labels based on the data provided
        by the VPN thread
        """
        upload = float(data[VPNManager.TUNTAP_WRITE_KEY] or "0")
        download = float(data[VPNManager.TUNTAP_READ_KEY] or "0")
        self._update_traffic_rates(upload, download)
        uprate, downrate = self._get_traffic_rates()

        upload_str = "%14.2f KB/s" % (uprate,)
        self.ui.lblUpload.setText(upload_str)

        download_str = "%14.2f KB/s" % (downrate,)
        self.ui.lblDownload.setText(download_str)

    def update_vpn_state(self, data):
        """
        SLOT
        TRIGGER: VPN.state_changed

        Updates the displayed VPN state based on the data provided by
        the VPN thread
        """
        status = data[VPNManager.STATUS_STEP_KEY]
        self.set_eip_status_icon(status)
        if status == "CONNECTED":
            self.set_eip_status(self.tr("ON"))
            # Only now we can properly enable the button.
            self.set_startstop_enabled(True)
        elif status == "AUTH":
            self.set_eip_status(self.tr("Authenticating..."))
        elif status == "GET_CONFIG":
            self.set_eip_status(self.tr("Retrieving configuration..."))
        elif status == "WAIT":
            self.set_eip_status(self.tr("Waiting to start..."))
        elif status == "ASSIGN_IP":
            self.set_eip_status(self.tr("Assigning IP"))
        elif status == "ALREADYRUNNING":
            # Put the following calls in Qt's event queue, otherwise
            # the UI won't update properly
            QtCore.QTimer.singleShot(0, self.stop_eip)
            QtCore.QTimer.singleShot(0, partial(self.set_global_status,
                                                self.tr("Unable to start VPN, "
                                                        "it's already "
                                                        "running.")))
        else:
            self.set_eip_status(status)

    def set_eip_status_icon(self, status):
        """
        Given a status step from the VPN thread, set the icon properly

        :param status: status step
        :type status: str
        """
        selected_pixmap = self.ERROR_ICON
        selected_pixmap_tray = self.ERROR_ICON_TRAY
        tray_message = self.tr("Encryption is OFF")
        if status in ("WAIT", "AUTH", "GET_CONFIG",
                      "RECONNECTING", "ASSIGN_IP"):
            selected_pixmap = self.CONNECTING_ICON
            selected_pixmap_tray = self.CONNECTING_ICON_TRAY
            tray_message = self.tr("Turning ON")
        elif status in ("CONNECTED"):
            tray_message = self.tr("Encryption is ON")
            selected_pixmap = self.CONNECTED_ICON
            selected_pixmap_tray = self.CONNECTED_ICON_TRAY

        self.set_icon(selected_pixmap)
        self._systray.setIcon(QtGui.QIcon(selected_pixmap_tray))
        self._action_eip_status.setText(tray_message)

    def set_provider(self, provider):
        self.ui.lblProvider.setText(provider)
