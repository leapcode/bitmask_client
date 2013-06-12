# -*- coding: utf-8 -*-
# leapsettings.py
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
QSettings abstraction
"""
import os
import logging

from PySide import QtCore

from leap.common.check import leap_assert, leap_assert_type
from leap.common.config.prefixers import get_platform_prefixer

logger = logging.getLogger(__name__)


def to_bool(val):
    """
    Returns the boolean value corresponding to val. Will return False
    in case val is not a string or something that behaves like one.

    :param val: value to cast
    :type val: either bool already or str

    :rtype: bool
    """
    if isinstance(val, bool):
        return val

    bool_val = False
    try:
        bool_val = val.lower() == "true"
    except:
        pass

    return bool_val


class LeapSettings(object):
    """
    Leap client QSettings wrapper
    """

    CONFIG_NAME = "leap.conf"

    # keys
    GEOMETRY_KEY = "Geometry"
    WINDOWSTATE_KEY = "WindowState"
    USER_KEY = "User"
    AUTOLOGIN_KEY = "AutoLogin"
    PROPERPROVIDER_KEY = "ProperProvider"
    REMEMBER_KEY = "RememberUserAndPass"
    DEFAULTPROVIDER_KEY = "DefaultProvider"
    ALERTMISSING_KEY = "AlertMissingScripts"

    def __init__(self, standalone=False):
        """
        Constructor

        :param standalone: parameter used to define the location of
        the config
        :type standalone: bool
        """

        settings_path = os.path.join(get_platform_prefixer()
                                     .get_path_prefix(standalone=standalone),
                                     "leap",
                                     self.CONFIG_NAME)
        self._settings = QtCore.QSettings(settings_path,
                                          QtCore.QSettings.IniFormat)

    def get_geometry(self):
        """
        Returns the saved geometry or None if it wasn't saved

        :rtype: bytearray or None
        """
        return self._settings.value(self.GEOMETRY_KEY, None)

    def set_geometry(self, geometry):
        """
        Saves the geometry to the settings

        :param geometry: bytearray representing the geometry
        :type geometry: bytearray
        """
        leap_assert(geometry, "We need a geometry")
        self._settings.setValue(self.GEOMETRY_KEY, geometry)

    def get_windowstate(self):
        """
        Returns the window state or None if it wasn't saved

        :rtype: bytearray or None
        """
        return self._settings.value(self.WINDOWSTATE_KEY, None)

    def set_windowstate(self, windowstate):
        """
        Saves the window state to the settings

        :param windowstate: bytearray representing the window state
        :type windowstate: bytearray
        """
        leap_assert(windowstate, "We need a window state")
        self._settings.setValue(self.WINDOWSTATE_KEY, windowstate)

    def get_enabled_services(self, provider):
        """
        Returns a list of enabled services for the given provider

        :param provider: provider domain
        :type provider: str

        :rtype: list of str
        """

        leap_assert(len(provider) > 0, "We need a nonempty provider")
        enabled_services = self._settings.value("%s/Services" % (provider,),
                                                [])
        if isinstance(enabled_services, (str, unicode)):
            enabled_services = enabled_services.split(",")

        return enabled_services

    def set_enabled_services(self, provider, services):
        """
        Saves the list of enabled services for the given provider

        :param provider: provider domain
        :type provider: str

        :param services: list of services to save
        :type services: list of str
        """

        leap_assert(len(provider) > 0, "We need a nonempty provider")
        leap_assert_type(services, list)

        self._settings.setValue("%s/Services" % (provider,),
                                services)

    def get_user(self):
        """
        Returns the configured user to remember, None if there isn't one

        :rtype: str or None
        """
        return self._settings.value(self.USER_KEY, None)

    def set_user(self, user):
        """
        Saves the user to remember

        :param user: user name to remember
        :type user: str
        """
        leap_assert(len(user) > 0, "We cannot save an empty user")
        self._settings.setValue(self.USER_KEY, user)

    def get_remember(self):
        """
        Returns the value of the remember selection.

        :rtype: bool
        """
        return to_bool(self._settings.value(self.REMEMBER_KEY, False))

    def set_remember(self, remember):
        """
        Sets wheter the app should remember username and password

        :param remember: True if the app should remember username and
            password, False otherwise
        :rtype: bool
        """
        leap_assert_type(remember, bool)
        self._settings.setValue(self.REMEMBER_KEY, remember)

    def get_autologin(self):
        """
        Returns True if the app should automatically login, False otherwise

        :rtype: bool
        """
        return to_bool(self._settings.value(self.AUTOLOGIN_KEY, False))

    def set_autologin(self, autologin):
        """
        Sets whether the app should automatically login

        :param autologin: True if the app should autologin, False otherwise
        :type autologin: bool
        """
        leap_assert_type(autologin, bool)
        self._settings.setValue(self.AUTOLOGIN_KEY, autologin)

    # TODO: make this scale with multiple providers, we are assuming
    # just one for now
    def get_properprovider(self):
        """
        Returns True if there is a properly configured provider.

        .. note:: this assumes only one provider for now.

        :rtype: bool
        """
        return to_bool(self._settings.value(self.PROPERPROVIDER_KEY, False))

    def set_properprovider(self, properprovider):
        """
        Sets whether the app should automatically login.

        :param properprovider: True if the provider is properly configured,
            False otherwise.
        :type properprovider: bool
        """
        leap_assert_type(properprovider, bool)
        self._settings.setValue(self.PROPERPROVIDER_KEY, properprovider)

    def get_defaultprovider(self):
        """
        Returns the default provider to be used for autostarting EIP

        :rtype: str or None
        """
        return self._settings.value(self.DEFAULTPROVIDER_KEY, None)

    def set_defaultprovider(self, provider):
        """
        Sets the default provider to be used for autostarting EIP

        :param provider: provider to use
        :type provider: str
        """
        leap_assert(len(provider) > 0, "We cannot save an empty provider")
        self._settings.setValue(self.DEFAULTPROVIDER_KEY, provider)

    def get_alert_missing_scripts(self):
        """
        Returns the setting for alerting of missing up/down scripts.

        :rtype: bool
        """
        return to_bool(self._settings.value(self.ALERTMISSING_KEY, True))

    def set_alert_missing_scripts(self, value):
        """
        Sets the setting for alerting of missing up/down scripts.

        :param value: the value to set
        :type value: bool
        """
        leap_assert_type(value, bool)
        self._settings.setValue(self.ALERTMISSING_KEY, value)
