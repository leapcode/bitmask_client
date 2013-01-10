"""Test ObjectStore backend bits.

For these tests to run, a leap server has to be running on (default) port
5984.
"""

import sys
import copy
import testtools
import testscenarios
from u1db import errors, Document
from leap.soledad.backends import leap_backend
from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests.test_remote_sync_target import make_http_app
from leap.soledad.tests.u1db_tests.test_backends import AllDatabaseTests
from leap.soledad.tests.u1db_tests.test_http_database import (
    TestHTTPDatabaseSimpleOperations,
    TestHTTPDatabaseCtrWithCreds,
    TestHTTPDatabaseIntegration
)


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_common_backends`.
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


LEAP_SCENARIOS = [
        ('http', {'make_database_for_test': make_leap_database_for_test,
                  'copy_database_for_test': copy_leap_database_for_test,
                  'make_document_for_test': tests.make_document_for_test,
                  'make_app_with_state': make_http_app}),
        ]


class LeapTests(AllDatabaseTests):

    scenarios = LEAP_SCENARIOS


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_http_client`.
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


class TestLeapDatabaseCtrWithCreds(TestHTTPDatabaseCtrWithCreds):
    pass


class TestLeapDatabaseIntegration(TestHTTPDatabaseIntegration):

    def test_non_existing_db(self):
        db = leap_backend.LeapDatabase(self.getURL('not-there'))
        self.assertRaises(errors.DatabaseDoesNotExist, db.get_doc, 'doc1')

    def test__ensure(self):
        db = leap_backend.LeapDatabase(self.getURL('new'))
        db._ensure()
        self.assertIs(None, db.get_doc('doc1'))

    def test__delete(self):
        self.request_state._create_database('db0')
        db = leap_backend.LeapDatabase(self.getURL('db0'))
        db._delete()
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_open_database_existing(self):
        self.request_state._create_database('db0')
        db = leap_backend.LeapDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        self.assertIs(None, db.get_doc('doc1'))

    def test_open_database_non_existing(self):
        self.assertRaises(errors.DatabaseDoesNotExist,
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
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_doc_ids_needing_quoting(self):
        db0 = self.request_state._create_database('db0')
        db = leap_backend.LeapDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        doc = Document('%fff', None, '{}')
        db.put_doc(doc)
        self.assertGetDoc(db0, '%fff', doc.rev, '{}', False)
        self.assertGetDoc(db, '%fff', doc.rev, '{}', False)

load_tests = tests.load_with_scenarios
