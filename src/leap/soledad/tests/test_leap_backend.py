"""Test ObjectStore backend bits.

For these tests to run, a leap server has to be running on (default) port
5984.
"""

from shutil import rmtree
import os
import copy
import unittest2 as unittest
import testtools
import testscenarios
import u1db
from leap.soledad import Soledad
from leap.soledad.backends import leap_backend
from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests.test_remote_sync_target import (
    make_http_app,
    make_oauth_http_app,
)
from leap.soledad.tests.u1db_tests.test_backends import AllDatabaseTests
from leap.soledad.tests.u1db_tests.test_http_database import (
    TestHTTPDatabaseSimpleOperations,
    TestHTTPDatabaseCtrWithCreds,
    TestHTTPDatabaseIntegration,
)
from leap.soledad.tests.u1db_tests.test_http_client import (
    TestHTTPClientBase,
)
from leap.soledad.tests.u1db_tests.test_document import (
    TestDocument,
    TestPyDocument,
)
from leap.soledad.tests.u1db_tests.test_remote_sync_target import (
    TestHTTPSyncTargetBasics,
    TestParsingSyncStream,
)
from leap.soledad.tests.u1db_tests.test_sync import (
    _make_local_db_and_target,
    DatabaseSyncTargetTests,
)
from leap.soledad.tests.u1db_tests.test_https import (
    TestHttpSyncTargetHttpsSupport,
    https_server_def,
)
from leap.soledad.tests.test_encrypted import (
    PUBLIC_KEY,
    PRIVATE_KEY,
    KEY_FINGERPRINT,
)

try:
    import simplejson as json
except ImportError:
    import json  # noqa

#-----------------------------------------------------------------------------
# The EncryptedSyncTest is used with multiple inheritance to guarantee that we
# have a working Soledad instance in each test.
#-----------------------------------------------------------------------------

class SoledadTest(unittest.TestCase):

    PREFIX     = "/var/tmp"
    GNUPG_HOME = "%s/gnupg" % PREFIX
    DB1_FILE   = "%s/db1.u1db" % PREFIX
    DB2_FILE   = "%s/db2.u1db" % PREFIX
    EMAIL      = 'leap@leap.se'

    def setUp(self):
        super(SoledadTest, self).setUp()
        self._db1 = u1db.open(self.DB1_FILE, create=True,
                              document_factory=leap_backend.LeapDocument)
        self._db2 = u1db.open(self.DB2_FILE, create=True,
                              document_factory=leap_backend.LeapDocument)
        self._soledad = Soledad(self.EMAIL, gpghome=self.GNUPG_HOME)
        self._soledad._gpg.import_keys(PUBLIC_KEY)
        self._soledad._gpg.import_keys(PRIVATE_KEY)

    def tearDown(self):
        super(SoledadTest, self).tearDown()
        os.unlink(self.DB1_FILE)
        os.unlink(self.DB2_FILE)
        #rmtree(self.GNUPG_HOME)


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_common_backend`.
#-----------------------------------------------------------------------------

class TestLeapBackendImpl(tests.TestCase):

    def test__allocate_doc_id(self):
        db = leap_backend.LeapDatabase('test')
        doc_id1 = db._allocate_doc_id()
        self.assertTrue(doc_id1.startswith('D-'))
        self.assertEqual(34, len(doc_id1))
        int(doc_id1[len('D-'):], 16)
        self.assertNotEqual(doc_id1, db._allocate_doc_id())


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_backends`.
#-----------------------------------------------------------------------------

def make_leap_database_for_test(test, replica_uid, path='test'):
    test.startServer()
    test.request_state._create_database(replica_uid)
    return leap_backend.LeapDatabase(test.getURL(path))


def copy_leap_database_for_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
    # HOUSE.
    return test.request_state._copy_database(db)


def make_oauth_leap_database_for_test(test, replica_uid):
    http_db = make_leap_database_for_test(test, replica_uid, '~/test')
    http_db.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                                  tests.token1.key, tests.token1.secret)
    return http_db


def make_document_for_test(test, doc_id, rev, content, has_conflicts=False):
    return leap_backend.LeapDocument(
        doc_id, rev, content, has_conflicts=has_conflicts)


