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

"""Tests for server state object."""

import os

from u1db import (
    errors,
    tests,
    )
from u1db.remote import (
    server_state,
    )
from u1db.backends import sqlite_backend


class TestServerState(tests.TestCase):

    def setUp(self):
        super(TestServerState, self).setUp()
        self.state = server_state.ServerState()

    def test_set_workingdir(self):
        tempdir = self.createTempDir()
        self.state.set_workingdir(tempdir)
        self.assertTrue(self.state._relpath('path').startswith(tempdir))

    def test_open_database(self):
        tempdir = self.createTempDir()
        self.state.set_workingdir(tempdir)
        path = tempdir + '/test.db'
        self.assertFalse(os.path.exists(path))
        # Create the db, but don't do anything with it
        sqlite_backend.SQLitePartialExpandDatabase(path)
        db = self.state.open_database('test.db')
        self.assertIsInstance(db, sqlite_backend.SQLitePartialExpandDatabase)

    def test_check_database(self):
        tempdir = self.createTempDir()
        self.state.set_workingdir(tempdir)
        path = tempdir + '/test.db'
        self.assertFalse(os.path.exists(path))

        # doesn't exist => raises
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.state.check_database, 'test.db')

        # Create the db, but don't do anything with it
        sqlite_backend.SQLitePartialExpandDatabase(path)
        # exists => returns
        res = self.state.check_database('test.db')
        self.assertIsNone(res)

    def test_ensure_database(self):
        tempdir = self.createTempDir()
        self.state.set_workingdir(tempdir)
        path = tempdir + '/test.db'
        self.assertFalse(os.path.exists(path))
        db, replica_uid = self.state.ensure_database('test.db')
        self.assertIsInstance(db, sqlite_backend.SQLitePartialExpandDatabase)
        self.assertEqual(db._replica_uid, replica_uid)
        self.assertTrue(os.path.exists(path))
        db2 = self.state.open_database('test.db')
        self.assertIsInstance(db2, sqlite_backend.SQLitePartialExpandDatabase)

    def test_delete_database(self):
        tempdir = self.createTempDir()
        self.state.set_workingdir(tempdir)
        path = tempdir + '/test.db'
        db, _ = self.state.ensure_database('test.db')
        db.close()
        self.state.delete_database('test.db')
        self.assertFalse(os.path.exists(path))

    def test_delete_database_DoesNotExist(self):
        tempdir = self.createTempDir()
        self.state.set_workingdir(tempdir)
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.state.delete_database, 'test.db')
