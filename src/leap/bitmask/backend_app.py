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
"""
Start point for the Backend.
"""
import logging
import multiprocessing
import signal

from leap.bitmask.backend.leapbackend import LeapBackend
from leap.bitmask.backend.utils import generate_certificates
from leap.bitmask.logs.utils import create_logger
from leap.bitmask.util import dict_to_flags

logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """
    Signal handler that quits the running app cleanly.

    :param signum: number of the signal received (e.g. SIGINT -> 2)
    :type signum: int
    :param frame: current stack frame
    :type frame: frame or None
    """
    # Note: we don't stop the backend in here since the frontend signal handler
    # will take care of that.
    # In the future we may need to do the stop in here when the frontend and
    # the backend are run separately (without multiprocessing)
    pname = multiprocessing.current_process().name
    logger.debug("{0}: SIGNAL #{1} catched.".format(pname, signum))


def run_backend(bypass_checks=False, flags_dict=None, frontend_pid=None):
    """
    Run the backend for the application.

    :param bypass_checks: whether we should bypass the checks or not
    :type bypass_checks: bool
    :param flags_dict: a dict containing the flag values set on app start.
    :type flags_dict: dict
    """
    # ignore SIGINT since app.py takes care of signaling SIGTERM to us.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal_handler)

    if flags_dict is not None:
        dict_to_flags(flags_dict)

    backend = LeapBackend(bypass_checks=bypass_checks,
                          frontend_pid=frontend_pid)
    backend.run()


if __name__ == '__main__':
    logger = create_logger(debug=True)
    generate_certificates()
    run_backend()
