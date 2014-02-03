# -*- coding: utf-8 -*-
# leap_log_handler.py
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
Custom handler for the logger window.
"""
import logging

from PySide import QtCore

from leap.bitmask.util import LOG_FORMAT


class LogHandler(logging.Handler):
    """
    This is the custom handler that implements our desired formatting
    and also keeps a history of all the logged events.
    """

    MESSAGE_KEY = 'message'
    RECORD_KEY = 'record'

    def __init__(self, qtsignal):
        """
        LogHander initialization.
        Calls parent method and keeps a reference to the qtsignal
        that will be used to fire the gui update.
        """
        # TODO This is going to eat lots of memory after some time.
        # Should be pruned at some moment.
        self._log_history = []

        logging.Handler.__init__(self)
        self._qtsignal = qtsignal

    def _get_format(self, logging_level):
        """
        Sets the log format depending on the parameter.
        It uses html and css to set the colors for the logs.

        :param logging_level: the debug level to define the color.
        :type logging_level: str.
        """
        formatter = logging.Formatter(LOG_FORMAT)
        return formatter

    def emit(self, logRecord):
        """
        This method is fired every time that a record is logged by the
        logging module.
        This method reimplements logging.Handler.emit that is fired
        in every logged message.

        :param logRecord: the record emitted by the logging module.
        :type logRecord: logging.LogRecord.
        """
        self.setFormatter(self._get_format(logRecord.levelname))
        log = self.format(logRecord)
        log_item = {self.RECORD_KEY: logRecord, self.MESSAGE_KEY: log}
        self._log_history.append(log_item)
        self._qtsignal(log_item)


class HandlerAdapter(object):
    """
    New style class that accesses all attributes from the LogHandler.

    Used as a workaround for a problem with multiple inheritance with Pyside
    that surfaced under OSX with pyside 1.1.0.
    """
    MESSAGE_KEY = 'message'
    RECORD_KEY = 'record'

    def __init__(self, qtsignal):
        self._handler = LogHandler(qtsignal=qtsignal)

    def setLevel(self, *args, **kwargs):
        return self._handler.setLevel(*args, **kwargs)

    def addFilter(self, *args, **kwargs):
        return self._handler.addFilter(*args, **kwargs)

    def handle(self, *args, **kwargs):
        return self._handler.handle(*args, **kwargs)

    @property
    def level(self):
        return self._handler.level


class LeapLogHandler(QtCore.QObject, HandlerAdapter):
    """
    Custom logging handler. It emits Qt signals so it can be plugged to a gui.

    Its inner handler also stores an history of logs that can be fetched after
    having been connected to a gui.
    """
    # All dicts returned are of the form
    # {'record': LogRecord, 'message': str}
    new_log = QtCore.Signal(dict)

    def __init__(self):
        """
        LeapLogHandler initialization.
        Initializes parent classes.
        """
        QtCore.QObject.__init__(self)
        HandlerAdapter.__init__(self, qtsignal=self.qtsignal)

    def qtsignal(self, log_item):
        # WARNING: the new-style connection does NOT work because PySide
        # translates the emit method to self.emit, and that collides with
        # the emit method for logging.Handler
        # self.new_log.emit(log_item)
        QtCore.QObject.emit(
            self,
            QtCore.SIGNAL('new_log(PyObject)'), log_item)

    @property
    def log_history(self):
        """
        Returns the history of the logged messages.
        """
        return self._handler._log_history
