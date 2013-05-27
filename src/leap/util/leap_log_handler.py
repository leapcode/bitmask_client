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


class LeapLogHandler(logging.Handler, QtCore.QObject):
    """
    Custom logging handler. It emits Qt signals so it can be plugged to a gui.
    Also stores an history of logs that can be fetched after connect to a gui.
    """
    # All dicts returned are of the form
    # {'record': LogRecord, 'message': str}
    new_log = QtCore.Signal(dict)

    MESSAGE_KEY = 'message'
    RECORD_KEY = 'record'

    def __init__(self):
        logging.Handler.__init__(self)
        QtCore.QObject.__init__(self)

        self._log_history = []

    def _set_format(self, logging_level):
        """
        Sets the log format depending on the parameter.
        It uses html and css to set the colors for the logs.

        :param logging_level: the debug level to define the color.
        :type logging_level: str.
        """
        html_style = {
            'DEBUG': "color: blue",
            'INFO': "color: black",
            'WARNING': "color: black; background: yellow;",
            'ERROR': "color: red",
            'CRITICAL': "color: red; font-weight: bold;"
        }

        style_open = "<span style='" + html_style[logging_level] + "'>"
        style_close = "</span>"
        time = "%(asctime)s"
        name = style_open + "%(name)s"
        level = "%(levelname)s"
        message = "%(message)s" + style_close
        format_attrs = [time, name, level, message]
        log_format = ' - '.join(format_attrs)
        formatter = logging.Formatter(log_format)
        self.setFormatter(formatter)

    def emit(self, logRecord):
        """
        This method is fired every time that a record is logged by the
        logging module.
        This method reimplements logging.Handler.emit that is fired
        in every logged message.
        QObject.emit gets in the way on the PySide signal model but we
        workarouded that issue.

        :param logRecord: the record emitted by the logging module.
        :type logRecord: logging.LogRecord.
        """
        self._set_format(logRecord.levelname)
        log = self.format(logRecord)
        log_item = {self.RECORD_KEY: logRecord, self.MESSAGE_KEY: log}
        self._log_history.append(log_item)

        # WARNING: the new-style connection does NOT work because PySide
        # translates the emit method to self.emit, and that collides with
        # the emit method for logging.Handler
        # self.new_log.emit(log_item)
        QtCore.QObject.emit(self, QtCore.SIGNAL('new_log(PyObject)'), log_item)

    @property
    def log_history(self):
        """
        Returns the history of the logged messages.
        """
        return self._log_history
