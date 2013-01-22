# Copyright 2011-2012 Canonical Ltd.
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

"""Test infrastructure for U1DB"""

import copy
import shutil
import socket
import tempfile
import threading

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from wsgiref import simple_server

from oauth import oauth
from sqlite3 import dbapi2
from StringIO import StringIO

import testscenarios
import testtools

from u1db import (
    errors,
    Document,
    )
from u1db.backends import (
    inmemory,
    sqlite_backend,
    )
from u1db.remote import (
    server_state,
    )

try:
    from leap.soledad.tests.u1db_tests import c_backend_wrapper
    c_backend_error = None
except ImportError, e:
    c_backend_wrapper = None  # noqa
    c_backend_error = e

# Setting this means that failing assertions will not include this module in
# their traceback. However testtools doesn't seem to set it, and we don't want
# this level to be omitted, but the lower levels to be shown.
# __unittest = 1


class TestCase(testtools.TestCase):

    def createTempDir(self, prefix='u1db-tmp-'):
        """Create a temporary directory to do some work in.

        This directory will be scheduled for cleanup when the test ends.
        """
        tempdir = tempfile.mkdtemp(prefix=prefix)
        self.addCleanup(shutil.rmtree, tempdir)
        return tempdir

    def make_document(self, doc_id, doc_rev, content, has_conflicts=False):
        return self.make_document_for_test(
            self, doc_id, doc_rev, content, has_conflicts)

    def make_document_for_test(self, test, doc_id, doc_rev, content,
                               has_conflicts):
        return make_document_for_test(
            test, doc_id, doc_rev, content, has_conflicts)

    def assertGetDoc(self, db, doc_id, doc_rev, content, has_conflicts):
        """Assert that the document in the database looks correct."""
        exp_doc = self.make_document(doc_id, doc_rev, content,
                                     has_conflicts=has_conflicts)
        self.assertEqual(exp_doc, db.get_doc(doc_id))

    def assertGetDocIncludeDeleted(self, db, doc_id, doc_rev, content,
                                   has_conflicts):
        """Assert that the document in the database looks correct."""
        exp_doc = self.make_document(doc_id, doc_rev, content,
                                     has_conflicts=has_conflicts)
        self.assertEqual(exp_doc, db.get_doc(doc_id, include_deleted=True))

    def assertGetDocConflicts(self, db, doc_id, conflicts):
        """Assert what conflicts are stored for a given doc_id.

        :param conflicts: A list of (doc_rev, content) pairs.
            The first item must match the first item returned from the
            database, however the rest can be returned in any order.
        """
        if conflicts:
            conflicts = [(rev, (json.loads(cont) if isinstance(cont, basestring)
                           else cont)) for (rev, cont) in conflicts]
            conflicts = conflicts[:1] + sorted(conflicts[1:])
        actual = db.get_doc_conflicts(doc_id)
        if actual:
            actual = [(doc.rev, (json.loads(doc.get_json())
                   if doc.get_json() is not None else None)) for doc in actual]
            actual = actual[:1] + sorted(actual[1:])
        self.assertEqual(conflicts, actual)


def multiply_scenarios(a_scenarios, b_scenarios):
    """Create the cross-product of scenarios."""

    all_scenarios = []
    for a_name, a_attrs in a_scenarios:
        for b_name, b_attrs in b_scenarios:
            name = '%s,%s' % (a_name, b_name)
            attrs = dict(a_attrs)
            attrs.update(b_attrs)
            all_scenarios.append((name, attrs))
    return all_scenarios


simple_doc = '{"key": "value"}'
nested_doc = '{"key": "value", "sub": {"doc": "underneath"}}'


def make_memory_database_for_test(test, replica_uid):
    return inmemory.InMemoryDatabase(replica_uid)


def copy_memory_database_for_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
    # HOUSE.
    new_db = inmemory.InMemoryDatabase(db._replica_uid)
    new_db._transaction_log = db._transaction_log[:]
    new_db._docs = copy.deepcopy(db._docs)
    new_db._conflicts = copy.deepcopy(db._conflicts)
    new_db._indexes = copy.deepcopy(db._indexes)
    new_db._factory = db._factory
    return new_db


def make_sqlite_partial_expanded_for_test(test, replica_uid):
    db = sqlite_backend.SQLitePartialExpandDatabase(':memory:')
    db._set_replica_uid(replica_uid)
    return db


