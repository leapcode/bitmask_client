# Copyright 2011 Canonical Ltd.
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

"""Tests error infrastructure."""

from u1db import (
    errors,
    tests,
    )


class TestError(tests.TestCase):

    def test_error_base(self):
        err = errors.U1DBError()
        self.assertEqual("error", err.wire_description)
        self.assertIs(None, err.message)

        err = errors.U1DBError("Message.")
        self.assertEqual("error", err.wire_description)
        self.assertEqual("Message.", err.message)

    def test_HTTPError(self):
        err = errors.HTTPError(500)
        self.assertEqual(500, err.status)
        self.assertIs(None, err.wire_description)
        self.assertIs(None, err.message)

        err = errors.HTTPError(500, "Crash.")
        self.assertEqual(500, err.status)
        self.assertIs(None, err.wire_description)
        self.assertEqual("Crash.", err.message)

    def test_HTTPError_str(self):
        err = errors.HTTPError(500)
        self.assertEqual("HTTPError(500)", str(err))

        err = errors.HTTPError(500, "ERROR")
        self.assertEqual("HTTPError(500, 'ERROR')", str(err))

    def test_Unvailable(self):
        err = errors.Unavailable()
        self.assertEqual(503, err.status)
        self.assertEqual("Unavailable()", str(err))

        err = errors.Unavailable("DOWN")
        self.assertEqual("DOWN", err.message)
        self.assertEqual("Unavailable('DOWN')", str(err))
