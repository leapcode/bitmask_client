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

"""Test sqlite backend internals."""

import os
import time
import threading

from sqlite3 import dbapi2

from u1db import (
    errors,
    query_parser,
)

from leap.soledad.tests import u1db_tests as tests

from u1db.backends import sqlite_backend
from leap.soledad.tests.u1db_tests.test_backends import TestAlternativeDocument


simple_doc = '{"key": "value"}'
nested_doc = '{"key": "value", "sub": {"doc": "underneath"}}'


class TestSQLiteDatabase(tests.TestCase):

    def test_atomic_initialize(self):
        tmpdir = self.createTempDir()
        dbname = os.path.join(tmpdir, 'atomic.db')

        t2 = None  # will be a thread

        class SQLiteDatabaseTesting(sqlite_backend.SQLiteDatabase):
            _index_storage_value = "testing"

            def __init__(self, dbname, ntry):
                self._try = ntry
                self._is_initialized_invocations = 0
                super(SQLiteDatabaseTesting, self).__init__(dbname)

            def _is_initialized(self, c):
                res = super(SQLiteDatabaseTesting, self)._is_initialized(c)
                if self._try == 1:
                    self._is_initialized_invocations += 1
                    if self._is_initialized_invocations == 2:
                        t2.start()
                        # hard to do better and have a generic test
                        time.sleep(0.05)
                return res

        outcome2 = []

        def second_try():
            try:
                db2 = SQLiteDatabaseTesting(dbname, 2)
            except Exception, e:
                outcome2.append(e)
            else:
                outcome2.append(db2)

        t2 = threading.Thread(target=second_try)
        db1 = SQLiteDatabaseTesting(dbname, 1)
        t2.join()

        self.assertIsInstance(outcome2[0], SQLiteDatabaseTesting)
        db2 = outcome2[0]
        self.assertTrue(db2._is_initialized(db1._get_sqlite_handle().cursor()))


