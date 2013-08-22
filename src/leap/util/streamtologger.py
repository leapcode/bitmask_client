# -*- coding: utf-8 -*-
# streamtologger.py
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
Stream object that redirects writes to a logger instance.
"""
import logging


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.

    Credits to:
    http://www.electricmonk.nl/log/2011/08/14/\
        redirect-stdout-and-stderr-to-a-logger-in-python/
    """
    def __init__(self, logger, log_level=logging.INFO):
        """
        Constructor, defines the logger and level to use to log messages.

        :param logger: logger object to log messages.
        :type logger: logging.Handler
        :param log_level: the level to use to log messages through the logger.
        :type log_level: int
                        look at logging-levels in 'logging' docs.
        """
        self._logger = logger
        self._log_level = log_level

    def write(self, data):
        """
        Simulates the 'write' method in a file object.
        It writes the data receibed in buf to the logger 'self._logger'.

        :param data: data to write to the 'file'
        :type data: str
        """
        for line in data.rstrip().splitlines():
            self._logger.log(self._log_level, line.rstrip())

    def flush(self):
        """
        Dummy method. Needed to replace the twisted.log output.
        """
        pass
