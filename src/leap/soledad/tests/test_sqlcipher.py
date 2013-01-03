"""Test sqlcipher backend internals."""

import os
import time
import threading
import unittest2 as unittest

from sqlite3 import dbapi2

from u1db import (
    errors,
    query_parser,
    )
from leap.soledad.backends import sqlcipher as sqlite_backend
from leap.soledad.backends.leap_backend import LeapDocument
from leap.soledad.tests import u1db_tests
from leap.soledad.tests.u1db_tests.test_sqlite_backend import (
  TestSQLiteDatabase,
  TestSQLitePartialExpandDatabase,
)
from leap.soledad.tests.u1db_tests.test_backends import TestAlternativeDocument

PASSWORD = '123456'


class TestSQLCipherDatabase(TestSQLitePartialExpandDatabase):

    def setUp(self):
        super(TestSQLitePartialExpandDatabase, self).setUp()
        self.db = sqlite_backend.SQLCipherDatabase(':memory:', PASSWORD)
        self.db._set_replica_uid('test')

    def test_default_replica_uid(self):
        self.db = sqlite_backend.SQLCipherDatabase(':memory:', PASSWORD)
        self.assertIsNot(None, self.db._replica_uid)
        self.assertEqual(32, len(self.db._replica_uid))
        int(self.db._replica_uid, 16)

    def test__parse_index(self):
        self.db = sqlite_backend.SQLCipherDatabase(':memory:', PASSWORD)
        g = self.db._parse_index_definition('fieldname')
        self.assertIsInstance(g, query_parser.ExtractField)
        self.assertEqual(['fieldname'], g.field)

    def test__update_indexes(self):
        self.db = sqlite_backend.SQLCipherDatabase(':memory:', PASSWORD)
        g = self.db._parse_index_definition('fieldname')
        c = self.db._get_sqlite_handle().cursor()
        self.db._update_indexes('doc-id', {'fieldname': 'val'},
                                [('fieldname', g)], c)
        c.execute('SELECT doc_id, field_name, value FROM document_fields')
        self.assertEqual([('doc-id', 'fieldname', 'val')],
                         c.fetchall())

    def test__set_replica_uid(self):
        # Start from scratch, so that replica_uid isn't set.
        self.db = sqlite_backend.SQLCipherDatabase(':memory:', PASSWORD)
        self.assertIsNot(None, self.db._real_replica_uid)
        self.assertIsNot(None, self.db._replica_uid)
        self.db._set_replica_uid('foo')
        c = self.db._get_sqlite_handle().cursor()
        c.execute("SELECT value FROM u1db_config WHERE name='replica_uid'")
        self.assertEqual(('foo',), c.fetchone())
        self.assertEqual('foo', self.db._real_replica_uid)
        self.assertEqual('foo', self.db._replica_uid)
        self.db._close_sqlite_handle()
        self.assertEqual('foo', self.db._replica_uid)

    def test__open_database(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/test.sqlite'
        sqlite_backend.SQLCipherDatabase(path, PASSWORD)
        db2 = sqlite_backend.SQLCipherDatabase._open_database(path, PASSWORD)
        self.assertIsInstance(db2, sqlite_backend.SQLCipherDatabase)

    def test__open_database_with_factory(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/test.sqlite'
        sqlite_backend.SQLCipherDatabase(path, PASSWORD)
        db2 = sqlite_backend.SQLCipherDatabase._open_database(
            path, PASSWORD, document_factory=TestAlternativeDocument)
        self.assertEqual(TestAlternativeDocument, db2._factory)

    def test_open_database_existing(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/existing.sqlite'
        sqlite_backend.SQLCipherDatabase(path, PASSWORD)
        db2 = sqlite_backend.SQLCipherDatabase.open_database(path, PASSWORD, create=False)
        self.assertIsInstance(db2, sqlite_backend.SQLCipherDatabase)

    def test_open_database_with_factory(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/existing.sqlite'
        sqlite_backend.SQLCipherDatabase(path, PASSWORD)
        db2 = sqlite_backend.SQLCipherDatabase.open_database(
            path, PASSWORD, create=False, document_factory=TestAlternativeDocument)
        self.assertEqual(TestAlternativeDocument, db2._factory)

    def test_create_database_initializes_schema(self):
        raw_db = self.db._get_sqlite_handle()
        c = raw_db.cursor()
        c.execute("SELECT * FROM u1db_config")
        config = dict([(r[0], r[1]) for r in c.fetchall()])
        self.assertEqual({'sql_schema': '0', 'replica_uid': 'test',
                          'index_storage': 'expand referenced encrypted'}, config)
