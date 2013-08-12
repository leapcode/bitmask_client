# -*- coding: utf-8 -*-
# test_leap_log_handler.py
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
tests for leap_log_handler
"""

import unittest

import logging

from leap.util.leap_log_handler import LeapLogHandler
from leap.common.testing.basetest import BaseLeapTest
from leap.util.pyside_tests_helper import BasicPySlotCase

from mock import Mock


class LeapLogHandlerTest(BaseLeapTest, BasicPySlotCase):
    """
    LeapLogHandlerTest's tests.
    """
    def _callback(self, *args):
        """
        Simple callback to track if a signal was emitted.
        """
        self.called = True
        self.emitted_msg = args[0][LeapLogHandler.MESSAGE_KEY]

    def setUp(self):
        BasicPySlotCase.setUp(self)

        # Create the logger
        level = logging.DEBUG
        self.logger = logging.getLogger(name='test')
        self.logger.setLevel(level)

        # Create the handler
        self.leap_handler = LeapLogHandler()
        self.leap_handler.setLevel(level)
        self.logger.addHandler(self.leap_handler)

    def tearDown(self):
        BasicPySlotCase.tearDown(self)
        try:
            self.leap_handler.new_log.disconnect()
        except Exception:
            pass

    def test_history_starts_empty(self):
        self.assertEqual(self.leap_handler.log_history, [])

    def test_one_log_captured(self):
        self.logger.debug('test')
        self.assertEqual(len(self.leap_handler.log_history), 1)

    def test_history_records_order(self):
        self.logger.debug('test 01')
        self.logger.debug('test 02')
        self.logger.debug('test 03')

        logs = []
        for message in self.leap_handler.log_history:
            logs.append(message[LeapLogHandler.RECORD_KEY].msg)

        self.assertIn('test 01', logs)
        self.assertIn('test 02', logs)
        self.assertIn('test 03', logs)

    def test_history_messages_order(self):
        self.logger.debug('test 01')
        self.logger.debug('test 02')
        self.logger.debug('test 03')

        logs = []
        for message in self.leap_handler.log_history:
            logs.append(message[LeapLogHandler.MESSAGE_KEY])

        self.assertIn('test 01', logs[0])
        self.assertIn('test 02', logs[1])
        self.assertIn('test 03', logs[2])

    def test_emits_signal(self):
        log_format = '%(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        get_format = Mock(return_value=formatter)
        self.leap_handler._handler._get_format = get_format

        self.leap_handler.new_log.connect(self._callback)
        self.logger.debug('test')

        expected_log_msg = "test - DEBUG - test"

        # signal emitted
        self.assertTrue(self.called)

        # emitted message
        self.assertEqual(self.emitted_msg, expected_log_msg)

        # Mock called
        self.assertTrue(get_format.called)


if __name__ == "__main__":
    unittest.main()