def make_leap_document_for_test(test, doc_id, rev, content, has_conflicts=False):
    return leap_backend.LeapDocument(
        doc_id, rev, content, has_conflicts=has_conflicts,
        soledad=test._soledad)


def make_leap_encrypted_document_for_test(test, doc_id, rev, encrypted_content,
                                          has_conflicts=False):
    return leap_backend.LeapDocument(
        doc_id, rev, encrypted_json=encrypted_content,
        has_conflicts=has_conflicts,
        soledad=test._soledad)


LEAP_SCENARIOS = [
        ('http', {'make_database_for_test': make_leap_database_for_test,
                  'copy_database_for_test': copy_leap_database_for_test,
                  'make_document_for_test': make_leap_document_for_test,
                  'make_app_with_state': make_http_app}),
        ]


class LeapTests(AllDatabaseTests, SoledadTest):

    scenarios = LEAP_SCENARIOS


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_http_database`.
#-----------------------------------------------------------------------------

class TestLeapDatabaseSimpleOperations(TestHTTPDatabaseSimpleOperations):

    def setUp(self):
        super(TestHTTPDatabaseSimpleOperations, self).setUp()
        self.db = leap_backend.LeapDatabase('dbase')
        self.db._conn = object()  # crash if used
        self.got = None
        self.response_val = None

        def _request(method, url_parts, params=None, body=None,
                                                     content_type=None):
            self.got = method, url_parts, params, body, content_type
            if isinstance(self.response_val, Exception):
                raise self.response_val
            return self.response_val

        def _request_json(method, url_parts, params=None, body=None,
                                                          content_type=None):
            self.got = method, url_parts, params, body, content_type
            if isinstance(self.response_val, Exception):
                raise self.response_val
            return self.response_val

        self.db._request = _request
        self.db._request_json = _request_json

    def test_get_sync_target(self):
        st = self.db.get_sync_target()
        self.assertIsInstance(st, leap_backend.LeapSyncTarget)
        self.assertEqual(st._url, self.db._url)


class TestLeapDatabaseCtrWithCreds(TestHTTPDatabaseCtrWithCreds):
    pass


class TestLeapDatabaseIntegration(TestHTTPDatabaseIntegration):

    def test_non_existing_db(self):
        db = leap_backend.LeapDatabase(self.getURL('not-there'))
        self.assertRaises(u1db.errors.DatabaseDoesNotExist, db.get_doc, 'doc1')

    def test__ensure(self):
        db = leap_backend.LeapDatabase(self.getURL('new'))
        db._ensure()
        self.assertIs(None, db.get_doc('doc1'))

    def test__delete(self):
        self.request_state._create_database('db0')
        db = leap_backend.LeapDatabase(self.getURL('db0'))
        db._delete()
        self.assertRaises(u1db.errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_open_database_existing(self):
        self.request_state._create_database('db0')
        db = leap_backend.LeapDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        self.assertIs(None, db.get_doc('doc1'))

    def test_open_database_non_existing(self):
        self.assertRaises(u1db.errors.DatabaseDoesNotExist,
                          leap_backend.LeapDatabase.open_database,
                          self.getURL('not-there'),
                          create=False)

    def test_open_database_create(self):
        db = leap_backend.LeapDatabase.open_database(self.getURL('new'),
                                                      create=True)
        self.assertIs(None, db.get_doc('doc1'))

    def test_delete_database_existing(self):
        self.request_state._create_database('db0')
        leap_backend.LeapDatabase.delete_database(self.getURL('db0'))
        self.assertRaises(u1db.errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_doc_ids_needing_quoting(self):
        db0 = self.request_state._create_database('db0')
        db = leap_backend.LeapDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        doc = leap_backend.LeapDocument('%fff', None, '{}')
        db.put_doc(doc)
        self.assertGetDoc(db0, '%fff', doc.rev, '{}', False)
        self.assertGetDoc(db, '%fff', doc.rev, '{}', False)


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_http_client`.
#-----------------------------------------------------------------------------