class TestSQLitePartialExpandDatabase(tests.TestCase):

    def setUp(self):
        super(TestSQLitePartialExpandDatabase, self).setUp()
        self.db = sqlite_backend.SQLitePartialExpandDatabase(':memory:')
        self.db._set_replica_uid('test')

    def test_create_database(self):
        raw_db = self.db._get_sqlite_handle()
        self.assertNotEqual(None, raw_db)

    def test_default_replica_uid(self):
        self.db = sqlite_backend.SQLitePartialExpandDatabase(':memory:')
        self.assertIsNot(None, self.db._replica_uid)
        self.assertEqual(32, len(self.db._replica_uid))
        int(self.db._replica_uid, 16)

    def test__close_sqlite_handle(self):
        raw_db = self.db._get_sqlite_handle()
        self.db._close_sqlite_handle()
        self.assertRaises(dbapi2.ProgrammingError,
                          raw_db.cursor)

    def test_create_database_initializes_schema(self):
        raw_db = self.db._get_sqlite_handle()
        c = raw_db.cursor()
        c.execute("SELECT * FROM u1db_config")
        config = dict([(r[0], r[1]) for r in c.fetchall()])
        self.assertEqual({'sql_schema': '0', 'replica_uid': 'test',
                          'index_storage': 'expand referenced'}, config)

        # These tables must exist, though we don't care what is in them yet
        c.execute("SELECT * FROM transaction_log")
        c.execute("SELECT * FROM document")
        c.execute("SELECT * FROM document_fields")
        c.execute("SELECT * FROM sync_log")
        c.execute("SELECT * FROM conflicts")
        c.execute("SELECT * FROM index_definitions")

    def test__parse_index(self):
        self.db = sqlite_backend.SQLitePartialExpandDatabase(':memory:')
        g = self.db._parse_index_definition('fieldname')
        self.assertIsInstance(g, query_parser.ExtractField)
        self.assertEqual(['fieldname'], g.field)

    def test__update_indexes(self):
        self.db = sqlite_backend.SQLitePartialExpandDatabase(':memory:')
        g = self.db._parse_index_definition('fieldname')
        c = self.db._get_sqlite_handle().cursor()
        self.db._update_indexes('doc-id', {'fieldname': 'val'},
                                [('fieldname', g)], c)
        c.execute('SELECT doc_id, field_name, value FROM document_fields')
        self.assertEqual([('doc-id', 'fieldname', 'val')],
                         c.fetchall())

    def test__set_replica_uid(self):
        # Start from scratch, so that replica_uid isn't set.
        self.db = sqlite_backend.SQLitePartialExpandDatabase(':memory:')
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

    def test__get_generation(self):
        self.assertEqual(0, self.db._get_generation())

    def test__get_generation_info(self):
        self.assertEqual((0, ''), self.db._get_generation_info())

    def test_create_index(self):
        self.db.create_index('test-idx', "key")
        self.assertEqual([('test-idx', ["key"])], self.db.list_indexes())

    def test_create_index_multiple_fields(self):
        self.db.create_index('test-idx', "key", "key2")
        self.assertEqual([('test-idx', ["key", "key2"])],
                         self.db.list_indexes())

    def test__get_index_definition(self):
        self.db.create_index('test-idx', "key", "key2")
        # TODO: How would you test that an index is getting used for an SQL
        #       request?
        self.assertEqual(["key", "key2"],
                         self.db._get_index_definition('test-idx'))

    def test_list_index_mixed(self):
        # Make sure that we properly order the output
        c = self.db._get_sqlite_handle().cursor()
        # We intentionally insert the data in weird ordering, to make sure the
        # query still gets it back correctly.
        c.executemany("INSERT INTO index_definitions VALUES (?, ?, ?)",
                      [('idx-1', 0, 'key10'),
                       ('idx-2', 2, 'key22'),
                       ('idx-1', 1, 'key11'),
                       ('idx-2', 0, 'key20'),
                       ('idx-2', 1, 'key21')])
        self.assertEqual([('idx-1', ['key10', 'key11']),
                          ('idx-2', ['key20', 'key21', 'key22'])],
                         self.db.list_indexes())

    def test_no_indexes_no_document_fields(self):
        self.db.create_doc_from_json(
            '{"key1": "val1", "key2": "val2"}')
        c = self.db._get_sqlite_handle().cursor()
        c.execute("SELECT doc_id, field_name, value FROM document_fields"
                  " ORDER BY doc_id, field_name, value")
        self.assertEqual([], c.fetchall())

    def test_create_extracts_fields(self):
        doc1 = self.db.create_doc_from_json('{"key1": "val1", "key2": "val2"}')
        doc2 = self.db.create_doc_from_json('{"key1": "valx", "key2": "valy"}')
        c = self.db._get_sqlite_handle().cursor()
        c.execute("SELECT doc_id, field_name, value FROM document_fields"
                  " ORDER BY doc_id, field_name, value")
        self.assertEqual([], c.fetchall())
        self.db.create_index('test', 'key1', 'key2')
        c.execute("SELECT doc_id, field_name, value FROM document_fields"
                  " ORDER BY doc_id, field_name, value")
        self.assertEqual(sorted(
            [(doc1.doc_id, "key1", "val1"),
             (doc1.doc_id, "key2", "val2"),
             (doc2.doc_id, "key1", "valx"),
             (doc2.doc_id, "key2", "valy"), ]), sorted(c.fetchall()))

    def test_put_updates_fields(self):
        self.db.create_index('test', 'key1', 'key2')
        doc1 = self.db.create_doc_from_json(
            '{"key1": "val1", "key2": "val2"}')
        doc1.content = {"key1": "val1", "key2": "valy"}
        self.db.put_doc(doc1)
        c = self.db._get_sqlite_handle().cursor()
        c.execute("SELECT doc_id, field_name, value FROM document_fields"
                  " ORDER BY doc_id, field_name, value")
        self.assertEqual([(doc1.doc_id, "key1", "val1"),
                          (doc1.doc_id, "key2", "valy"), ], c.fetchall())

    def test_put_updates_nested_fields(self):
        self.db.create_index('test', 'key', 'sub.doc')
        doc1 = self.db.create_doc_from_json(nested_doc)
        c = self.db._get_sqlite_handle().cursor()
        c.execute("SELECT doc_id, field_name, value FROM document_fields"
                  " ORDER BY doc_id, field_name, value")
        self.assertEqual([(doc1.doc_id, "key", "value"),
                          (doc1.doc_id, "sub.doc", "underneath"), ],
                         c.fetchall())

    def test__ensure_schema_rollback(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/rollback.db'

        class SQLitePartialExpandDbTesting(
                sqlite_backend.SQLitePartialExpandDatabase):

            def _set_replica_uid_in_transaction(self, uid):
                super(SQLitePartialExpandDbTesting,
                      self)._set_replica_uid_in_transaction(uid)
                if fail:
                    raise Exception()

        db = SQLitePartialExpandDbTesting.__new__(SQLitePartialExpandDbTesting)
        db._db_handle = dbapi2.connect(path)  # db is there but not yet init-ed
        fail = True
        self.assertRaises(Exception, db._ensure_schema)
        fail = False
        db._initialize(db._db_handle.cursor())

    def test__open_database(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/test.sqlite'
        sqlite_backend.SQLitePartialExpandDatabase(path)
        db2 = sqlite_backend.SQLiteDatabase._open_database(path)
        self.assertIsInstance(db2, sqlite_backend.SQLitePartialExpandDatabase)

    def test__open_database_with_factory(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/test.sqlite'
        sqlite_backend.SQLitePartialExpandDatabase(path)
        db2 = sqlite_backend.SQLiteDatabase._open_database(
            path, document_factory=TestAlternativeDocument)
        self.assertEqual(TestAlternativeDocument, db2._factory)

    def test__open_database_non_existent(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/non-existent.sqlite'
        self.assertRaises(errors.DatabaseDoesNotExist,
                          sqlite_backend.SQLiteDatabase._open_database, path)

    def test__open_database_during_init(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/initialised.db'
        db = sqlite_backend.SQLitePartialExpandDatabase.__new__(
            sqlite_backend.SQLitePartialExpandDatabase)
        db._db_handle = dbapi2.connect(path)  # db is there but not yet init-ed
        self.addCleanup(db.close)
        observed = []

        class SQLiteDatabaseTesting(sqlite_backend.SQLiteDatabase):
            WAIT_FOR_PARALLEL_INIT_HALF_INTERVAL = 0.1

            @classmethod
            def _which_index_storage(cls, c):
                res = super(SQLiteDatabaseTesting, cls)._which_index_storage(c)
                db._ensure_schema()  # init db
                observed.append(res[0])
                return res

        db2 = SQLiteDatabaseTesting._open_database(path)
        self.addCleanup(db2.close)
        self.assertIsInstance(db2, sqlite_backend.SQLitePartialExpandDatabase)
        self.assertEqual(
            [None,
             sqlite_backend.SQLitePartialExpandDatabase._index_storage_value],
            observed)

    def test__open_database_invalid(self):
        class SQLiteDatabaseTesting(sqlite_backend.SQLiteDatabase):
            WAIT_FOR_PARALLEL_INIT_HALF_INTERVAL = 0.1
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path1 = temp_dir + '/invalid1.db'
        with open(path1, 'wb') as f:
            f.write("")
        self.assertRaises(dbapi2.OperationalError,
                          SQLiteDatabaseTesting._open_database, path1)
        with open(path1, 'wb') as f:
            f.write("invalid")
        self.assertRaises(dbapi2.DatabaseError,
                          SQLiteDatabaseTesting._open_database, path1)

    def test_open_database_existing(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/existing.sqlite'
        sqlite_backend.SQLitePartialExpandDatabase(path)
        db2 = sqlite_backend.SQLiteDatabase.open_database(path, create=False)
        self.assertIsInstance(db2, sqlite_backend.SQLitePartialExpandDatabase)

    def test_open_database_with_factory(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/existing.sqlite'
        sqlite_backend.SQLitePartialExpandDatabase(path)
        db2 = sqlite_backend.SQLiteDatabase.open_database(
            path, create=False, document_factory=TestAlternativeDocument)
        self.assertEqual(TestAlternativeDocument, db2._factory)

    def test_open_database_create(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/new.sqlite'
        sqlite_backend.SQLiteDatabase.open_database(path, create=True)
        db2 = sqlite_backend.SQLiteDatabase.open_database(path, create=False)
        self.assertIsInstance(db2, sqlite_backend.SQLitePartialExpandDatabase)

    def test_open_database_non_existent(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/non-existent.sqlite'
        self.assertRaises(errors.DatabaseDoesNotExist,
                          sqlite_backend.SQLiteDatabase.open_database, path,
                          create=False)

    def test_delete_database_existent(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/new.sqlite'
        db = sqlite_backend.SQLiteDatabase.open_database(path, create=True)
        db.close()
        sqlite_backend.SQLiteDatabase.delete_database(path)
        self.assertRaises(errors.DatabaseDoesNotExist,
                          sqlite_backend.SQLiteDatabase.open_database, path,
                          create=False)

    def test_delete_database_nonexistent(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/non-existent.sqlite'
        self.assertRaises(errors.DatabaseDoesNotExist,
                          sqlite_backend.SQLiteDatabase.delete_database, path)

    def test__get_indexed_fields(self):
        self.db.create_index('idx1', 'a', 'b')
        self.assertEqual(set(['a', 'b']), self.db._get_indexed_fields())
        self.db.create_index('idx2', 'b', 'c')
        self.assertEqual(set(['a', 'b', 'c']), self.db._get_indexed_fields())

    def test_indexed_fields_expanded(self):
        self.db.create_index('idx1', 'key1')
        doc1 = self.db.create_doc_from_json('{"key1": "val1", "key2": "val2"}')
        self.assertEqual(set(['key1']), self.db._get_indexed_fields())
        c = self.db._get_sqlite_handle().cursor()
        c.execute("SELECT doc_id, field_name, value FROM document_fields"
                  " ORDER BY doc_id, field_name, value")
        self.assertEqual([(doc1.doc_id, 'key1', 'val1')], c.fetchall())

    def test_create_index_updates_fields(self):
        doc1 = self.db.create_doc_from_json('{"key1": "val1", "key2": "val2"}')
        self.db.create_index('idx1', 'key1')
        self.assertEqual(set(['key1']), self.db._get_indexed_fields())
        c = self.db._get_sqlite_handle().cursor()
        c.execute("SELECT doc_id, field_name, value FROM document_fields"
                  " ORDER BY doc_id, field_name, value")
        self.assertEqual([(doc1.doc_id, 'key1', 'val1')], c.fetchall())

    def assertFormatQueryEquals(self, exp_statement, exp_args, definition,
                                values):
        statement, args = self.db._format_query(definition, values)
        self.assertEqual(exp_statement, statement)
        self.assertEqual(exp_args, args)

    def test__format_query(self):
        self.assertFormatQueryEquals(
            "SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM "
            "document d, document_fields d0 LEFT OUTER JOIN conflicts c ON "
            "c.doc_id = d.doc_id WHERE d.doc_id = d0.doc_id AND d0.field_name "
            "= ? AND d0.value = ? GROUP BY d.doc_id, d.doc_rev, d.content "
            "ORDER BY d0.value;", ["key1", "a"],
            ["key1"], ["a"])

    def test__format_query2(self):
        self.assertFormatQueryEquals(
            'SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM '
            'document d, document_fields d0, document_fields d1, '
            'document_fields d2 LEFT OUTER JOIN conflicts c ON c.doc_id = '
            'd.doc_id WHERE d.doc_id = d0.doc_id AND d0.field_name = ? AND '
            'd0.value = ? AND d.doc_id = d1.doc_id AND d1.field_name = ? AND '
            'd1.value = ? AND d.doc_id = d2.doc_id AND d2.field_name = ? AND '
            'd2.value = ? GROUP BY d.doc_id, d.doc_rev, d.content ORDER BY '
            'd0.value, d1.value, d2.value;',
            ["key1", "a", "key2", "b", "key3", "c"],
            ["key1", "key2", "key3"], ["a", "b", "c"])

    def test__format_query_wildcard(self):
        self.assertFormatQueryEquals(
            'SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM '
            'document d, document_fields d0, document_fields d1, '
            'document_fields d2 LEFT OUTER JOIN conflicts c ON c.doc_id = '
            'd.doc_id WHERE d.doc_id = d0.doc_id AND d0.field_name = ? AND '
            'd0.value = ? AND d.doc_id = d1.doc_id AND d1.field_name = ? AND '
            'd1.value GLOB ? AND d.doc_id = d2.doc_id AND d2.field_name = ? '
            'AND d2.value NOT NULL GROUP BY d.doc_id, d.doc_rev, d.content '
            'ORDER BY d0.value, d1.value, d2.value;',
            ["key1", "a", "key2", "b*", "key3"], ["key1", "key2", "key3"],
            ["a", "b*", "*"])

    def assertFormatRangeQueryEquals(self, exp_statement, exp_args, definition,
                                     start_value, end_value):
        statement, args = self.db._format_range_query(
            definition, start_value, end_value)
        self.assertEqual(exp_statement, statement)
        self.assertEqual(exp_args, args)

    def test__format_range_query(self):
        self.assertFormatRangeQueryEquals(
            'SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM '
            'document d, document_fields d0, document_fields d1, '
            'document_fields d2 LEFT OUTER JOIN conflicts c ON c.doc_id = '
            'd.doc_id WHERE d.doc_id = d0.doc_id AND d0.field_name = ? AND '
            'd0.value >= ? AND d.doc_id = d1.doc_id AND d1.field_name = ? AND '
            'd1.value >= ? AND d.doc_id = d2.doc_id AND d2.field_name = ? AND '
            'd2.value >= ? AND d.doc_id = d0.doc_id AND d0.field_name = ? AND '
            'd0.value <= ? AND d.doc_id = d1.doc_id AND d1.field_name = ? AND '
            'd1.value <= ? AND d.doc_id = d2.doc_id AND d2.field_name = ? AND '
            'd2.value <= ? GROUP BY d.doc_id, d.doc_rev, d.content ORDER BY '
            'd0.value, d1.value, d2.value;',
            ['key1', 'a', 'key2', 'b', 'key3', 'c', 'key1', 'p', 'key2', 'q',
             'key3', 'r'],
            ["key1", "key2", "key3"], ["a", "b", "c"], ["p", "q", "r"])

    def test__format_range_query_no_start(self):
        self.assertFormatRangeQueryEquals(
            'SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM '
            'document d, document_fields d0, document_fields d1, '
            'document_fields d2 LEFT OUTER JOIN conflicts c ON c.doc_id = '
            'd.doc_id WHERE d.doc_id = d0.doc_id AND d0.field_name = ? AND '
            'd0.value <= ? AND d.doc_id = d1.doc_id AND d1.field_name = ? AND '
            'd1.value <= ? AND d.doc_id = d2.doc_id AND d2.field_name = ? AND '
            'd2.value <= ? GROUP BY d.doc_id, d.doc_rev, d.content ORDER BY '
            'd0.value, d1.value, d2.value;',
            ['key1', 'a', 'key2', 'b', 'key3', 'c'],
            ["key1", "key2", "key3"], None, ["a", "b", "c"])

    def test__format_range_query_no_end(self):
        self.assertFormatRangeQueryEquals(
            'SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM '
            'document d, document_fields d0, document_fields d1, '
            'document_fields d2 LEFT OUTER JOIN conflicts c ON c.doc_id = '
            'd.doc_id WHERE d.doc_id = d0.doc_id AND d0.field_name = ? AND '
            'd0.value >= ? AND d.doc_id = d1.doc_id AND d1.field_name = ? AND '
            'd1.value >= ? AND d.doc_id = d2.doc_id AND d2.field_name = ? AND '
            'd2.value >= ? GROUP BY d.doc_id, d.doc_rev, d.content ORDER BY '
            'd0.value, d1.value, d2.value;',
            ['key1', 'a', 'key2', 'b', 'key3', 'c'],
            ["key1", "key2", "key3"], ["a", "b", "c"], None)

    def test__format_range_query_wildcard(self):
        self.assertFormatRangeQueryEquals(
            'SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM '
            'document d, document_fields d0, document_fields d1, '
            'document_fields d2 LEFT OUTER JOIN conflicts c ON c.doc_id = '
            'd.doc_id WHERE d.doc_id = d0.doc_id AND d0.field_name = ? AND '
            'd0.value >= ? AND d.doc_id = d1.doc_id AND d1.field_name = ? AND '
            'd1.value >= ? AND d.doc_id = d2.doc_id AND d2.field_name = ? AND '
            'd2.value NOT NULL AND d.doc_id = d0.doc_id AND d0.field_name = ? '
            'AND d0.value <= ? AND d.doc_id = d1.doc_id AND d1.field_name = ? '
            'AND (d1.value < ? OR d1.value GLOB ?) AND d.doc_id = d2.doc_id '
            'AND d2.field_name = ? AND d2.value NOT NULL GROUP BY d.doc_id, '
            'd.doc_rev, d.content ORDER BY d0.value, d1.value, d2.value;',
            ['key1', 'a', 'key2', 'b', 'key3', 'key1', 'p', 'key2', 'q', 'q*',
             'key3'],
            ["key1", "key2", "key3"], ["a", "b*", "*"], ["p", "q*", "*"])
