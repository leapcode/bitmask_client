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
Provider utilities.
"""
import os

from pkg_resources import parse_version

from leap.bitmask import __short_version__ as BITMASK_VERSION
from leap.common.check import leap_assert


# The currently supported API versions by the client.
SUPPORTED_APIS = ["1"]


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


def supports_api(api_version):
    """
    :param api_version: the version number of the api that we need to check
    :type api_version: str

    :returns: if that version is supported or not.
    :return type: bool
    """
    return api_version in SUPPORTED_APIS


def supports_client(minimum_version):
    """
    :param minimum_version: the version number of the client that
                            we need to check.
    :type minimum_version: str

    :returns: True if that version is supported or False otherwise.
    :return type: bool
    """
    return parse_version(minimum_version) <= parse_version(BITMASK_VERSION)
