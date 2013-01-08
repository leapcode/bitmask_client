"""Test ObjectStore backend bits."""

import sys
import copy
import testtools
import testscenarios
from leap.soledad.backends import couch
from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests.test_backends import AllDatabaseTests


class TestCouchBackendImpl(tests.TestCase):

    def test__allocate_doc_id(self):
        db = couch.CouchDatabase('http://localhost:5984', 'u1db_tests')
        doc_id1 = db._allocate_doc_id()
        self.assertTrue(doc_id1.startswith('D-'))
        self.assertEqual(34, len(doc_id1))
        int(doc_id1[len('D-'):], 16)
        self.assertNotEqual(doc_id1, db._allocate_doc_id())

def make_couch_database_for_test(test, replica_uid, path='test'):
    return couch.CouchDatabase('http://localhost:5984', 'u1db_tests',
                               replica_uid=replica_uid)

def copy_couch_database_for_test(test, db):
    new_db = couch.CouchDatabase('http://localhost:5984', 'u1db_tests_2',
                                 replica_uid=db.replica_uid)
    new_db._transaction_log = copy.deepcopy(db._transaction_log)
    new_db._sync_log = copy.deepcopy(db._sync_log)
    gen, docs = db.get_all_docs(include_deleted=True)
    for doc in docs:
        new_db._put_doc(doc)
    new_db._ensure_u1db_data()
    return new_db

def make_couch_app(test):
    pass


class CouchTests(AllDatabaseTests):

    scenarios = [
        ('couch', {'make_database_for_test': make_couch_database_for_test,
                  'copy_database_for_test': copy_couch_database_for_test,
                  'make_document_for_test': tests.make_document_for_test,}),
        ]

    def tearDown(self):
        self.db.delete_database()
        super(CouchTests, self).tearDown()


    #make_database_for_test = make_couch_database_for_test
    #copy_database_for_test = copy_couch_database_for_test

#    def runTest(self):
#        pass
#

load_tests = tests.load_with_scenarios
