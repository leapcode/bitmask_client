# -*- coding: utf-8 -*-
# test_leapsettings.py
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
Tests for leapsettings module.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import mock

from leap.common.testing.basetest import BaseLeapTest
from leap.bitmask.config.leapsettings import LeapSettings


class LeapSettingsTest(BaseLeapTest):
    """Tests for LeapSettings"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_configured_providers(self):
        """
        Test that the config file IS NOT stored under the CWD.
        """
        self._leapsettings = LeapSettings()
        with mock.patch('os.listdir') as os_listdir:
            # use this method only to spy where LeapSettings is looking for
            self._leapsettings.get_configured_providers()
            args, kwargs = os_listdir.call_args
            config_dir = args[0]
            self.assertFalse(config_dir.startswith(os.getcwd()))
            self.assertFalse(config_dir.endswith('config'))

    def test_get_configured_providers_in_bundle(self):
        """
        Test that the config file IS stored under the CWD.
        """
        self._leapsettings = LeapSettings(standalone=True)
        with mock.patch('os.listdir') as os_listdir:
            # use this method only to spy where LeapSettings is looking for
            self._leapsettings.get_configured_providers()
            args, kwargs = os_listdir.call_args
            config_dir = args[0]
            self.assertTrue(config_dir.startswith(os.getcwd()))
            self.assertFalse(config_dir.endswith('config'))


if __name__ == "__main__":
    unittest.main()
