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
from ._version import get_versions

# HACK: This is a hack so that py2app copies _scrypt.so to the right
# place, it can't be technically imported, but that doesn't matter
# because the import is never executed
if False:
    import _scrypt  # noqa - skip 'not used' warning


def _is_release_version(version_str):
    """
    Helper to determine whether a version is a final release or not.
    The release needs to be of the form: w.x.y.z containing only numbers
    and dots.

    :param version: the version string
    :type version: str
    :returns: if the version is a release version or not.
    :rtype: bool
    """
    parts = __version__.split('.')
    try:
        patch = parts[2]
    except IndexError:
        return False
    return patch.isdigit()


__version__ = get_versions()['version']
__version_hash__ = get_versions()['full-revisionid']
IS_RELEASE_VERSION = _is_release_version(__version__)
del get_versions
