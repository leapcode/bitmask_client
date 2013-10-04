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
from leap.bitmask.util import get_path_prefix

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
    PROPERPROVIDER_KEY = "ProperProvider"
    REMEMBER_KEY = "RememberUserAndPass"
    DEFAULTPROVIDER_KEY = "DefaultProvider"
    AUTOSTARTEIP_KEY = "AutoStartEIP"
    ALERTMISSING_KEY = "AlertMissingScripts"
    GATEWAY_KEY = "Gateway"
    PINNED_KEY = "Pinned"

    # values
    GATEWAY_AUTOMATIC = "Automatic"

    def __init__(self):
        settings_path = os.path.join(get_path_prefix(),
                                     "leap", self.CONFIG_NAME)

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

    def get_configured_providers(self):
        """
        Returns the configured providers based on the file structure in the
        settings directory.

        :rtype: list of str
        """
        # TODO: check which providers have a valid certificate among
        # other things, not just the directories
        providers = []
        try:
            providers_path = os.path.join(get_path_prefix(),
                                          "leap", "providers")
            providers = os.listdir(providers_path)
        except Exception as e:
            logger.debug("Error listing providers, assume there are none. %r"
                         % (e,))

        return providers

    def is_pinned_provider(self, domain):
        """
        Returns True if the domain 'domain' is pinned with the application.
                False otherwise.

        :param provider: provider domain
        :type provider: str

        :rtype: bool
        """
        leap_assert(len(domain) > 0, "We need a nonempty domain.")
        pinned_key = "{0}/{1}".format(domain, self.PINNED_KEY)
        result = to_bool(self._settings.value(pinned_key, False))

        return result

    def get_selected_gateway(self, provider):
        """
        Returns the configured gateway for the given provider.

        :param provider: provider domain
        :type provider: str

        :rtype: str
        """
        leap_assert(len(provider) > 0, "We need a nonempty provider")
        gateway_key = "{0}/{1}".format(provider, self.GATEWAY_KEY)
        gateway = self._settings.value(gateway_key, self.GATEWAY_AUTOMATIC)

        return gateway

    def set_selected_gateway(self, provider, gateway):
        """
        Saves the configured gateway for the given provider

        :param provider: provider domain
        :type provider: str

        :param gateway: gateway to use as default
        :type gateway: str
        """

        leap_assert(len(provider) > 0, "We need a nonempty provider")
        leap_assert_type(gateway, (str, unicode))

        gateway_key = "{0}/{1}".format(provider, self.GATEWAY_KEY)
        self._settings.setValue(gateway_key, gateway)

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

        key = "{0}/Services".format(provider)
        if not services:
            # if there are no enabled services we don't need that key
            self._settings.remove(key)
        else:
            self._settings.setValue(key, services)

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
        :type provider: str or None
        """
        if provider is None:
            self._settings.remove(self.DEFAULTPROVIDER_KEY)
        else:
            self._settings.setValue(self.DEFAULTPROVIDER_KEY, provider)

    def get_autostart_eip(self):
        """
        Gets whether the app should autostart EIP.

        :rtype: bool
        """
        return to_bool(self._settings.value(self.AUTOSTARTEIP_KEY, False))

    def set_autostart_eip(self, autostart):
        """
        Sets whether the app should autostart EIP.

        :param autostart: True if we should try to autostart EIP.
        :type autostart: bool
        """
        leap_assert_type(autostart, bool)
        self._settings.setValue(self.AUTOSTARTEIP_KEY, autostart)

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
