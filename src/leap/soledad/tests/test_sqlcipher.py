"""Test sqlcipher backend internals."""

import os
import time
from sqlite3 import dbapi2, DatabaseError
import unittest2 as unittest
from StringIO import StringIO
import threading

# u1db stuff.
from u1db import (
    errors,
    query_parser,
    sync,
)
from u1db.backends.sqlite_backend import SQLitePartialExpandDatabase

# soledad stuff.
from leap.soledad.backends.sqlcipher import (
    SQLCipherDatabase,
    DatabaseIsNotEncrypted,
)
from leap.soledad.backends.sqlcipher import open as u1db_open
from leap.soledad.backends.leap_backend import LeapDocument

# u1db tests stuff.
from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests import test_sqlite_backend
from leap.soledad.tests.u1db_tests import test_backends
from leap.soledad.tests.u1db_tests import test_open
from leap.soledad.tests.u1db_tests import test_sync
from leap.soledad.backends.leap_backend import LeapSyncTarget

PASSWORD = '123456'


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_common_backend`.
#-----------------------------------------------------------------------------

class TestSQLCipherBackendImpl(tests.TestCase):

    def test__allocate_doc_id(self):
        db = SQLCipherDatabase(':memory:', PASSWORD)
        doc_id1 = db._allocate_doc_id()
        self.assertTrue(doc_id1.startswith('D-'))
        self.assertEqual(34, len(doc_id1))
        int(doc_id1[len('D-'):], 16)
        self.assertNotEqual(doc_id1, db._allocate_doc_id())


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_backends`.
#-----------------------------------------------------------------------------

def make_sqlcipher_database_for_test(test, replica_uid):
    db = SQLCipherDatabase(':memory:', PASSWORD)
    db._set_replica_uid(replica_uid)
    return db


def copy_sqlcipher_database_for_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
    # HOUSE.
    new_db = SQLCipherDatabase(':memory:', PASSWORD)
    tmpfile = StringIO()
    for line in db._db_handle.iterdump():
        if not 'sqlite_sequence' in line:  # work around bug in iterdump
            tmpfile.write('%s\n' % line)
    tmpfile.seek(0)
    new_db._db_handle = dbapi2.connect(':memory:')
    new_db._db_handle.cursor().executescript(tmpfile.read())
    new_db._db_handle.commit()
    new_db._set_replica_uid(db._replica_uid)
    new_db._factory = db._factory
    return new_db


def make_document_for_test(test, doc_id, rev, content, has_conflicts=False):
    return LeapDocument(doc_id, rev, content, has_conflicts=has_conflicts)


SQLCIPHER_SCENARIOS = [
    ('sqlcipher', {'make_database_for_test': make_sqlcipher_database_for_test,
                   'copy_database_for_test': copy_sqlcipher_database_for_test,
                   'make_document_for_test': make_document_for_test, }),
]


class SQLCipherTests(test_backends.AllDatabaseTests):
    scenarios = SQLCIPHER_SCENARIOS


class SQLCipherDatabaseTests(test_backends.LocalDatabaseTests):
    scenarios = SQLCIPHER_SCENARIOS


class SQLCipherValidateGenNTransIdTests(
        test_backends.LocalDatabaseValidateGenNTransIdTests):
    scenarios = SQLCIPHER_SCENARIOS


class SQLCipherValidateSourceGenTests(
        test_backends.LocalDatabaseValidateSourceGenTests):
    scenarios = SQLCIPHER_SCENARIOS


class SQLCipherWithConflictsTests(
        test_backends.LocalDatabaseWithConflictsTests):
    scenarios = SQLCIPHER_SCENARIOS


class SQLCipherIndexTests(test_backends.DatabaseIndexTests):
    scenarios = SQLCIPHER_SCENARIOS