def copy_sqlite_partial_expanded_for_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
    # HOUSE.
    new_db = sqlite_backend.SQLitePartialExpandDatabase(':memory:')
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
    return Document(doc_id, rev, content, has_conflicts=has_conflicts)


def make_c_database_for_test(test, replica_uid):
    if c_backend_wrapper is None:
        test.skipTest('c_backend_wrapper is not available')
    db = c_backend_wrapper.CDatabase(':memory:')
    db._set_replica_uid(replica_uid)
    return db


def copy_c_database_for_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
    # HOUSE.
    if c_backend_wrapper is None:
        test.skipTest('c_backend_wrapper is not available')
    new_db = db._copy(db)
    return new_db


def make_c_document_for_test(test, doc_id, rev, content, has_conflicts=False):
    if c_backend_wrapper is None:
        test.skipTest('c_backend_wrapper is not available')
    return c_backend_wrapper.make_document(
        doc_id, rev, content, has_conflicts=has_conflicts)


LOCAL_DATABASES_SCENARIOS = [
        ('mem', {'make_database_for_test': make_memory_database_for_test,
                 'copy_database_for_test': copy_memory_database_for_test,
                 'make_document_for_test': make_document_for_test}),
        ('sql', {'make_database_for_test':
                 make_sqlite_partial_expanded_for_test,
                 'copy_database_for_test':
                 copy_sqlite_partial_expanded_for_test,
                 'make_document_for_test': make_document_for_test}),
        ]


C_DATABASE_SCENARIOS = [
        ('c', {'make_database_for_test': make_c_database_for_test,
               'copy_database_for_test': copy_c_database_for_test,
               'make_document_for_test': make_c_document_for_test})]


class DatabaseBaseTests(TestCase):

    accept_fixed_trans_id = False  # set to True assertTransactionLog
                                   # is happy with all trans ids = ''

    scenarios = LOCAL_DATABASES_SCENARIOS

    def create_database(self, replica_uid):
        return self.make_database_for_test(self, replica_uid)

    def copy_database(self, db):
        # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES
        # IS THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST
        # THAT WE CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS
        # RATHER THAN CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND
        # NINJA TO YOUR HOUSE.
        return self.copy_database_for_test(self, db)

    def setUp(self):
        super(DatabaseBaseTests, self).setUp()
        self.db = self.create_database('test')

    def tearDown(self):
        # TODO: Add close_database parameterization
        # self.close_database(self.db)
        super(DatabaseBaseTests, self).tearDown()

    def assertTransactionLog(self, doc_ids, db):
        """Assert that the given docs are in the transaction log."""
        log = db._get_transaction_log()
        just_ids = []
        seen_transactions = set()
        for doc_id, transaction_id in log:
            just_ids.append(doc_id)
            self.assertIsNot(None, transaction_id,
                             "Transaction id should not be None")
            if transaction_id == '' and self.accept_fixed_trans_id:
                continue
            self.assertNotEqual('', transaction_id,
                                "Transaction id should be a unique string")
            self.assertTrue(transaction_id.startswith('T-'))
            self.assertNotIn(transaction_id, seen_transactions)
            seen_transactions.add(transaction_id)
        self.assertEqual(doc_ids, just_ids)

    def getLastTransId(self, db):
        """Return the transaction id for the last database update."""
        return self.db._get_transaction_log()[-1][-1]


class ServerStateForTests(server_state.ServerState):
    """Used in the test suite, so we don't have to touch disk, etc."""

    def __init__(self):
        super(ServerStateForTests, self).__init__()
        self._dbs = {}

    def open_database(self, path):
        try:
            return self._dbs[path]
        except KeyError:
            raise errors.DatabaseDoesNotExist

    def check_database(self, path):
        # cares only about the possible exception
        self.open_database(path)

    def ensure_database(self, path):
        try:
            db =  self.open_database(path)
        except errors.DatabaseDoesNotExist:
            db = self._create_database(path)
        return db, db._replica_uid

    def _copy_database(self, db):
        # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES
        # IS THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST
        # THAT WE CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS
        # RATHER THAN CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND
        # NINJA TO YOUR HOUSE.
        new_db = copy_memory_database_for_test(None, db)
        path = db._replica_uid
        while path in self._dbs:
            path += 'copy'
        self._dbs[path] = new_db
        return new_db

    def _create_database(self, path):
        db = inmemory.InMemoryDatabase(path)
        self._dbs[path] = db
        return db

    def delete_database(self, path):
        del self._dbs[path]


