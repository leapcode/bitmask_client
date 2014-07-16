# -*- coding: utf-8 -*-
# settings.py
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
Backend settings
"""
import ConfigParser
import logging
import os

from leap.bitmask.util import get_path_prefix
from leap.common.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)

# We need this one available for the default decorator
GATEWAY_AUTOMATIC = "Automatic"
GENERAL_SECTION = "General"


class Settings(object):
    """
    Leap backend settings hanler.
    """
    CONFIG_NAME = "leap-backend.conf"

    # keys
    GATEWAY_KEY = "Gateway"

    def __init__(self):
        """
        Create the ConfigParser object and read it.
        """
        self._settings_path = os.path.join(get_path_prefix(),
                                           "leap", self.CONFIG_NAME)

        self._settings = ConfigParser.ConfigParser()
        self._settings.read(self._settings_path)

        self._add_section(GENERAL_SECTION)

    def _add_section(self, section):
        """
        Add `section` to the config file and don't fail if already exists.

        :param section: the section to add.
        :type section: str
        """
        self._settings.read(self._settings_path)
        try:
            self._settings.add_section(section)
        except ConfigParser.DuplicateSectionError:
            pass

    def _save(self):
        """
        Save the current state to the config file.
        """
        with open(self._settings_path, 'wb') as f:
            self._settings.write(f)

    def _get_value(self, section, key, default):
        """
        Return the value for the fiven `key` in `section`.
        If there's no such section/key, `default` is returned.

        :param section: the section to get the value from.
        :type section: str
        :param key: the key which value we want to get.
        :type key: str
        :param default: the value to return if there is no section/key.
        :type default: object

        :rtype: object
        """
        try:
            return self._settings.get(section, key)
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return default

    def get_selected_gateway(self, provider):
        """
        Return the configured gateway for the given `provider`.

        :param provider: provider domain
        :type provider: str

        :rtype: str
        """
        leap_assert(len(provider) > 0, "We need a nonempty provider")
        return self._get_value(provider, self.GATEWAY_KEY, GATEWAY_AUTOMATIC)

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

        self._add_section(provider)

        self._settings.set(provider, self.GATEWAY_KEY, gateway)
        self._save()

    def get_uuid(self, username):
        """
        Gets the uuid for a given username.

        :param username: the full user identifier in the form user@provider
        :type username: basestring
        """
        leap_assert("@" in username,
                    "Expected username in the form user@provider")
        user, provider = username.split('@')

        return self._get_value(provider, username, "")

    def set_uuid(self, username, value):
        """
        Sets the uuid for a given username.

        :param username: the full user identifier in the form user@provider
        :type username: str or unicode
        :param value: the uuid to save or None to remove it
        :type value: str or unicode or None
        """
        leap_assert("@" in username,
                    "Expected username in the form user@provider")
        user, provider = username.split('@')

        if value is None:
            self._settings.remove_option(provider, username)
        else:
            leap_assert(len(value) > 0, "We cannot save an empty uuid")
            self._add_section(provider)
            self._settings.set(provider, username, value)

        self._save()
