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
import multiprocessing
import signal

from twisted.internet import reactor

from leap.common.events import server as event_server

from leap.bitmask.backend.leapbackend import LeapBackend
from leap.bitmask.backend.utils import generate_zmq_certificates
from leap.bitmask.config import flags
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.util import dict_to_flags


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
    print "{0}: SIGNAL #{1} catched.".format(pname, signum)


def run_backend(bypass_checks=False, flags_dict=None, frontend_pid=None):
    """
    Run the backend for the application.
    This is called from the main app.py entrypoint, and is run in a child
    subprocess.

    :param bypass_checks: whether we should bypass the checks or not
    :type bypass_checks: bool
    :param flags_dict: a dict containing the flag values set on app start.
    :type flags_dict: dict
    """
    # In the backend, we want all the components to log into logbook
    # that is: logging handlers and twisted logs
    from logbook.compat import redirect_logging
    from twisted.python.log import PythonLoggingObserver
    redirect_logging()
    observer = PythonLoggingObserver()
    observer.start()

    # NOTE: this needs to be used here, within the call since this function is
    # executed in a different process and it seems that the process/thread
    # identification isn't working 100%
    logger = get_logger()  # noqa

    if flags_dict is not None:
        dict_to_flags(flags_dict)

    # The backend is the one who always creates the certificates. Either if it
    # is run separately or in a process in the same app as the frontend.
    if flags.ZMQ_HAS_CURVE:
        generate_zmq_certificates()

    # ignore SIGINT since app.py takes care of signaling SIGTERM to us.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal_handler)

    reactor.callWhenRunning(start_events_and_updater, logger)

    backend = LeapBackend(bypass_checks=bypass_checks,
                          frontend_pid=frontend_pid)
    backend.run()


def start_events_and_updater(logger):
    event_server.ensure_server()

    if flags.STANDALONE:
        try:
            from leap.bitmask.updater import Updater
            updater = Updater()
            updater.start()
        except ImportError:
            logger.error("Updates are not enabled in this distribution.")


if __name__ == '__main__':
    run_backend()
