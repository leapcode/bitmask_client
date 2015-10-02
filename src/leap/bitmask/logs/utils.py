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
from leap.common.files import mkdir_p

from PySide import QtCore

import logbook
from logbook.more import ColorizedStderrHandler
from logbook.queues import ZeroMQSubscriber


# NOTE: make sure that the folder exists, the logger is created before saving
# settings on the first run.
_base = os.path.join(get_path_prefix(), "leap")
mkdir_p(_base)
BITMASK_LOG_FILE = os.path.join(_base, 'bitmask.log')


def get_logger(perform_rollover=False):
    """
    Push to the app stack the needed handlers and return a Logger object.

    :rtype: logbook.Logger
    """
    level = logbook.WARNING
    if flags.DEBUG:
        level = logbook.NOTSET

    # This handler consumes logs not handled by the others
    null_handler = logbook.NullHandler()
    null_handler.push_application()

    silencer = SelectiveSilencerFilter()

    zmq_handler = SafeZMQHandler('tcp://127.0.0.1:5000', multi=True,
                                 level=level, filter=silencer.filter)
    zmq_handler.push_application()

    file_handler = logbook.RotatingFileHandler(
        BITMASK_LOG_FILE, format_string=LOG_FORMAT, bubble=True,
        filter=silencer.filter, max_size=sys.maxint)

    if perform_rollover:
        file_handler.perform_rollover()

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


class QtLogHandler(logbook.Handler, logbook.StringFormatterHandlerMixin):
    """
    Custom log handler which emits a log record with the message properly
    formatted using a Qt Signal.
    """

    class _QtSignaler(QtCore.QObject):
        """
        inline class used to hold the `new_log` Signal, if this is used
        directly in the outside class it fails due how PySide works.

        This is the message we get if not use this method:
        TypeError: Error when calling the metaclass bases
            metaclass conflict: the metaclass of a derived class must be a
            (non-strict) subclass of the metaclasses of all its bases

        """
        new_log = QtCore.Signal(object)

        def emit(self, data):
            """
            emit the `new_log` Signal with the given `data` parameter.

            :param data: the data to emit along with the signal.
            :type data: object
            """
            # WARNING: the new-style connection does NOT work because PySide
            # translates the emit method to self.emit, and that collides with
            # the emit method for logging.Handler
            # self.new_log.emit(log_item)
            QtCore.QObject.emit(self, QtCore.SIGNAL('new_log(PyObject)'), data)

    def __init__(self, level=logbook.NOTSET, format_string=None,
                 encoding=None, filter=None, bubble=False):

        logbook.Handler.__init__(self, level, filter, bubble)
        logbook.StringFormatterHandlerMixin.__init__(self, format_string)

        self.qt = self._QtSignaler()
        self.logs = []

    def __enter__(self):
        return logbook.Handler.__enter__(self)

    def __exit__(self, exc_type, exc_value, tb):
        return logbook.Handler.__exit__(self, exc_type, exc_value, tb)

    def emit(self, record):
        """
        Emit the specified logging record using a Qt Signal.
        Also add it to the history in order to be able to access it later.

        :param record: the record to emit
        :type record: logbook.LogRecord
        """
        global _LOGS_HISTORY
        record.msg = self.format(record)
        # NOTE: not optimal approach, we may want to look at
        # bisect.insort with a custom approach to use key or
        # http://code.activestate.com/recipes/577197-sortedcollection/
        # Sort logs on arrival, logs transmitted over zmq may arrive unsorted.
        self.logs.append(record)
        self.logs = sorted(self.logs, key=lambda r: r.time)

        # XXX: emitting the record on arrival does not allow us to sort here so
        # in the GUI the logs may arrive with with some time sort problem.
        # We should implement a sort-on-arrive for the log window.
        # Maybe we should switch to a tablewidget item that sort automatically
        # by timestamp.
        # As a user workaround you can close/open the log window
        self.qt.emit(record)


class _LogController(object):

    def __init__(self):
        self._qt_handler = QtLogHandler(format_string=LOG_FORMAT)
        self._logbook_controller = None
        self.new_log = self._qt_handler.qt.new_log

    def start_logbook_subscriber(self):
        """
        Run in the background the log receiver.
        """
        if self._logbook_controller is None:
            subscriber = ZeroMQSubscriber('tcp://127.0.0.1:5000', multi=True)
            self._logbook_controller = subscriber.dispatch_in_background(
                self._qt_handler)

    def stop_logbook_subscriber(self):
        """
        Stop the background thread that receives messages through zmq, also
        close the subscriber socket.
        This allows us to re-create the subscriber when we reopen this window
        without getting an error at trying to connect twice to the zmq port.
        """
        if self._logbook_controller is not None:
            self._logbook_controller.stop()
            self._logbook_controller.subscriber.close()
            self._logbook_controller = None

    def get_logs(self):
        return self._qt_handler.logs

# use a global variable to store received logs through different opened
# instances of the log window as well as to containing the logbook background
# handle.
LOG_CONTROLLER = _LogController()
