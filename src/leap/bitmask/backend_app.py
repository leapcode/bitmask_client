# -*- coding: utf-8 -*-
# backend_app.py
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
import signal

from leap.bitmask.backend.leapbackend import LeapBackend
from leap.bitmask.util import dict_to_flags


def run_backend(bypass_checks, flags_dict):
    """
    Run the backend for the application.

    :param bypass_checks: whether we should bypass the checks or not
    :type bypass_checks: bool
    :param flags_dict: a dict containing the flag values set on app start.
    :type flags_dict: dict
    """
    # Ensure that the application quits using CTRL-C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    dict_to_flags(flags_dict)

    backend = LeapBackend(bypass_checks=bypass_checks)
    backend.run()
