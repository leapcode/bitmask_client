"""Test ObjectStore backend bits.

For these tests to run, a leap server has to be running on (default) port
5984.
"""

import u1db
from leap.soledad.backends import leap_backend
from leap.soledad.tests import u1db_tests as tests
from leap.soledad.tests.u1db_tests.test_remote_sync_target import (
    make_http_app,
    make_oauth_http_app,
)
from leap.soledad.tests import BaseSoledadTest
from leap.soledad.tests.u1db_tests import test_backends
from leap.soledad.tests.u1db_tests import test_http_database
from leap.soledad.tests.u1db_tests import test_http_client
from leap.soledad.tests.u1db_tests import test_document
from leap.soledad.tests.u1db_tests import test_remote_sync_target
from leap.soledad.tests.u1db_tests import test_https


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_backends`.
#-----------------------------------------------------------------------------

def make_leap_document_for_test(test, doc_id, rev, content,
                                has_conflicts=False):
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
    ('http', {
        'make_database_for_test': test_backends.make_http_database_for_test,
        'copy_database_for_test': test_backends.copy_http_database_for_test,
        'make_document_for_test': make_leap_document_for_test,
        'make_app_with_state': make_http_app}),
]


class LeapTests(test_backends.AllDatabaseTests, BaseSoledadTest):

    scenarios = LEAP_SCENARIOS


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_http_client`.
#-----------------------------------------------------------------------------

class TestLeapClientBase(test_http_client.TestHTTPClientBase):
    pass


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_document`.
#-----------------------------------------------------------------------------

class TestLeapDocument(test_document.TestDocument, BaseSoledadTest):

    scenarios = ([(
        'leap', {'make_document_for_test': make_leap_document_for_test})])


class TestLeapPyDocument(test_document.TestPyDocument, BaseSoledadTest):

    scenarios = ([(
        'leap', {'make_document_for_test': make_leap_document_for_test})])


#-----------------------------------------------------------------------------
# The following tests come from `u1db.tests.test_remote_sync_target`.
#-----------------------------------------------------------------------------

class TestLeapSyncTargetBasics(
        test_remote_sync_target.TestHTTPSyncTargetBasics):

    def test_parse_url(self):
        remote_target = leap_backend.LeapSyncTarget('http://127.0.0.1:12345/')
        self.assertEqual('http', remote_target._url.scheme)
        self.assertEqual('127.0.0.1', remote_target._url.hostname)
        self.assertEqual(12345, remote_target._url.port)
        self.assertEqual('/', remote_target._url.path)


class TestLeapParsingSyncStream(test_remote_sync_target.TestParsingSyncStream):

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


class TestLeapSyncTargetHttpsSupport(test_https.TestHttpSyncTargetHttpsSupport,
                                     BaseSoledadTest):

    scenarios = [
        ('oauth_https', {'server_def': test_https.https_server_def,
                         'make_app_with_state': make_oauth_http_app,
                         'make_document_for_test': make_leap_document_for_test,
                         'sync_target': oauth_https_sync_target,
                         }), ]

load_tests = tests.load_with_scenarios
