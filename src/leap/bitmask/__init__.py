# -*- coding: utf-8 -*-
# __init__.py
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
Init file for leap.bitmask

Initializes version and app info.
"""
import re

from pkg_resources import parse_version

from leap.bitmask.util import first


def _is_release_version(version):
    """
    Helper to determine whether a version is a final release or not.
    The release needs to be of the form: w.x.y.z containing only numbers
    and dots.

    :param version: the version string
    :type version: str
    :returns: if the version is a release version or not.
    :rtype: bool
    """
    parsed_version = parse_version(version)
    not_number = 0
    for x in parsed_version:
        try:
            int(x)
        except:
            not_number += 1

    return not_number == 1


__version__ = "unknown"
IS_RELEASE_VERSION = False

__short_version__ = "unknown"

try:
    from leap.bitmask._version import get_versions
    __version__ = get_versions()['version']
    IS_RELEASE_VERSION = _is_release_version(__version__)
    del get_versions
except ImportError:
    #running on a tree that has not run
    #the setup.py setver
    pass

__appname__ = "unknown"
try:
    from leap._appname import __appname__
except ImportError:
    #running on a tree that has not run
    #the setup.py setver
    pass

__short_version__ = first(re.findall('\d+\.\d+\.\d+', __version__))
__full_version__ = __appname__ + '/' + str(__version__)
