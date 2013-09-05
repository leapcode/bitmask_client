# -*- coding: utf-8 -*-
# test_is_release_version.py
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
tests for _is_release_version function
"""
import unittest

from leap.bitmask import _is_release_version as is_release_version
from leap.common.testing.basetest import BaseLeapTest


class TestIsReleaseVersion(BaseLeapTest):
    """Tests for release version check."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_git_version(self):
        version = '0.2.3-12-ge5b50a1'
        self.assertFalse(is_release_version(version))

    def test_release(self):
        version = '0.2.4'
        self.assertTrue(is_release_version(version))

    def test_release_candidate(self):
        version = '0.2.4-rc1'
        self.assertFalse(is_release_version(version))

    def test_complex_version(self):
        version = '12.5.2.4-rc12.dev.alpha1'
        self.assertFalse(is_release_version(version))

    def test_super_high_version(self):
        version = '12.5.2.4.45'
        self.assertTrue(is_release_version(version))


if __name__ == "__main__":
    unittest.main(verbosity=2)
