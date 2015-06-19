# -*- coding: utf-8 -*-
# utils.py
# Copyright (C) 2013, 2014, 2015 LEAP
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
Logs utilities
"""

import os
import sys

from leap.bitmask.config import flags
from leap.bitmask.logs import LOG_FORMAT
from leap.bitmask.logs.log_silencer import SelectiveSilencerFilter
from leap.bitmask.logs.safezmqhandler import SafeZMQHandler
# from leap.bitmask.logs.streamtologger import StreamToLogger
from leap.bitmask.platform_init import IS_WIN
from leap.bitmask.util import get_path_prefix

import logbook
from logbook.more import ColorizedStderrHandler


BITMASK_LOG_FILE = os.path.join(get_path_prefix(), "leap", 'bitmask.log')


def get_logger():
    """
    Push to the app stack the needed handlers and return a Logger object.

    :rtype: logbook.Logger
    """
    level = logbook.WARNING
    if flags.DEBUG:
        level = logbook.NOTSET

    # This handler consumes logs not handled by the others
    null_handler = logbook.NullHandler(bubble=False)
    null_handler.push_application()

    silencer = SelectiveSilencerFilter()

    zmq_handler = SafeZMQHandler('tcp://127.0.0.1:5000', multi=True,
                                 level=level, filter=silencer.filter)
    zmq_handler.push_application()

    file_handler = logbook.FileHandler(BITMASK_LOG_FILE,
                                       format_string=LOG_FORMAT, bubble=True,
                                       filter=silencer.filter)
    file_handler.push_application()

    # don't use simple stream, go for colored log handler instead
    # stream_handler = logbook.StreamHandler(sys.stdout,
    #                                        format_string=LOG_FORMAT,
    #                                        bubble=True)
    # stream_handler.push_application()
    stream_handler = ColorizedStderrHandler(
        level=level, format_string=LOG_FORMAT, bubble=True,
        filter=silencer.filter)
    stream_handler.push_application()

    logger = logbook.Logger('leap')

    return logger


def replace_stdout_stderr_with_logging(logger=None):
    """
    NOTE:
        we are not using this right now (see commented lines on app.py),
        this needs to be reviewed since the log handler has changed.

    Replace:
        - the standard output
        - the standard error
        - the twisted log output
    with a custom one that writes to the logger.
    """
    # Disabling this on windows since it breaks ALL THE THINGS
    # The issue for this is #4149
    if not IS_WIN:
        # logger = get_logger()
        # sys.stdout = StreamToLogger(logger, logbook.NOTSET)
        # sys.stderr = StreamToLogger(logger, logging.ERROR)

        # Replace twisted's logger to use our custom output.
        from twisted.python import log
        log.startLogging(sys.stdout)
