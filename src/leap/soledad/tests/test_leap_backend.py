"""Test ObjectStore backend bits.

For these tests to run, a leap server has to be running on (default) port
5984.
"""

import sys
import copy
import testtools
import testscenarios
from leap.soledad.backends import leap_backend
from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests.test_remote_sync_target import make_http_app
from leap.soledad.tests.u1db_tests.test_backends import (
  AllDatabaseTests,
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


load_tests = tests.load_with_scenarios
