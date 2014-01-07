# -*- coding: utf-8 -*-
# __init.py
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
Module initialization for leap.bitmask.provider
"""
import os

from distutils.version import LooseVersion

from leap.bitmask import __version__ as BITMASK_VERSION
from leap.common.check import leap_assert


def get_provider_path(domain):
    """
    Returns relative path for provider config.

    :param domain: the domain to which this providerconfig belongs to.
    :type domain: str
    :returns: the path
    :rtype: str
    """
    leap_assert(domain is not None, "get_provider_path: We need a domain")
    return os.path.join("leap", "providers", domain, "provider.json")


class SupportedClient(object):
    """
    Class responsible of checking for client compatibility.
    """

    @classmethod
    def supports(self, minimum_version):
        """
        :param minimum_version: the version number of the client that
                                we need to check.
        :type minimum_version: str

        :returns: True if that version is supported or False otherwise.
        :return type: bool
        """
        return LooseVersion(minimum_version) <= LooseVersion(BITMASK_VERSION)
