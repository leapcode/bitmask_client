"""Test LEAP backend internals."""

from u1db import (
    errors,
    Document,
    )

from leap.soledad.backends import leap_backend as http_database
from leap.soledad.backends.leap_backend import LeapDocument

from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests.test_http_database import (
  TestHTTPDatabaseSimpleOperations,
  TestHTTPDatabaseCtrWithCreds,
  TestHTTPDatabaseIntegration,
)
from leap.soledad.tests.u1db_tests.test_http_client import TestHTTPClientBase
from leap.soledad.tests.u1db_tests.test_document import (
  TestDocument,
  TestPyDocument,
)
from leap.soledad.tests.u1db_tests.test_remote_sync_target import (
  TestHTTPSyncTargetBasics,
  TestParsingSyncStream,
)


#-----------------------------------------------------------------------------
# LeapDatabase
#-----------------------------------------------------------------------------

class TestLeapDatabaseSimpleOperations(TestHTTPDatabaseSimpleOperations):

    def setUp(self):
        super(TestHTTPDatabaseSimpleOperations, self).setUp()
        self.db = http_database.LeapDatabase('dbase')
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

    def test_create_doc_without_id(self):
        self.response_val = {'rev': 'doc-rev-2'}, {}
        new_doc = self.db.create_doc_from_json('{"v": 3}')


class TestLeapDatabaseCtrWithCreds(TestHTTPDatabaseCtrWithCreds):

    def test_ctr_with_creds(self):
        db1 = http_database.LeapDatabase('http://dbs/db', creds={'oauth': {
            'consumer_key': tests.consumer1.key,
            'consumer_secret': tests.consumer1.secret,
            'token_key': tests.token1.key,
            'token_secret': tests.token1.secret
            }})
        self.assertIn('oauth',  db1._creds)


class TestLeapDatabaseIntegration(TestHTTPDatabaseIntegration):

    def test_non_existing_db(self):
        db = http_database.LeapDatabase(self.getURL('not-there'))
        self.assertRaises(errors.DatabaseDoesNotExist, db.get_doc, 'doc1')

    def test__ensure(self):
        db = http_database.LeapDatabase(self.getURL('new'))
        db._ensure()
        self.assertIs(None, db.get_doc('doc1'))

    def test__delete(self):
        self.request_state._create_database('db0')
        db = http_database.LeapDatabase(self.getURL('db0'))
        db._delete()
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_open_database_existing(self):
        self.request_state._create_database('db0')
        db = http_database.LeapDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        self.assertIs(None, db.get_doc('doc1'))

    def test_open_database_non_existing(self):
        self.assertRaises(errors.DatabaseDoesNotExist,
                          http_database.LeapDatabase.open_database,
                          self.getURL('not-there'),
                          create=False)

    def test_open_database_create(self):
        db = http_database.LeapDatabase.open_database(self.getURL('new'),
                                                      create=True)
        self.assertIs(None, db.get_doc('doc1'))

    def test_delete_database_existing(self):
        self.request_state._create_database('db0')
        http_database.LeapDatabase.delete_database(self.getURL('db0'))
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_doc_ids_needing_quoting(self):
        db0 = self.request_state._create_database('db0')
        db = http_database.LeapDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        doc = Document('%fff', None, '{}')
        db.put_doc(doc)
        self.assertGetDoc(db0, '%fff', doc.rev, '{}', False)
        self.assertGetDoc(db, '%fff', doc.rev, '{}', False)


class TestLeapClientBase(TestHTTPClientBase):
    pass


#-----------------------------------------------------------------------------
# LeapDocument
#-----------------------------------------------------------------------------

def make_document_for_test(test, doc_id, rev, content, has_conflicts=False):
    return LeapDocument(doc_id, rev, content, has_conflicts=has_conflicts)


class TestLeapDocument(TestDocument):

    scenarios = ([(
        'py', {'make_document_for_test': make_document_for_test})])


class TestLeapPyDocument(TestPyDocument):

    scenarios = ([(
        'py', {'make_document_for_test': make_document_for_test})])


#-----------------------------------------------------------------------------
# LeapSyncTarget
#-----------------------------------------------------------------------------

class TestLeapSyncTargetBasics(TestHTTPSyncTargetBasics):

    def test_parse_url(self):
        remote_target = http_database.LeapSyncTarget('http://127.0.0.1:12345/')
        self.assertEqual('http', remote_target._url.scheme)
        self.assertEqual('127.0.0.1', remote_target._url.hostname)
        self.assertEqual(12345, remote_target._url.port)
        self.assertEqual('/', remote_target._url.path)

class TestLeapParsingSyncStream(TestParsingSyncStream):

    def test_wrong_start(self):
        tgt = http_database.LeapSyncTarget("http://foo/foo")

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "{}\r\n]", None)

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "\r\n{}\r\n]", None)

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "", None)

    def test_wrong_end(self):
        tgt = http_database.LeapSyncTarget("http://foo/foo")

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n{}", None)

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n", None)

    def test_missing_comma(self):
        tgt = http_database.LeapSyncTarget("http://foo/foo")

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream,
                          '[\r\n{}\r\n{"id": "i", "rev": "r", '
                          '"content": "c", "gen": 3}\r\n]', None)

    def test_no_entries(self):
        tgt = http_database.LeapSyncTarget("http://foo/foo")

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n]", None)

    def test_extra_comma(self):
        tgt = http_database.LeapSyncTarget("http://foo/foo")

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream, "[\r\n{},\r\n]", None)

        self.assertRaises(http_database.NoSoledadInstance,
                          tgt._parse_sync_stream,
                          '[\r\n{},\r\n{"id": "i", "rev": "r", '
                          '"content": "{}", "gen": 3, "trans_id": "T-sid"}'
                          ',\r\n]',
                          lambda doc, gen, trans_id: None)

    def test_error_in_stream(self):
        tgt = http_database.LeapSyncTarget("http://foo/foo")

        self.assertRaises(errors.Unavailable,
                          tgt._parse_sync_stream,
                          '[\r\n{"new_generation": 0},'
                          '\r\n{"error": "unavailable"}\r\n', None)

        self.assertRaises(errors.Unavailable,
                          tgt._parse_sync_stream,
                          '[\r\n{"error": "unavailable"}\r\n', None)

        self.assertRaises(errors.BrokenSyncStream,
                          tgt._parse_sync_stream,
                          '[\r\n{"error": "?"}\r\n', None)