load_tests = tests.load_with_scenarios


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_sqlite_backend`.
#-----------------------------------------------------------------------------

class TestSQLCipherDatabase(test_sqlite_backend.TestSQLiteDatabase):

    def test_atomic_initialize(self):
        tmpdir = self.createTempDir()
        dbname = os.path.join(tmpdir, 'atomic.db')

        t2 = None  # will be a thread

        class SQLCipherDatabaseTesting(SQLitePartialExpandDatabase):
            _index_storage_value = "testing"

            def __init__(self, dbname, ntry):
                self._try = ntry
                self._is_initialized_invocations = 0
                super(SQLCipherDatabaseTesting, self).__init__(dbname)

            def _is_initialized(self, c):
                res = super(SQLCipherDatabaseTesting, self)._is_initialized(c)
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
                db2 = SQLCipherDatabaseTesting(dbname, 2)
            except Exception, e:
                outcome2.append(e)
            else:
                outcome2.append(db2)

        t2 = threading.Thread(target=second_try)
        db1 = SQLCipherDatabaseTesting(dbname, 1)
        t2.join()

        self.assertIsInstance(outcome2[0], SQLCipherDatabaseTesting)
        db2 = outcome2[0]
        self.assertTrue(db2._is_initialized(db1._get_sqlite_handle().cursor()))


class TestAlternativeDocument(LeapDocument):
    """A (not very) alternative implementation of Document."""


class TestSQLCipherPartialExpandDatabase(
        test_sqlite_backend.TestSQLitePartialExpandDatabase):

    # The following tests had to be cloned from u1db because they all
    # instantiate the backend directly, so we need to change that in order to
    # our backend be instantiated in place.

    def setUp(self):
        super(test_sqlite_backend.TestSQLitePartialExpandDatabase,
              self).setUp()
        self.db = SQLCipherDatabase(':memory:', PASSWORD)
        self.db._set_replica_uid('test')

    def test_default_replica_uid(self):
        self.db = SQLCipherDatabase(':memory:', PASSWORD)
        self.assertIsNot(None, self.db._replica_uid)
        self.assertEqual(32, len(self.db._replica_uid))
        int(self.db._replica_uid, 16)

    def test__parse_index(self):
        self.db = SQLCipherDatabase(':memory:', PASSWORD)
        g = self.db._parse_index_definition('fieldname')
        self.assertIsInstance(g, query_parser.ExtractField)
        self.assertEqual(['fieldname'], g.field)

    def test__update_indexes(self):
        self.db = SQLCipherDatabase(':memory:', PASSWORD)
        g = self.db._parse_index_definition('fieldname')
        c = self.db._get_sqlite_handle().cursor()
        self.db._update_indexes('doc-id', {'fieldname': 'val'},
                                [('fieldname', g)], c)
        c.execute('SELECT doc_id, field_name, value FROM document_fields')
        self.assertEqual([('doc-id', 'fieldname', 'val')],
                         c.fetchall())

    def test__set_replica_uid(self):
        # Start from scratch, so that replica_uid isn't set.
        self.db = SQLCipherDatabase(':memory:', PASSWORD)
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
        SQLCipherDatabase(path, PASSWORD)
        db2 = SQLCipherDatabase._open_database(path, PASSWORD)
        self.assertIsInstance(db2, SQLCipherDatabase)

    def test__open_database_with_factory(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/test.sqlite'
        SQLCipherDatabase(path, PASSWORD)
        db2 = SQLCipherDatabase._open_database(
            path, PASSWORD,
            document_factory=TestAlternativeDocument)
        self.assertEqual(TestAlternativeDocument, db2._factory)

    def test_open_database_existing(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/existing.sqlite'
        SQLCipherDatabase(path, PASSWORD)
        db2 = SQLCipherDatabase.open_database(path, PASSWORD, create=False)
        self.assertIsInstance(db2, SQLCipherDatabase)

    def test_open_database_with_factory(self):
        temp_dir = self.createTempDir(prefix='u1db-test-')
        path = temp_dir + '/existing.sqlite'
        SQLCipherDatabase(path, PASSWORD)
        db2 = SQLCipherDatabase.open_database(
            path, PASSWORD, create=False,
            document_factory=TestAlternativeDocument)
        self.assertEqual(TestAlternativeDocument, db2._factory)

    def test_create_database_initializes_schema(self):
        # This test had to be cloned because our implementation of SQLCipher
        # backend is referenced with an index_storage_value that includes the
        # word "encrypted". See u1db's sqlite_backend and our
        # sqlcipher_backend for reference.
        raw_db = self.db._get_sqlite_handle()
        c = raw_db.cursor()
        c.execute("SELECT * FROM u1db_config")
        config = dict([(r[0], r[1]) for r in c.fetchall()])
        self.assertEqual({'sql_schema': '0', 'replica_uid': 'test',
                          'index_storage': 'expand referenced encrypted'},
                         config)

    def test_store_syncable(self):
        doc = self.db.create_doc_from_json(tests.simple_doc)
        # assert that docs are syncable by default
        self.assertEqual(True, doc.syncable)
        # assert that we can store syncable = False
        doc.syncable = False
        self.db.put_doc(doc)
        self.assertEqual(False, self.db.get_doc(doc.doc_id).syncable)
        # assert that we can store syncable = True
        doc.syncable = True
        self.db.put_doc(doc)
        self.assertEqual(True, self.db.get_doc(doc.doc_id).syncable)


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_open`.
#-----------------------------------------------------------------------------