class TestLeapClientBase(TestHTTPClientBase):
    pass


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_document`.
#-----------------------------------------------------------------------------

class TestLeapDocument(TestDocument, SoledadTest):

    scenarios = ([(
        'leap', {'make_document_for_test': make_leap_document_for_test})])


class TestLeapPyDocument(TestPyDocument, SoledadTest):

    scenarios = ([(
        'leap', {'make_document_for_test': make_leap_document_for_test})])


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_remote_sync_target`.
#-----------------------------------------------------------------------------

class TestLeapSyncTargetBasics(TestHTTPSyncTargetBasics):

    def test_parse_url(self):
        remote_target = leap_backend.LeapSyncTarget('http://127.0.0.1:12345/')
        self.assertEqual('http', remote_target._url.scheme)
        self.assertEqual('127.0.0.1', remote_target._url.hostname)
        self.assertEqual(12345, remote_target._url.port)
        self.assertEqual('/', remote_target._url.path)

class TestLeapParsingSyncStream(TestParsingSyncStream):

    def test_wrong_start(self):
        tgt = leap_backend.LeapSyncTarget("http://foo/foo")

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "{}\r\n]", None)

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "\r\n{}\r\n]", None)

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "", None)

    def test_wrong_end(self):
        tgt = leap_backend.LeapSyncTarget("http://foo/foo")

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n{}", None)

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n", None)

    def test_missing_comma(self):
        tgt = leap_backend.LeapSyncTarget("http://foo/foo")

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream,
                          '[\r\n{}\r\n{"id": "i", "rev": "r", '
                          '"content": "c", "gen": 3}\r\n]', None)

    def test_no_entries(self):
        tgt = leap_backend.LeapSyncTarget("http://foo/foo")

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n]", None)

    def test_extra_comma(self):
        tgt = leap_backend.LeapSyncTarget("http://foo/foo")

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n{},\r\n]", None)

        self.assertRaises(leap_backend.NoSoledadInstance,
                          tgt._parse_sync_stream,
                          '[\r\n{},\r\n{"id": "i", "rev": "r", '
                          '"content": "{}", "gen": 3, "trans_id": "T-sid"}'
                          ',\r\n]',
                          lambda doc, gen, trans_id: None)

    def test_error_in_stream(self):
        tgt = leap_backend.LeapSyncTarget("http://foo/foo")

        self.assertRaises(u1db.errors.Unavailable,
                          tgt._parse_sync_stream,
                          '[\r\n{"new_generation": 0},'
                          '\r\n{"error": "unavailable"}\r\n', None)

        self.assertRaises(u1db.errors.Unavailable,
                          tgt._parse_sync_stream,
                          '[\r\n{"error": "unavailable"}\r\n', None)

        self.assertRaises(u1db.errors.BrokenSyncStream,
                          tgt._parse_sync_stream,
                          '[\r\n{"error": "?"}\r\n', None)


def leap_sync_target(test, path):
    return leap_backend.LeapSyncTarget(test.getURL(path))


def oauth_leap_sync_target(test, path):
    st = leap_sync_target(test, '~/' + path)
    st.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                             tests.token1.key, tests.token1.secret)
    return st


class TestRemoteSyncTargets(tests.TestCaseWithServer):

    scenarios = [
        ('http', {'make_app_with_state': make_http_app,
                  'make_document_for_test': make_leap_document_for_test,
                  'sync_target': leap_sync_target}),
        ('oauth_http', {'make_app_with_state': make_oauth_http_app,
                        'make_document_for_test': make_leap_document_for_test,
                        'sync_target': oauth_leap_sync_target}),
        ]


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_https`.
#-----------------------------------------------------------------------------

def oauth_https_sync_target(test, host, path):
    _, port = test.server.server_address
    st = leap_backend.LeapSyncTarget('https://%s:%d/~/%s' % (host, port, path))
    st.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                             tests.token1.key, tests.token1.secret)
    return st

class TestLeapSyncTargetHttpsSupport(TestHttpSyncTargetHttpsSupport, SoledadTest):

    scenarios = [
        ('oauth_https', {'server_def': https_server_def,
                         'make_app_with_state': make_oauth_http_app,
                         'make_document_for_test': make_leap_document_for_test,
                         'sync_target': oauth_https_sync_target
                         }),
        ]

load_tests = tests.load_with_scenarios
