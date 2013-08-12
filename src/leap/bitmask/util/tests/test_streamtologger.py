# -*- coding: utf-8 -*-
# test_streamtologger.py
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
tests for streamtologger
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import logging
import sys

from leap.bitmask.util.streamtologger import StreamToLogger
from leap.common.testing.basetest import BaseLeapTest


class SimpleLogHandler(logging.Handler):
    """
    The simplest log handler that allows to check if the log was
    delivered to the handler correctly.
    """
    def __init__(self):
        logging.Handler.__init__(self)
        self._last_log = ""
        self._last_log_level = ""

    def emit(self, record):
        self._last_log = record.getMessage()
        self._last_log_level = record.levelno

    def get_last_log(self):
        """
        Returns the last logged message by this handler.

        :return: the last logged message.
        :rtype: str
        """
        return self._last_log

    def get_last_log_level(self):
        """
        Returns the level of the last logged message by this handler.

        :return: the last logged level.
        :rtype: str
        """
        return self._last_log_level


class StreamToLoggerTest(BaseLeapTest):
    """
    StreamToLogger's tests.

    NOTE: we may need to find a way to test the use case that an exception
    is raised. I couldn't catch the output of an exception because the
    test failed if some exception is raised.
    """
    def setUp(self):
        # Create the logger
        level = logging.DEBUG
        self.logger = logging.getLogger(name='test')
        self.logger.setLevel(level)

        # Simple log handler
        self.handler = SimpleLogHandler()
        self.logger.addHandler(self.handler)

        # Preserve original values
        self._sys_stdout = sys.stdout
        self._sys_stderr = sys.stderr

        # Create the handler
        sys.stdout = StreamToLogger(self.logger, logging.DEBUG)
        sys.stderr = StreamToLogger(self.logger, logging.ERROR)

    def tearDown(self):
        # Restore original values
        sys.stdout = self._sys_stdout
        sys.stderr = self._sys_stderr

    def test_logger_starts_empty(self):
        self.assertEqual(self.handler.get_last_log(), '')

    def test_standard_output(self):
        message = 'Test string'
        print message

        log = self.handler.get_last_log()
        log_level = self.handler.get_last_log_level()

        self.assertEqual(log, message)
        self.assertEqual(log_level, logging.DEBUG)

    def test_standard_error(self):
        message = 'Test string'
        sys.stderr.write(message)

        log_level = self.handler.get_last_log_level()
        log = self.handler.get_last_log()

        self.assertEqual(log, message)
        self.assertEqual(log_level, logging.ERROR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