class SQLCipherOpen(test_open.TestU1DBOpen):

    def test_open_no_create(self):
        self.assertRaises(errors.DatabaseDoesNotExist,
                          u1db_open, self.db_path,
                          password=PASSWORD,
                          create=False)
        self.assertFalse(os.path.exists(self.db_path))

    def test_open_create(self):
        db = u1db_open(self.db_path, password=PASSWORD, create=True)
        self.addCleanup(db.close)
        self.assertTrue(os.path.exists(self.db_path))
        self.assertIsInstance(db, SQLCipherDatabase)

    def test_open_with_factory(self):
        db = u1db_open(self.db_path, password=PASSWORD, create=True,
                       document_factory=TestAlternativeDocument)
        self.addCleanup(db.close)
        self.assertEqual(TestAlternativeDocument, db._factory)

    def test_open_existing(self):
        db = SQLCipherDatabase(self.db_path, PASSWORD)
        self.addCleanup(db.close)
        doc = db.create_doc_from_json(tests.simple_doc)
        # Even though create=True, we shouldn't wipe the db
        db2 = u1db_open(self.db_path, password=PASSWORD, create=True)
        self.addCleanup(db2.close)
        doc2 = db2.get_doc(doc.doc_id)
        self.assertEqual(doc, doc2)

    def test_open_existing_no_create(self):
        db = SQLCipherDatabase(self.db_path, PASSWORD)
        self.addCleanup(db.close)
        db2 = u1db_open(self.db_path, password=PASSWORD, create=False)
        self.addCleanup(db2.close)
        self.assertIsInstance(db2, SQLCipherDatabase)


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_sync`.
#-----------------------------------------------------------------------------

sync_scenarios = []
for name, scenario in SQLCIPHER_SCENARIOS:
    scenario = dict(scenario)
    scenario['do_sync'] = test_sync.sync_via_synchronizer
    sync_scenarios.append((name, scenario))
    scenario = dict(scenario)


def sync_via_synchronizer_and_leap(test, db_source, db_target,
                                   trace_hook=None, trace_hook_shallow=None):
    if trace_hook:
        test.skipTest("full trace hook unsupported over http")
    path = test._http_at[db_target]
    target = LeapSyncTarget.connect(test.getURL(path))
    if trace_hook_shallow:
        target._set_trace_hook_shallow(trace_hook_shallow)
    return sync.Synchronizer(db_source, target).sync()


sync_scenarios.append(('pyleap', {
    'make_database_for_test': test_sync.make_database_for_http_test,
    'copy_database_for_test': test_sync.copy_database_for_http_test,
    'make_document_for_test': tests.make_document_for_test,
    'make_app_with_state': tests.test_remote_sync_target.make_http_app,
    'do_sync': sync_via_synchronizer_and_leap,
}))


class SQLCipherDatabaseSyncTests(test_sync.DatabaseSyncTests):

    scenarios = sync_scenarios


def _make_local_db_and_leap_target(test, path='test'):
    test.startServer()
    db = test.request_state._create_database(os.path.basename(path))
    st = LeapSyncTarget.connect(test.getURL(path))
    return db, st


target_scenarios = [
    ('leap', {
        'create_db_and_target': _make_local_db_and_leap_target,
        'make_app_with_state': tests.test_remote_sync_target.make_http_app}),
]


class SQLCipherSyncTargetTests(test_sync.DatabaseSyncTargetTests):

    scenarios = (tests.multiply_scenarios(SQLCIPHER_SCENARIOS,
                                          target_scenarios))


#-----------------------------------------------------------------------------
# Tests for actual encryption of the database
#-----------------------------------------------------------------------------

class SQLCipherEncryptionTest(unittest.TestCase):

    DB_FILE = '/tmp/test.db'

    def delete_dbfiles(self):
        for dbfile in [self.DB_FILE]:
            if os.path.exists(dbfile):
                os.unlink(dbfile)

    def setUp(self):
        self.delete_dbfiles()

    def tearDown(self):
        self.delete_dbfiles()

    def test_try_to_open_encrypted_db_with_sqlite_backend(self):
        db = SQLCipherDatabase(self.DB_FILE, PASSWORD)
        doc = db.create_doc_from_json(tests.simple_doc)
        db.close()
        try:
            # trying to open an encrypted database with the regular u1db
            # backend should raise a DatabaseError exception.
            SQLitePartialExpandDatabase(self.DB_FILE,
                                        document_factory=LeapDocument)
            raise DatabaseIsNotEncrypted()
        except DatabaseError:
            # at this point we know that the regular U1DB sqlcipher backend
            # did not succeed on opening the database, so it was indeed
            # encrypted.
            db = SQLCipherDatabase(self.DB_FILE, PASSWORD)
            doc = db.get_doc(doc.doc_id)
            self.assertEqual(tests.simple_doc, doc.get_json(),
                             'decrypted content mismatch')

    def test_try_to_open_raw_db_with_sqlcipher_backend(self):
        db = SQLitePartialExpandDatabase(self.DB_FILE,
                                         document_factory=LeapDocument)
        db.create_doc_from_json(tests.simple_doc)
        db.close()
        try:
            # trying to open the a non-encrypted database with sqlcipher
            # backend should raise a DatabaseIsNotEncrypted exception.
            SQLCipherDatabase(self.DB_FILE, PASSWORD)
            raise DatabaseError("SQLCipher backend should not be able to open "
                                "non-encrypted dbs.")
        except DatabaseIsNotEncrypted:
            pass


load_tests = tests.load_with_scenarios
