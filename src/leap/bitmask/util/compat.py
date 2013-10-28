# -*- coding: utf-8 -*-
# compat.py
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
Utilities for dealing with compat versions.
"""
from distutils.version import LooseVersion as V

from requests import __version__ as _requests_version


def _requests_has_max_retries():
    """
    Returns True if we can use the max_retries parameter
    """
    return V(_requests_version) > V('1.1.0')

requests_has_max_retries = _requests_has_max_retries()
