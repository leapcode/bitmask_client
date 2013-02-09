"""Test ObjectStore backend bits.

For these tests to run, a couch server has to be running on (default) port
5984.
"""

import copy
from leap.soledad.backends import couch
from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests import test_backends
from leap.soledad.tests.u1db_tests import test_sync
try:
    import simplejson as json
except ImportError:
    import json  # noqa


#-----------------------------------------------------------------------------
# A wrapper for running couchdb locally.
#-----------------------------------------------------------------------------

import re
import os
import tempfile
import subprocess
import time
import unittest


# from: https://github.com/smcq/paisley/blob/master/paisley/test/util.py
# TODO: include license of above project.
class CouchDBWrapper(object):
    """
    Wrapper for external CouchDB instance which is started and stopped for
    testing.
    """

    def start(self):
        self.tempdir = tempfile.mkdtemp(suffix='.couch.test')

        path = os.path.join(os.path.dirname(__file__),
                            'couchdb.ini.template')
        handle = open(path)
        conf = handle.read() % {
            'tempdir': self.tempdir,
        }
        handle.close()

        confPath = os.path.join(self.tempdir, 'test.ini')
        handle = open(confPath, 'w')
        handle.write(conf)
        handle.close()

        # create the dirs from the template
        os.mkdir(os.path.join(self.tempdir, 'lib'))
        os.mkdir(os.path.join(self.tempdir, 'log'))
        args = ['couchdb', '-n' '-a', confPath]
        #null = open('/dev/null', 'w')
        self.process = subprocess.Popen(
            args, env=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            close_fds=True)
        # find port
        logPath = os.path.join(self.tempdir, 'log', 'couch.log')
        while not os.path.exists(logPath):
            if self.process.poll() is not None:
                raise Exception("""
couchdb exited with code %d.
stdout:
%s
stderr:
%s""" % (
                    self.process.returncode, self.process.stdout.read(),
                    self.process.stderr.read()))
            time.sleep(0.01)
        while os.stat(logPath).st_size == 0:
            time.sleep(0.01)
        PORT_RE = re.compile(
            'Apache CouchDB has started on http://127.0.0.1:(?P<port>\d+)')

        handle = open(logPath)
        line = handle.read()
        handle.close()
        m = PORT_RE.search(line)
        if not m:
            self.stop()
            raise Exception("Cannot find port in line %s" % line)
        self.port = int(m.group('port'))

    def stop(self):
        self.process.terminate()
        self.process.wait()
        os.system("rm -rf %s" % self.tempdir)


class CouchDBTestCase(unittest.TestCase):
    """
    TestCase base class for tests against a real CouchDB server.
    """

    def setUp(self):
        self.wrapper = CouchDBWrapper()
        self.wrapper.start()
        #self.db = self.wrapper.db
        super(CouchDBTestCase, self).setUp()

    def tearDown(self):
        self.wrapper.stop()
        super(CouchDBTestCase, self).tearDown()


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_common_backend`.
#-----------------------------------------------------------------------------

class TestCouchBackendImpl(CouchDBTestCase):

    def test__allocate_doc_id(self):
        db = couch.CouchDatabase('http://localhost:'+str(self.wrapper.port),
                                 'u1db_tests')
        doc_id1 = db._allocate_doc_id()
        self.assertTrue(doc_id1.startswith('D-'))
        self.assertEqual(34, len(doc_id1))
        int(doc_id1[len('D-'):], 16)
        self.assertNotEqual(doc_id1, db._allocate_doc_id())


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_backends`.
#-----------------------------------------------------------------------------

def make_couch_database_for_test(test, replica_uid):
    port = str(test.wrapper.port)
    return couch.CouchDatabase('http://localhost:'+port, replica_uid,
                               replica_uid=replica_uid or 'test')


def copy_couch_database_for_test(test, db):
    port = str(test.wrapper.port)
    new_db = couch.CouchDatabase('http://localhost:'+port,
                                 db._replica_uid + '_copy',
                                 replica_uid=db._replica_uid or 'test')
    gen, docs = db.get_all_docs(include_deleted=True)
    for doc in docs:
        new_db._put_doc(doc)
    new_db._transaction_log = copy.deepcopy(db._transaction_log)
    new_db._conflicts = copy.deepcopy(db._conflicts)
    new_db._other_generations = copy.deepcopy(db._other_generations)
    new_db._indexes = copy.deepcopy(db._indexes)
    new_db._set_u1db_data()
    return new_db


