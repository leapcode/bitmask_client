# -*- coding: utf-8 -*-
# systray.py
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
Custom system tray manager.
"""

from PySide import QtGui

from leap.common.check import leap_assert_type


class SysTray(QtGui.QSystemTrayIcon):
    """
    Custom system tray that allows us to use a more 'intelligent' tooltip.
    """

    def __init__(self, parent=None):
        QtGui.QSystemTrayIcon.__init__(self, parent)
        self._services = {}

    def set_service_tooltip(self, service, tooltip):
        """
        Sets the service tooltip.

        :param service: service name identifier
        :type service: unicode
        :param tooltip: tooltip to display for that service
        :type tooltip: unicode
        """
        leap_assert_type(service, unicode)
        leap_assert_type(tooltip, unicode)

        self._services[service] = tooltip
        tooltip = "\n".join(self._services.values())
        self.setToolTip(tooltip)
