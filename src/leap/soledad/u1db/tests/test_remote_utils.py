# Copyright 2012 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for protocol details utils."""

from u1db.tests import TestCase
from u1db.remote import utils


class TestUtils(TestCase):

    def test_check_and_strip_comma(self):
        line, comma = utils.check_and_strip_comma("abc,")
        self.assertTrue(comma)
        self.assertEqual("abc", line)

        line, comma = utils.check_and_strip_comma("abc")
        self.assertFalse(comma)
        self.assertEqual("abc", line)

        line, comma = utils.check_and_strip_comma("")
        self.assertFalse(comma)
        self.assertEqual("", line)
