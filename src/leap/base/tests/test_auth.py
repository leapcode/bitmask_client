from BaseHTTPServer import BaseHTTPRequestHandler
import urlparse
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import requests
#from mock import Mock

from leap.base import auth
#from leap.base import exceptions
from leap.eip.tests.test_checks import NoLogRequestHandler
from leap.testing.basetest import BaseLeapTest
from leap.testing.https_server import BaseHTTPSServerTestCase


class LeapSRPRegisterTests(BaseHTTPSServerTestCase, BaseLeapTest):
    __name__ = "leap_srp_register_test"
    provider = "testprovider.example.org"

    class request_handler(NoLogRequestHandler, BaseHTTPRequestHandler):
        responses = {
            '/': ['OK', '']}

        def do_GET(self):
            path = urlparse.urlparse(self.path)
            message = '\n'.join(self.responses.get(
                path.path, None))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(message)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_srp_auth_should_implement_check_methods(self):
        SERVER = "https://localhost:8443"
        srp_auth = auth.LeapSRPRegister(provider=SERVER, verify=False)

        self.assertTrue(hasattr(srp_auth, "init_session"),
                        "missing meth")
        self.assertTrue(hasattr(srp_auth, "get_registration_uri"),
                        "missing meth")
        self.assertTrue(hasattr(srp_auth, "register_user"),
                        "missing meth")

    def test_srp_auth_basic_functionality(self):
        SERVER = "https://localhost:8443"
        srp_auth = auth.LeapSRPRegister(provider=SERVER, verify=False)

        self.assertIsInstance(srp_auth.session, requests.sessions.Session)
        self.assertEqual(
            srp_auth.get_registration_uri(),
            "https://localhost:8443/1/users.json")
