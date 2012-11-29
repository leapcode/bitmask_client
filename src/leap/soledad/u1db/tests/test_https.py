"""Test support for client-side https support."""

import os
import ssl
import sys

from paste import httpserver

from u1db import (
    tests,
    )
from u1db.remote import (
    http_client,
    http_target,
    )

from u1db.tests.test_remote_sync_target import (
    make_oauth_http_app,
    )


def https_server_def():
    def make_server(host_port, application):
        from OpenSSL import SSL
        cert_file = os.path.join(os.path.dirname(__file__), 'testing-certs',
                                 'testing.cert')
        key_file = os.path.join(os.path.dirname(__file__), 'testing-certs',
                                'testing.key')
        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        ssl_context.use_privatekey_file(key_file)
        ssl_context.use_certificate_chain_file(cert_file)
        srv = httpserver.WSGIServerBase(application, host_port,
                                        httpserver.WSGIHandler,
                                        ssl_context=ssl_context
                                        )

        def shutdown_request(req):
            req.shutdown()
            srv.close_request(req)

        srv.shutdown_request = shutdown_request
        application.base_url = "https://localhost:%s" % srv.server_address[1]
        return srv
    return make_server, "shutdown", "https"


def oauth_https_sync_target(test, host, path):
    _, port = test.server.server_address
    st = http_target.HTTPSyncTarget('https://%s:%d/~/%s' % (host, port, path))
    st.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                             tests.token1.key, tests.token1.secret)
    return st


class TestHttpSyncTargetHttpsSupport(tests.TestCaseWithServer):

    scenarios = [
        ('oauth_https', {'server_def': https_server_def,
                         'make_app_with_state': make_oauth_http_app,
                         'make_document_for_test': tests.make_document_for_test,
                         'sync_target': oauth_https_sync_target
                         }),
        ]

    def setUp(self):
        try:
            import OpenSSL  # noqa
        except ImportError:
            self.skipTest("Requires pyOpenSSL")
        self.cacert_pem = os.path.join(os.path.dirname(__file__),
                                       'testing-certs', 'cacert.pem')
        super(TestHttpSyncTargetHttpsSupport, self).setUp()

    def getSyncTarget(self, host, path=None):
        if self.server is None:
            self.startServer()
        return self.sync_target(self, host, path)

    def test_working(self):
        self.startServer()
        db = self.request_state._create_database('test')
        self.patch(http_client, 'CA_CERTS', self.cacert_pem)
        remote_target = self.getSyncTarget('localhost', 'test')
        remote_target.record_sync_info('other-id', 2, 'T-id')
        self.assertEqual(
            (2, 'T-id'), db._get_replica_gen_and_trans_id('other-id'))

    def test_cannot_verify_cert(self):
        if not sys.platform.startswith('linux'):
            self.skipTest(
                "XXX certificate verification happens on linux only for now")
        self.startServer()
        # don't print expected traceback server-side
        self.server.handle_error = lambda req, cli_addr: None
        self.request_state._create_database('test')
        remote_target = self.getSyncTarget('localhost', 'test')
        try:
            remote_target.record_sync_info('other-id', 2, 'T-id')
        except ssl.SSLError, e:
            self.assertIn("certificate verify failed", str(e))
        else:
            self.fail("certificate verification should have failed.")

    def test_host_mismatch(self):
        if not sys.platform.startswith('linux'):
            self.skipTest(
                "XXX certificate verification happens on linux only for now")
        self.startServer()
        self.request_state._create_database('test')
        self.patch(http_client, 'CA_CERTS', self.cacert_pem)
        remote_target = self.getSyncTarget('127.0.0.1', 'test')
        self.assertRaises(
            http_client.CertificateError, remote_target.record_sync_info,
            'other-id', 2, 'T-id')


load_tests = tests.load_with_scenarios
