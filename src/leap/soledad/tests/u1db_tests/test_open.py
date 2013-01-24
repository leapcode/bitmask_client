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

"""Test u1db.open"""

import os

from u1db import (
    errors,
    open as u1db_open,
)
from leap.soledad.tests import u1db_tests as tests
from u1db.backends import sqlite_backend
from leap.soledad.tests.u1db_tests.test_backends import TestAlternativeDocument


class TestU1DBOpen(tests.TestCase):

    def setUp(self):
        super(TestU1DBOpen, self).setUp()
        tmpdir = self.createTempDir()
        self.db_path = tmpdir + '/test.db'

    def test_open_no_create(self):
        self.assertRaises(errors.DatabaseDoesNotExist,
                          u1db_open, self.db_path, create=False)
        self.assertFalse(os.path.exists(self.db_path))

    def test_open_create(self):
        db = u1db_open(self.db_path, create=True)
        self.addCleanup(db.close)
        self.assertTrue(os.path.exists(self.db_path))
        self.assertIsInstance(db, sqlite_backend.SQLiteDatabase)

    def test_open_with_factory(self):
        db = u1db_open(self.db_path, create=True,
                       document_factory=TestAlternativeDocument)
        self.addCleanup(db.close)
        self.assertEqual(TestAlternativeDocument, db._factory)

    def test_open_existing(self):
        db = sqlite_backend.SQLitePartialExpandDatabase(self.db_path)
        self.addCleanup(db.close)
        doc = db.create_doc_from_json(tests.simple_doc)
        # Even though create=True, we shouldn't wipe the db
        db2 = u1db_open(self.db_path, create=True)
        self.addCleanup(db2.close)
        doc2 = db2.get_doc(doc.doc_id)
        self.assertEqual(doc, doc2)

    def test_open_existing_no_create(self):
        db = sqlite_backend.SQLitePartialExpandDatabase(self.db_path)
        self.addCleanup(db.close)
        db2 = u1db_open(self.db_path, create=False)
        self.addCleanup(db2.close)
        self.assertIsInstance(db2, sqlite_backend.SQLitePartialExpandDatabase)