class ResponderForTests(object):
    """Responder for tests."""
    _started = False
    sent_response = False
    status = None

    def start_response(self, status='success', **kwargs):
        self._started = True
        self.status = status
        self.kwargs = kwargs

    def send_response(self, status='success', **kwargs):
        self.start_response(status, **kwargs)
        self.finish_response()

    def finish_response(self):
        self.sent_response = True


class TestCaseWithServer(TestCase):

    @staticmethod
    def server_def():
        # hook point
        # should return (ServerClass, "shutdown method name", "url_scheme")
        class _RequestHandler(simple_server.WSGIRequestHandler):
            def log_request(*args):
                pass  # suppress

        def make_server(host_port, application):
            assert application, "forgot to override make_app(_with_state)?"
            srv = simple_server.WSGIServer(host_port, _RequestHandler)
            # patch the value in if it's None
            if getattr(application, 'base_url', 1) is None:
                application.base_url = "http://%s:%s" % srv.server_address
            srv.set_app(application)
            return srv

        return make_server, "shutdown", "http"

    @staticmethod
    def make_app_with_state(state):
        # hook point
        return None

    def make_app(self):
        # potential hook point
        self.request_state = ServerStateForTests()
        return self.make_app_with_state(self.request_state)

    def setUp(self):
        super(TestCaseWithServer, self).setUp()
        self.server = self.server_thread = None

    @property
    def url_scheme(self):
        return self.server_def()[-1]

    def startServer(self):
        server_def = self.server_def()
        server_class, shutdown_meth, _ = server_def
        application = self.make_app()
        self.server = server_class(('127.0.0.1', 0), application)
        self.server_thread = threading.Thread(target=self.server.serve_forever,
                                              kwargs=dict(poll_interval=0.01))
        self.server_thread.start()
        self.addCleanup(self.server_thread.join)
        self.addCleanup(getattr(self.server, shutdown_meth))

    def getURL(self, path=None):
        host, port = self.server.server_address
        if path is None:
            path = ''
        return '%s://%s:%s/%s' % (self.url_scheme, host, port, path)


def socket_pair():
    """Return a pair of TCP sockets connected to each other.

    Unlike socket.socketpair, this should work on Windows.
    """
    sock_pair = getattr(socket, 'socket_pair', None)
    if sock_pair:
        return sock_pair(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.bind(('127.0.0.1', 0))
    listen_sock.listen(1)
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(listen_sock.getsockname())
    server_sock, addr = listen_sock.accept()
    listen_sock.close()
    return server_sock, client_sock


# OAuth related testing

consumer1 = oauth.OAuthConsumer('K1', 'S1')
token1 = oauth.OAuthToken('kkkk1', 'XYZ')
consumer2 = oauth.OAuthConsumer('K2', 'S2')
token2 = oauth.OAuthToken('kkkk2', 'ZYX')
token3 = oauth.OAuthToken('kkkk3', 'ZYX')


class TestingOAuthDataStore(oauth.OAuthDataStore):
    """In memory predefined OAuthDataStore for testing."""

    consumers = {
        consumer1.key: consumer1,
        consumer2.key: consumer2,
        }

    tokens = {
        token1.key: token1,
        token2.key: token2
        }

    def lookup_consumer(self, key):
        return self.consumers.get(key)

    def lookup_token(self, token_type, token_token):
        return self.tokens.get(token_token)

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        return None

testingOAuthStore = TestingOAuthDataStore()

sign_meth_HMAC_SHA1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
sign_meth_PLAINTEXT = oauth.OAuthSignatureMethod_PLAINTEXT()


def load_with_scenarios(loader, standard_tests, pattern):
    """Load the tests in a given module.

    This just applies testscenarios.generate_scenarios to all the tests that
    are present. We do it at load time rather than at run time, because it
    plays nicer with various tools.
    """
    suite = loader.suiteClass()
    suite.addTests(testscenarios.generate_scenarios(standard_tests))
    return suite