COUCH_SCENARIOS = [
    ('couch', {'make_database_for_test': make_couch_database_for_test,
               'copy_database_for_test': copy_couch_database_for_test,
               'make_document_for_test': tests.make_document_for_test, }),
]


class CouchTests(test_backends.AllDatabaseTests, CouchDBTestCase):

    scenarios = COUCH_SCENARIOS

    def tearDown(self):
        self.db.delete_database()
        super(CouchTests, self).tearDown()


class CouchDatabaseTests(test_backends.LocalDatabaseTests, CouchDBTestCase):

    scenarios = COUCH_SCENARIOS

    def tearDown(self):
        self.db.delete_database()
        super(CouchDatabaseTests, self).tearDown()


class CouchValidateGenNTransIdTests(
        test_backends.LocalDatabaseValidateGenNTransIdTests, CouchDBTestCase):

    scenarios = COUCH_SCENARIOS

    def tearDown(self):
        self.db.delete_database()
        super(CouchValidateGenNTransIdTests, self).tearDown()


class CouchValidateSourceGenTests(
        test_backends.LocalDatabaseValidateSourceGenTests, CouchDBTestCase):

    scenarios = COUCH_SCENARIOS

    def tearDown(self):
        self.db.delete_database()
        super(CouchValidateSourceGenTests, self).tearDown()


class CouchWithConflictsTests(
        test_backends.LocalDatabaseWithConflictsTests, CouchDBTestCase):

    scenarios = COUCH_SCENARIOS

    def tearDown(self):
        self.db.delete_database()
        super(CouchWithConflictsTests, self).tearDown()


# Notice: the CouchDB backend is currently used for storing encrypted data in
# the server, so indexing makes no sense. Thus, we ignore index testing for
# now.

class CouchIndexTests(test_backends.DatabaseIndexTests, CouchDBTestCase):

    scenarios = COUCH_SCENARIOS

    def tearDown(self):
        self.db.delete_database()
        super(CouchIndexTests, self).tearDown()


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_sync`.
#-----------------------------------------------------------------------------

target_scenarios = [
    ('local', {'create_db_and_target': test_sync._make_local_db_and_target}), ]


simple_doc = tests.simple_doc
nested_doc = tests.nested_doc


class CouchDatabaseSyncTargetTests(test_sync.DatabaseSyncTargetTests,
                                   CouchDBTestCase):

    scenarios = (tests.multiply_scenarios(COUCH_SCENARIOS, target_scenarios))

    def tearDown(self):
        self.db.delete_database()
        super(CouchDatabaseSyncTargetTests, self).tearDown()

    def test_sync_exchange_returns_many_new_docs(self):
        # This test was replicated to allow dictionaries to be compared after
        # JSON expansion (because one dictionary may have many different
        # serialized representations).
        doc = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.assertTransactionLog([doc.doc_id, doc2.doc_id], self.db)
        new_gen, _ = self.st.sync_exchange(
            [], 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertTransactionLog([doc.doc_id, doc2.doc_id], self.db)
        self.assertEqual(2, new_gen)
        self.assertEqual(
            [(doc.doc_id, doc.rev, json.loads(simple_doc), 1),
             (doc2.doc_id, doc2.rev, json.loads(nested_doc), 2)],
            [c[:-3] + (json.loads(c[-3]), c[-2]) for c in self.other_changes])
        if self.whitebox:
            self.assertEqual(
                self.db._last_exchange_log['return'],
                {'last_gen': 2, 'docs':
                 [(doc.doc_id, doc.rev), (doc2.doc_id, doc2.rev)]})


sync_scenarios = []
for name, scenario in COUCH_SCENARIOS:
    scenario = dict(scenario)
    scenario['do_sync'] = test_sync.sync_via_synchronizer
    sync_scenarios.append((name, scenario))
    scenario = dict(scenario)


class CouchDatabaseSyncTests(test_sync.DatabaseSyncTests, CouchDBTestCase):

    scenarios = sync_scenarios

    def setUp(self):
        self.db = None
        self.db1 = None
        self.db2 = None
        self.db3 = None
        super(CouchDatabaseSyncTests, self).setUp()

    def tearDown(self):
        self.db and self.db.delete_database()
        self.db1 and self.db1.delete_database()
        self.db2 and self.db2.delete_database()
        self.db3 and self.db3.delete_database()
        db = self.create_database('test1_copy', 'source')
        db.delete_database()
        db = self.create_database('test2_copy', 'target')
        db.delete_database()
        db = self.create_database('test3', 'target')
        db.delete_database()
        super(CouchDatabaseSyncTests, self).tearDown()


load_tests = tests.load_with_scenarios
